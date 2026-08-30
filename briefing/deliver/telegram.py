"""텔레그램 봇으로 브리핑 요약을 전송한다."""
from __future__ import annotations

import html
import logging

import requests

from ..models import Brief, Quote

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/sendMessage"
LIMIT = 4000          # 텔레그램 메시지 한도 4096자, 여유를 둔다


def _esc(text: str) -> str:
    """텔레그램 HTML 파스모드는 & < > 를 반드시 이스케이프해야 한다.
    ("S&P 500" 을 그대로 보내면 400 Bad Request 로 전송이 실패한다.)"""
    return html.escape(text or "", quote=False)


def _line(q: Quote) -> str:
    if not q.ok:
        return f"{_esc(q.name)}: —"
    mark = "🔺" if q.change_pct > 0 else ("🔻" if q.change_pct < 0 else "▪")
    delta = f"{q.change * 100:+.1f}bp" if q.change_mode == "bp" else f"{q.change_pct:+.2f}%"
    body = f"{q.price:,.2f}"
    price = f"{q.unit}{body}" if q.unit in ("$", "€", "¥") else f"{body}{q.unit}"
    return f"{mark} {_esc(q.name)} {price} ({delta})"


def build_message(brief: Brief, max_news: int = 6) -> str:
    parts = [f"📈 <b>해외 시장 브리핑</b> · {brief.market_date or '미상'}", ""]

    parts.append("<b>주요 지수</b>")
    parts += [_line(q) for q in brief.indices]
    parts.append("")

    parts.append("<b>매크로</b>")
    parts += [_line(q) for q in brief.macro]
    parts.append("")

    if brief.watchlist:
        parts.append("<b>관심 종목</b>")
        parts += [_line(q) for q in brief.watchlist]
        parts.append("")

    if brief.ai_summary:
        # 텔레그램 HTML 파스모드는 마크다운 ** 를 모르므로 <b> 로 바꿔준다
        summary = _esc(brief.ai_summary.replace("**", ""))
        parts += ["<b>시장 총평</b>", summary, ""]

    if brief.news:
        parts.append("<b>주요 뉴스</b>")
        for n in brief.news[:max_news]:
            title = _esc(n.summary_ko or n.title)
            parts.append(f'• <a href="{html.escape(n.url, quote=True)}">{title}</a>')
        parts.append("")

    parts.append("<i>참고 자료이며 투자 권유가 아닙니다.</i>")

    # 글자수로 자르면 <a href> 태그 한가운데가 잘려 텔레그램이 400 을 낸다.
    # 한도를 넘으면 뒤에서부터 줄 단위로 덜어낸다.
    tail = "…(이하 생략)"
    truncated = False
    while parts and len("\n".join(parts)) > LIMIT - len(tail) - 1:
        parts.pop()
        truncated = True
        while parts and not parts[-1].strip():
            parts.pop()

    msg = "\n".join(parts)
    return msg + "\n" + tail if truncated else msg


def send(brief: Brief, secrets) -> str | None:
    """성공하면 None, 실패하면 경고 문자열을 반환한다."""
    if not (secrets.telegram_token and secrets.telegram_chat):
        return "텔레그램 전송 건너뜀 (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 없음)"
    try:
        r = requests.post(
            API.format(token=secrets.telegram_token),
            json={
                "chat_id": secrets.telegram_chat,
                "text": build_message(brief),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        r.raise_for_status()
        log.info("텔레그램 전송 완료")
        return None
    except Exception as e:
        log.warning("텔레그램 전송 실패: %s", e)
        return f"텔레그램 전송 실패: {e}"
