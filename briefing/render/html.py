"""HTML 리포트 렌더링 (Jinja2)."""
from __future__ import annotations

import html as _html
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from ..models import Brief, Quote

TEMPLATE_DIR = Path(__file__).parent / "templates"


# --- Jinja 필터 ---------------------------------------------------------
def f_price(q: Quote) -> str:
    if q.price is None:
        return "—"
    digits = 2 if abs(q.price) < 10000 else 0
    body = f"{q.price:,.{digits}f}"
    return f"{q.unit}{body}" if q.unit in ("$", "€", "¥") else f"{body}{q.unit}"


def f_pct(q: Quote) -> str:
    if q.change_pct is None:
        return "—"
    arrow = "▲" if q.change_pct > 0 else ("▼" if q.change_pct < 0 else "—")
    if q.change_mode == "bp":          # 금리는 등락률이 아니라 변동폭(bp)으로 읽는다
        return f"{arrow} {q.change * 100:+.1f}bp"
    return f"{arrow} {q.change_pct:+.2f}%"


def f_vol(q: Quote) -> str:
    v = q.volume
    if not v:
        return "—"
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if v >= div:
            return f"{v / div:.1f}{unit}"
    return f"{v:,.0f}"


def f_from_high(q: Quote) -> str:
    p = q.pct_from_high
    return "—" if p is None else f"{p:.1f}%"


def f_pos_bar(q: Quote) -> Markup:
    """52주 레인지 내 현재가 위치를 작은 막대로."""
    pos = q.range_position
    if pos is None:
        return Markup("<span class='flat'>—</span>")
    return Markup(f"<span class='pos' title='52주 저점 대비 {pos:.0f}%'>"
                  f"<b style='left:{max(0, min(100, pos)):.1f}%'></b></span>")


def make_sector_fill(quotes: list[Quote]):
    """섹터 막대는 그날 최대 변동폭 기준으로 폭을 정규화한다."""
    scale = max((abs(q.change_pct) for q in quotes if q.ok), default=1.0) or 1.0

    def _fill(q: Quote) -> Markup:
        if not q.ok:
            return Markup("")
        half = min(abs(q.change_pct) / scale, 1.0) * 50
        color = "var(--up)" if q.change_pct > 0 else "var(--down)"
        if q.change_pct >= 0:
            style = f"left:50%;width:{half:.1f}%"
        else:
            style = f"right:50%;width:{half:.1f}%"
        return Markup(f"<span class='fill' style='{style};background:{color}'></span>")

    return _fill


_BOLD = re.compile(r"\*\*(.+?)\*\*")


def f_md_bold(text: str) -> Markup:
    """Claude 요약에 섞여 오는 **굵게** 만 최소한으로 살린다 (그 외는 이스케이프)."""
    escaped = _html.escape(text or "")
    return Markup(_BOLD.sub(r"<strong>\1</strong>", escaped))


# --- 렌더 ---------------------------------------------------------------
def render(brief: Brief) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(
        price=f_price, pct=f_pct, vol=f_vol, pos_bar=f_pos_bar,
        from_high=f_from_high, md_bold=f_md_bold,
        sector_fill=make_sector_fill(brief.sectors),
    )
    return env.get_template("report.html.j2").render(
        brief=brief,
        sectors_sorted=sorted(
            brief.sectors, key=lambda q: q.change_pct if q.ok else -999, reverse=True
        ),
        mover_tables=[("상승 상위", brief.gainers), ("하락 상위", brief.losers)],
    )
