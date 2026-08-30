"""Claude Messages API 로 영문 헤드라인을 한국어로 요약하고 시장 총평을 만든다.

원칙: 사실 요약만 한다. 매수/매도 추천이나 개인화된 투자 조언은 생성하지 않는다.
"""
from __future__ import annotations

import json
import logging

from .models import Brief, NewsItem, Quote

log = logging.getLogger(__name__)

SYSTEM = """당신은 한국 투자자를 위한 해외 시장 데일리 브리핑 에디터입니다.

역할:
- 제공된 영문 뉴스 헤드라인과 시세 데이터만 근거로 사실을 정리합니다.
- 모든 출력은 자연스러운 한국어로 작성합니다. 번역투를 피하고 경제 기사체로 씁니다.
- 고유명사(기업명, 인물, 기관)는 한국에서 통용되는 표기를 쓰고, 필요하면 괄호에 원문을 병기합니다.

엄격한 금지 사항:
- 매수/매도/보유 추천, 목표가 제시, "지금 사야 한다" 류의 투자 권유를 하지 않습니다.
- 제공되지 않은 수치, 사건, 인용문을 지어내지 않습니다. 근거가 없으면 언급하지 않습니다.
- 미래 가격을 단정적으로 예측하지 않습니다. 시장의 관측/전망은 "~라는 해석이 나온다" 처럼 출처를 시장에 돌립니다.

톤: 담백하고 정보 밀도 높게. 감탄사, 이모지, 과장 표현을 쓰지 않습니다."""

SCHEMA = {
    "type": "object",
    "properties": {
        "market_commentary": {
            "type": "string",
            "description": "전일 해외 증시 총평. 4~6문장의 한국어 단락. 지수 방향, 주도 섹터, 매크로 변수(금리/달러/유가)를 엮어서 서술한다.",
        },
        "headlines": {
            "type": "array",
            "description": "입력으로 준 각 헤드라인에 대한 한국어 요약. 입력과 같은 개수, 같은 순서.",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "입력 헤드라인의 0-기반 번호"},
                    "title_ko": {"type": "string", "description": "헤드라인을 한국어 한 문장으로 옮긴 제목"},
                    "note": {"type": "string", "description": "왜 시장에 의미가 있는지 한 문장. 정보가 부족하면 빈 문자열."},
                },
                "required": ["index", "title_ko", "note"],
                "additionalProperties": False,
            },
        },
        "sector_commentary": {
            "type": "string",
            "description": ("섹터별 등락 해설. 2~4문장의 한국어. 가장 오른/내린 섹터가 왜 움직였는지를 "
                            "제공된 헤드라인과 시세에서 근거를 찾아 설명한다. 헤드라인에 근거가 없으면 "
                            "지어내지 말고 '뚜렷한 단일 재료보다는 ~' 처럼 신중하게 서술한다."),
        },
        "watch_points": {
            "type": "array",
            "description": "오늘 확인할 관전 포인트 3~5개. 각 항목은 한 문장. 투자 권유가 아닌 확인 사항으로 서술.",
            "items": {"type": "string"},
        },
    },
    "required": ["market_commentary", "sector_commentary", "headlines", "watch_points"],
    "additionalProperties": False,
}


def _quotes_block(label: str, quotes: list[Quote]) -> str:
    rows = []
    for q in quotes:
        if not q.ok:
            continue
        delta = f"{q.change * 100:+.1f}bp" if q.change_mode == "bp" else f"{q.change_pct:+.2f}%"
        digits = q.digits if q.digits is not None else 2
        rows.append(f"- {q.name} ({q.symbol}): {q.price:,.{digits}f}{q.unit} ({delta})")
    return f"[{label}]\n" + ("\n".join(rows) if rows else "- 데이터 없음")


def _collect_headlines(brief: Brief, limit: int) -> list[list[NewsItem]]:
    """번역 대상 헤드라인을 모은다. 시장 뉴스 + 관심종목 뉴스.

    같은 기사가 두 섹션에 겹쳐 나올 수 있으므로 제목이 같은 것끼리 묶고,
    번역은 한 번만 시킨 뒤 묶인 모두에 적용한다.
    """
    groups: dict[str, list[NewsItem]] = {}
    order: list[str] = []

    def add(item: NewsItem) -> None:
        key = item.title.strip().lower()[:70]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item)

    for n in brief.news[:limit]:
        add(n)
    for items in brief.ticker_news.values():
        for n in items:
            add(n)

    return [groups[k] for k in order]


def _build_prompt(brief: Brief, headlines: list[NewsItem]) -> str:
    parts = [
        f"기준일: {brief.market_date or '미상'} (미국 시장 마감 기준)",
        "",
        _quotes_block("주요 지수", brief.indices),
        "",
        _quotes_block("글로벌 증시 (G10 등)", brief.global_indices),
        "",
        _quotes_block("G10 통화 (달러 대비)", brief.fx),
        "",
        _quotes_block("매크로/환율/원자재", brief.macro),
        "",
        _quotes_block("섹터 ETF", brief.sectors),
        "",
        _quotes_block("관심 종목", brief.watchlist),
        "",
        _quotes_block("상승 상위", brief.gainers),
        "",
        _quotes_block("하락 상위", brief.losers),
        "",
        "[영문 뉴스 헤드라인]",
    ]
    for i, n in enumerate(headlines):
        parts.append(f"{i}. ({n.source}) {n.title}")
    parts += [
        "",
        "위 데이터만 근거로 다음을 작성하세요:",
        "1) market_commentary — 전일 해외 증시 총평",
        "1-1) sector_commentary — 섹터 ETF 등락의 배경 해설 (근거는 위 헤드라인에서만)",
        f"2) headlines — 위 {len(headlines)}개 헤드라인 전부를 같은 번호로 한국어 요약",
        "3) watch_points — 오늘의 관전 포인트",
    ]
    return "\n".join(parts)


def summarize(brief: Brief, cfg) -> None:
    """brief 를 제자리에서 갱신한다. 실패해도 예외를 올리지 않고 warning 만 남긴다."""
    if not cfg.ai_enabled:
        brief.warnings.append("AI 요약 건너뜀 (ai.enabled=false 이거나 ANTHROPIC_API_KEY 없음)")
        return
    if not brief.news:
        brief.warnings.append("AI 요약 건너뜀 (뉴스 없음)")
        return

    import anthropic

    ai = cfg.get("ai", {})
    groups = _collect_headlines(brief, ai.get("max_headlines", 16))
    headlines = [g[0] for g in groups]        # 그룹 대표 1건씩만 번역시킨다
    client = anthropic.Anthropic(api_key=cfg.secrets.anthropic, timeout=180.0, max_retries=3)

    try:
        with client.messages.stream(
            model=ai.get("model", "claude-opus-5"),
            max_tokens=ai.get("max_tokens", 16000),
            system=SYSTEM,
            messages=[{"role": "user", "content": _build_prompt(brief, headlines)}],
            thinking={"type": "adaptive"},
            output_config={
                "effort": ai.get("effort", "medium"),
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
        ) as stream:
            response = stream.get_final_message()
    except anthropic.AuthenticationError:
        brief.warnings.append("AI 요약 실패: ANTHROPIC_API_KEY 가 유효하지 않습니다.")
        return
    except anthropic.RateLimitError:
        brief.warnings.append("AI 요약 실패: API 요청 한도 초과. 잠시 후 다시 시도하세요.")
        return
    except anthropic.APIStatusError as e:
        brief.warnings.append(f"AI 요약 실패: API 오류 {e.status_code}")
        return
    except anthropic.APIConnectionError:
        brief.warnings.append("AI 요약 실패: 네트워크 연결 오류")
        return
    except Exception as e:                                    # 요약이 없어도 리포트는 나가야 한다
        log.exception("AI 요약 중 예상치 못한 오류")
        brief.warnings.append(f"AI 요약 실패: {type(e).__name__}")
        return

    if response.stop_reason == "refusal":
        brief.warnings.append("AI 요약 거부됨 (safety). 데이터 섹션만 표시합니다.")
        return

    try:
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
    except (StopIteration, json.JSONDecodeError) as e:
        brief.warnings.append(f"AI 응답 파싱 실패: {type(e).__name__}")
        return

    brief.ai_summary = data.get("market_commentary")
    brief.sector_note = (data.get("sector_commentary") or "").strip() or None
    for item in data.get("headlines", []):
        i = item.get("index")
        if not (isinstance(i, int) and 0 <= i < len(groups)):
            continue
        note = (item.get("note") or "").strip()
        line = item.get("title_ko", "")
        if note:
            line += f" — {note}"
        for n in groups[i]:                   # 같은 기사끼리 번역을 공유
            n.summary_ko = line

    points = data.get("watch_points") or []
    if points:
        brief.ai_summary = (brief.ai_summary or "") + "\n\n**오늘의 관전 포인트**\n" + \
            "\n".join(f"- {p}" for p in points)

    usage = getattr(response, "usage", None)
    if usage:
        log.info("AI 토큰 사용: in=%s out=%s", usage.input_tokens, usage.output_tokens)
