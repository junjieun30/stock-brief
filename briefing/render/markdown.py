"""마크다운 리포트 렌더링."""
from __future__ import annotations

from ..models import Brief, Quote


def _fmt(q: Quote) -> str:
    if not q.ok:
        return f"| {q.name} | — | — | {q.error or '데이터 없음'} |"
    arrow = "▲" if q.change_pct > 0 else ("▼" if q.change_pct < 0 else "—")
    body = f"{q.price:,.{q.digits if q.digits is not None else 2}f}"
    price = f"{q.unit}{body}" if q.unit in ("$", "€", "¥") else f"{body}{q.unit}"
    delta = f"{q.change * 100:+.1f}bp" if q.change_mode == "bp" else f"{q.change_pct:+.2f}%"
    return f"| {q.name} | {price} | {arrow} {delta} | {q.symbol} |"


def _table(title: str, quotes: list[Quote]) -> str:
    if not quotes:
        return ""
    head = f"### {title}\n\n| 항목 | 종가 | 등락 | 심볼 |\n|---|---:|---:|---|\n"
    return head + "\n".join(_fmt(q) for q in quotes) + "\n\n"


def render(brief: Brief) -> str:
    ts = brief.generated_at.strftime("%Y-%m-%d %H:%M")
    out = [
        f"# 해외 시장 데일리 브리핑",
        "",
        f"- 시장 기준일: **{brief.market_date or '미상'}** (미국 마감 기준)",
        f"- 생성 시각: {ts} KST",
        "",
    ]

    if brief.alerts:
        th = brief.alerts[0].threshold
        out += [f"## 급등락 알림 (±{th:g}% 초과)", ""]
        for a in brief.alerts:
            mark = "🔺" if a.direction == "up" else "🔻"
            out.append(f"- {mark} **{a.quote.name}** ({a.quote.symbol}) {a.quote.change_pct:+.2f}%")
        out.append("")

    if brief.ai_summary:
        out += ["## 시장 총평", "", brief.ai_summary, "",
                "> AI가 생성한 요약입니다. 투자 판단의 근거로 삼기 전에 원문을 확인하세요.", ""]

    out += ["## 시세", ""]
    out.append(_table("주요 지수", brief.indices))
    out.append(_table("글로벌 증시", brief.global_indices))
    out.append(_table("G10 통화", brief.fx))
    out.append(_table("매크로 · 환율 · 원자재", brief.macro))
    out.append(_table("섹터 ETF", brief.sectors))
    out.append(_table("관심 종목", brief.watchlist))

    if brief.gainers or brief.losers:
        out += ["## 상승 / 하락 상위", ""]
        out.append(_table("상승 상위", brief.gainers))
        out.append(_table("하락 상위", brief.losers))

    if brief.calendar:
        today = brief.generated_at.date()
        out += ["## 앞으로 예정된 일정", ""]
        for e in brief.calendar:
            kind = "실적" if e.kind == "earnings" else "지표"
            out.append(f"- **{e.d_day(today)}** · {e.title} ({kind})"
                       + (f"  \n  <sub>{e.detail}</sub>" if e.detail else ""))
        out.append("")

    if brief.news:
        out += ["## 주요 뉴스", ""]
        for n in brief.news:
            when = n.published.strftime("%m-%d %H:%M") if n.published else ""
            title = n.summary_ko or n.title
            out.append(f"- **[{title}]({n.url})**  \n  <sub>{n.source} · {when} · {n.title}</sub>")
        out.append("")

    if brief.ticker_news:
        out += ["## 내 관심 종목 소식", ""]
        for q in brief.watchlist:
            items = brief.ticker_news.get(q.symbol)
            if not items:
                continue
            out.append(f"**{q.name}** ({q.symbol})")
            for n in items:
                out.append(f"- [{n.summary_ko or n.title}]({n.url}) <sub>{n.source}</sub>")
            out.append("")

    if brief.lessons:
        out += ["## 오늘의 공부", ""]
        for l in brief.lessons:
            badge = "주식 용어" if l.kind == "term" else "투자 심리"
            out += [f"### [{badge}] {l.term}", "", l.plain, "", f"> {l.why}", ""]

    if brief.reflection:
        r = brief.reflection
        body = f"“{r.body}”" if r.kind == "quote" else r.body
        kind_label = "인용" if r.kind == "quote" else "사상 요약 · 직접 인용이 아닙니다"
        out += ["## 오늘의 사색", "", f"> {body}", "",
                f"— **{r.name}** · {r.who}  ", f"<sub>{kind_label} · {r.source}</sub>", "",
                f"*{r.sit}*", ""]
        if r.note:
            out += [f"<sub>{r.note}</sub>", ""]

    if brief.warnings:
        out += ["## 수집 경고", ""] + [f"- {w}" for w in brief.warnings] + [""]

    out += ["---", "",
            "이 리포트는 공개 시세·뉴스 데이터를 자동 수집해 정리한 참고 자료이며, "
            "투자 자문이나 매매 권유가 아닙니다."]
    return "\n".join(out)
