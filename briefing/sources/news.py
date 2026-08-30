"""RSS 기반 해외 시장 뉴스 헤드라인 수집."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from ..models import NewsItem

log = logging.getLogger(__name__)

_TAG = re.compile(r"<[^>]+>")


def _parse_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _clean(text: str) -> str:
    return _TAG.sub("", text or "").strip()


def _balance(items: list[NewsItem], feed_order: list[str]) -> list[NewsItem]:
    """소스별로 한 건씩 번갈아 뽑는다. 각 소스 안에서는 최신순이 유지된다."""
    buckets: dict[str, list[NewsItem]] = {name: [] for name in feed_order}
    for n in items:
        buckets.setdefault(n.source, []).append(n)

    out: list[NewsItem] = []
    while any(buckets.values()):
        for name in list(buckets):
            if buckets[name]:
                out.append(buckets[name].pop(0))
    return out


def _compile(patterns: list[str] | None) -> list:
    out = []
    for p in patterns or []:
        try:
            out.append(re.compile(p, re.IGNORECASE))
        except re.error as e:
            log.warning("exclude_patterns 정규식 오류 (%s): %s", p, e)
    return out


def fetch_news(feeds: list[dict], max_items: int = 14, lookback_hours: int = 30,
               exclude_patterns: list[str] | None = None) -> tuple[list[NewsItem], list[str]]:
    """피드들을 돌며 최근 기사만 모으고, 중복과 비시장성 칼럼을 걸러낸다."""
    import feedparser

    excludes = _compile(exclude_patterns)
    dropped = 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items: list[NewsItem] = []
    seen: set[str] = set()
    warnings: list[str] = []

    for feed in feeds:
        name, url = feed.get("name", "?"), feed["url"]
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            warnings.append(f"뉴스 피드 실패 [{name}]: {e}")
            continue

        if not parsed.entries:
            warnings.append(f"뉴스 피드 비어 있음 [{name}]")
            continue

        for entry in parsed.entries:
            title = _clean(getattr(entry, "title", ""))
            if not title:
                continue
            if any(rx.search(title) for rx in excludes):   # 개인 재무상담·라이프스타일 칼럼
                dropped += 1
                continue
            key = re.sub(r"[^a-z0-9]", "", title.lower())[:60]
            if key in seen:
                continue
            published = _parse_time(entry)
            if published and published < cutoff:
                continue
            seen.add(key)
            items.append(NewsItem(
                title=title,
                url=getattr(entry, "link", ""),
                source=name,
                published=published,
            ))

    # 최신순 정렬 (시간 없는 항목은 뒤로)
    items.sort(key=lambda n: n.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # 한 피드가 목록을 독점하지 않도록 소스별 라운드로빈으로 섞는다
    items = _balance(items, [f.get("name", "?") for f in feeds])

    if dropped:
        log.info("비시장성 기사 %d건 제외", dropped)
    if not items:
        warnings.append("수집된 뉴스가 없습니다 — lookback_hours 를 늘려보세요.")

    return items[:max_items], warnings


def fetch_ticker_news(watchlist: list[dict], per_ticker: int = 2,
                      lookback_hours: int = 48) -> dict[str, list[NewsItem]]:
    """관심 종목별 뉴스. yfinance 가 종목에 태깅된 기사를 준다.

    전체 시장 뉴스와 달리 '내가 담은 종목에 무슨 일이 있었나'만 본다.
    """
    import yfinance as yf

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    out: dict[str, list[NewsItem]] = {}

    for spec in watchlist:
        sym = spec["symbol"]
        try:
            raw = yf.Ticker(sym).news or []
        except Exception as e:
            log.debug("종목 뉴스 실패 %s: %s", sym, e)
            continue

        items: list[NewsItem] = []
        for entry in raw:
            c = entry.get("content") or entry
            title = _clean(c.get("title") or "")
            if not title:
                continue
            url = ((c.get("canonicalUrl") or {}).get("url")
                   or (c.get("clickThroughUrl") or {}).get("url")
                   or entry.get("link") or "")
            published = None
            stamp = c.get("pubDate") or c.get("displayTime")
            if stamp:
                try:
                    published = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                except ValueError:
                    pass
            if published and published < cutoff:
                continue
            provider = (c.get("provider") or {}).get("displayName") or "Yahoo"
            items.append(NewsItem(title=title, url=url, source=provider, published=published))
            if len(items) >= per_ticker:
                break

        if items:
            out[sym] = items

    return out
