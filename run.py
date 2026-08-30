#!/usr/bin/env python
"""해외 주식 데일리 브리핑 생성기.

    python run.py                # 전체 실행 → report/latest.html + 날짜별 파일
    python run.py --open         # 만든 뒤 브라우저로 열기
    python run.py --no-ai        # Claude 요약 없이 데이터만
    python run.py --telegram     # 텔레그램으로도 전송
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Windows 기본 콘솔은 cp949 라서 →, ⚠ 같은 기호에서 로그가 깨진다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

from briefing.config import Config
from briefing.data.universe import DEFAULT_UNIVERSE
from briefing.models import Brief
from briefing.render import html as render_html
from briefing.render import markdown as render_md
from briefing.sources.market import fetch_quotes, scan_movers
from briefing.sources.news import fetch_news

KST = timezone(timedelta(hours=9))
log = logging.getLogger("briefing")


def _now_kst() -> datetime:
    return datetime.now(KST)


def build_brief(cfg: Config, *, use_ai: bool = True, use_news: bool = True,
                use_movers: bool = True) -> Brief:
    brief = Brief(generated_at=_now_kst())

    log.info("지수 · 매크로 수집 중…")
    quotes, market_date = fetch_quotes(cfg.indices + cfg.macro, cfg.secrets)
    n_idx = len(cfg.indices)
    brief.indices, brief.macro = quotes[:n_idx], quotes[n_idx:]
    brief.market_date = market_date

    log.info("섹터 ETF 수집 중…")
    brief.sectors, _ = fetch_quotes(cfg.sectors, cfg.secrets)

    if cfg.watchlist:
        log.info("관심 종목 %d개 수집 중…", len(cfg.watchlist))
        brief.watchlist, _ = fetch_quotes(cfg.watchlist, cfg.secrets, want_52w=True)

    if use_movers:
        mv = cfg.get("movers", {})
        universe = DEFAULT_UNIVERSE if mv.get("universe", "default") == "default" \
            else mv.get("universe", DEFAULT_UNIVERSE)
        log.info("상승/하락 상위 스캔 중… (%d종목)", len(universe))
        brief.gainers, brief.losers = scan_movers(universe, cfg.secrets, mv.get("top_n", 7))

    if use_news:
        nc = cfg.get("news", {})
        log.info("뉴스 수집 중…")
        brief.news, warns = fetch_news(
            nc.get("feeds", []), nc.get("max_items", 14), nc.get("lookback_hours", 30),
            nc.get("exclude_patterns"),
        )
        brief.warnings += warns

    failed = [q.name for q in brief.indices + brief.macro + brief.sectors + brief.watchlist
              if not q.ok]
    if failed:
        brief.warnings.append("시세 조회 실패: " + ", ".join(failed))

    if use_ai:
        from briefing.summarize import summarize
        log.info("Claude 요약 생성 중… (모델 %s)", cfg.get("ai", {}).get("model"))
        t0 = time.time()
        summarize(brief, cfg)
        log.info("요약 완료 (%.1fs)", time.time() - t0)

    return brief


def write_outputs(brief: Brief, cfg: Config) -> dict[str, Path]:
    outdir = cfg.outdir
    stamp = brief.generated_at.strftime("%Y-%m-%d")
    formats = cfg.get("output", {}).get("formats", ["html"])
    written: dict[str, Path] = {}

    if "html" in formats:
        content = render_html.render(brief)
        dated = outdir / f"brief-{stamp}.html"
        dated.write_text(content, encoding="utf-8")
        latest = outdir / "latest.html"          # 로컬 브라우저 시작페이지용 고정 경로
        latest.write_text(content, encoding="utf-8")
        index = outdir / "index.html"            # GitHub Pages 진입점
        index.write_text(content, encoding="utf-8")
        written["html"], written["latest"] = dated, latest

    if "markdown" in formats:
        dated = outdir / f"brief-{stamp}.md"
        dated.write_text(render_md.render(brief), encoding="utf-8")
        written["markdown"] = dated

    _cleanup(outdir, cfg.get("output", {}).get("keep_days", 60))
    if "html" in formats:
        written["archive"] = _write_archive(outdir)
    return written


ARCHIVE_TPL = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>지난 브리핑</title><style>
:root{{--bg:#f6f7f9;--panel:#fff;--line:#e3e6ea;--ink:#141821;--muted:#6b7480;--accent:#3d5afe}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0e1116;--panel:#161b22;--line:#252c36;
--ink:#e6eaf0;--muted:#8d97a5;--accent:#7c8cff}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.6;
font-family:"Pretendard","Malgun Gothic",-apple-system,"Segoe UI",sans-serif}}
.wrap{{max-width:640px;margin:0 auto;padding:32px 20px 60px}}
h1{{font-size:20px;margin:0 0 6px}}
.sub{{color:var(--muted);font-size:13px;margin-bottom:22px}}
ul{{list-style:none;margin:0;padding:0;background:var(--panel);border:1px solid var(--line);
border-radius:12px;overflow:hidden}}
li{{border-bottom:1px solid var(--line)}} li:last-child{{border-bottom:none}}
a{{display:block;padding:12px 18px;color:var(--ink);text-decoration:none}}
a:hover{{background:color-mix(in srgb,var(--accent) 6%,transparent);color:var(--accent)}}
.top{{display:inline-block;margin-bottom:18px;color:var(--accent);text-decoration:none;font-size:13px}}
</style></head><body><div class="wrap">
<a class="top" href="./index.html">← 오늘 브리핑으로</a>
<h1>지난 브리핑</h1><div class="sub">최근 {n}건</div>
<ul>{rows}</ul></div></body></html>"""


def _write_archive(outdir: Path) -> Path:
    """지난 리포트 목록 페이지. Pages 에 쌓인 날짜별 파일을 훑어 만든다."""
    files = sorted(outdir.glob("brief-*.html"), reverse=True)
    rows = "".join(
        f'<li><a href="./{f.name}">{f.stem.replace("brief-", "")}</a></li>' for f in files
    ) or "<li><a>아직 없습니다</a></li>"
    path = outdir / "archive.html"
    path.write_text(ARCHIVE_TPL.format(n=len(files), rows=rows), encoding="utf-8")
    return path


def _cleanup(outdir: Path, keep_days: int) -> None:
    if not keep_days:
        return
    cutoff = time.time() - keep_days * 86400
    for f in outdir.glob("brief-*"):
        if f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)
            log.debug("오래된 리포트 삭제: %s", f.name)


def main() -> int:
    ap = argparse.ArgumentParser(description="해외 주식 데일리 브리핑 생성")
    ap.add_argument("--config", help="config.yaml 경로")
    ap.add_argument("--no-ai", action="store_true", help="Claude 요약 생략")
    ap.add_argument("--no-news", action="store_true", help="뉴스 수집 생략")
    ap.add_argument("--no-movers", action="store_true", help="상승/하락 상위 스캔 생략 (빠름)")
    ap.add_argument("--telegram", action="store_true", help="텔레그램으로도 전송")
    ap.add_argument("--open", action="store_true", help="생성 후 브라우저로 열기")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("yfinance").setLevel(logging.ERROR)

    cfg = Config.load(args.config)
    brief = build_brief(
        cfg,
        use_ai=not args.no_ai,
        use_news=not args.no_news,
        use_movers=not args.no_movers,
    )

    if args.telegram or cfg.get("telegram", {}).get("enabled"):
        from briefing.deliver.telegram import send
        warn = send(brief, cfg.secrets)
        if warn:
            brief.warnings.append(warn)

    written = write_outputs(brief, cfg)
    for kind, path in written.items():
        log.info("%-8s → %s", kind, path)

    for w in brief.warnings:
        log.warning("⚠ %s", w)

    if args.open and "latest" in written:
        webbrowser.open(written["latest"].as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
