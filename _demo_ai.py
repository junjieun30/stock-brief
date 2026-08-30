"""AI 요약이 켜졌을 때의 화면을 확인하기 위한 데모 렌더 (실제 API 호출 없음).

    python _demo_ai.py     →  report/demo-ai.html
"""
import json
import pathlib
import sys
import types
from unittest.mock import MagicMock, patch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from briefing.config import Config
from briefing.render import html as render_html
from briefing.summarize import _collect_headlines, summarize
import run as runner

cfg = Config.load()
cfg.secrets.anthropic = "sk-demo-not-a-real-key"
brief = runner.build_brief(cfg, use_ai=False)

groups = _collect_headlines(brief, cfg.get("ai", {}).get("max_headlines", 16))
print(f"번역 대상 그룹: {len(groups)}개 (시장뉴스 {len(brief.news)} + 종목뉴스 "
      f"{sum(len(v) for v in brief.ticker_news.values())})")

payload = {
    "market_commentary": (
        "전일 뉴욕증시는 기술주가 주도하며 3대 지수가 동반 상승 마감했다. "
        "나스닥 종합지수는 1.57% 오르며 상승폭이 가장 컸고, S&P 500도 0.72% 올랐다. "
        "섹터별로는 기술이 3.16% 급등한 반면 나머지 10개 섹터는 모두 하락해, "
        "지수 상승이 소수 대형 기술주에 집중됐다는 점이 드러났다. "
        "VIX는 4.6% 내린 14.51로 위험 선호 심리가 유지됐고, "
        "미국 10년물 금리는 4.67% 부근에서 큰 변동 없이 마감했다."),
    "sector_commentary": (
        "기술 섹터가 3.16% 급등하며 상승을 홀로 이끌었다. 엔비디아가 시장 예상을 웃돈 실적을 내놓은 "
        "여파가 반도체와 소프트웨어 전반으로 번진 영향이다. 반면 나머지 10개 섹터는 모두 내렸는데, "
        "금리가 4.67%대에 머물면서 유틸리티·부동산 같은 금리 민감 업종의 부담이 이어졌다."),
    "headlines": [
        {"index": i, "title_ko": f"[번역예시] {g[0].title[:38]}…",
         "note": "시장에 어떤 의미인지 한 문장" if i % 3 == 0 else ""}
        for i, g in enumerate(groups)
    ],
    "watch_points": [
        "오늘 밤 발표되는 미국 고용보고서",
        "브로드컴 실적 발표 이후 반도체 섹터 반응",
        "원/달러 환율의 1,370원선 지지 여부",
    ],
}

msg = MagicMock()
msg.stop_reason = "end_turn"
msg.content = [types.SimpleNamespace(type="text", text=json.dumps(payload, ensure_ascii=False))]
msg.usage = types.SimpleNamespace(input_tokens=0, output_tokens=0)
ctx = MagicMock()
ctx.__enter__.return_value.get_final_message.return_value = msg
client = MagicMock()
client.messages.stream.return_value = ctx

with patch("anthropic.Anthropic", return_value=client):
    summarize(brief, cfg)

translated_market = sum(1 for n in brief.news if n.summary_ko)
translated_ticker = sum(1 for v in brief.ticker_news.values() for n in v if n.summary_ko)
print(f"번역 적용 — 시장뉴스 {translated_market}/{len(brief.news)}, "
      f"종목뉴스 {translated_ticker}/{sum(len(v) for v in brief.ticker_news.values())}")

out = pathlib.Path("report/demo-ai.html")
out.write_text(render_html.render(brief), encoding="utf-8")
print("데모 렌더:", out, "| 경고:", brief.warnings or "없음")
