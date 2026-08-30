"""앞으로 예정된 일정 수집 — FOMC, 관심종목 실적발표, 사용자 지정 이벤트.

가격 전망은 다루지 않는다. 확정되어 공표된 '언제 무슨 일이 있는지'만 모은다.
BLS(고용·CPI)는 봇 차단(403)이라 긁을 수 없어, 통상 규칙과 사용자 지정 목록으로 채운다.
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

import requests

from ..models import CalendarEvent

log = logging.getLogger(__name__)

FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], start=1)}

# 페이지는 연도별 panel 안에 회의가 한 줄씩 들어 있다.
#   <div class="fomc-meeting__month ..."><strong>January</strong></div>
#   <div class="fomc-meeting__date  ...">27-28</div>
_PANEL_YEAR = re.compile(r'<h4><a id="\d+">(\d{4}) FOMC Meetings</a></h4>')
_ROW = re.compile(
    r'fomc-meeting__month[^>]*>\s*(?:<strong>)?\s*([A-Z][a-z]+)\s*(?:</strong>)?\s*</div>'
    r'.*?fomc-meeting__date[^>]*>\s*([^<]+?)\s*</div>',
    re.S,
)
# "27-28" / "17-18*" / "31-February 1" / "29"
_SPAN = re.compile(r'^(\d{1,2})(?:\s*[-–]\s*(?:([A-Z][a-z]+)\s+)?(\d{1,2}))?\*?$')


def _parse_span(year: int, month: str, text: str) -> tuple[date, date] | None:
    m = _SPAN.match(text.strip())
    if not m or month not in MONTHS:
        return None
    d1, end_month, d2 = m.groups()
    try:
        start = date(year, MONTHS[month], int(d1))
        if not d2:
            return start, start
        end = date(year, MONTHS[end_month] if end_month else MONTHS[month], int(d2))
        if end < start:                       # 12/31-1/1 처럼 해를 넘기는 경우
            end = date(year + 1, end.month, end.day)
        return start, end
    except (ValueError, KeyError):
        return None


def fetch_fomc(today: date, horizon_days: int) -> list[CalendarEvent]:
    """연준 공식 캘린더에서 다가오는 FOMC 회의를 읽는다."""
    try:
        r = requests.get(FOMC_URL, headers=UA, timeout=20)
        r.raise_for_status()
    except Exception as e:
        log.warning("FOMC 일정 조회 실패: %s", e)
        return []

    # 연도 패널 경계를 잡아 각 회의 줄이 어느 해에 속하는지 정한다
    marks = [(m.start(), int(m.group(1))) for m in _PANEL_YEAR.finditer(r.text)]
    if not marks:
        log.warning("FOMC 페이지 구조가 바뀐 듯합니다 — 일정 건너뜀")
        return []

    limit = today + timedelta(days=horizon_days)
    events: list[CalendarEvent] = []
    seen: set[date] = set()

    for row in _ROW.finditer(r.text):
        year = next((y for pos, y in reversed(marks) if pos < row.start()), None)
        if year is None:
            continue
        span = _parse_span(year, row.group(1), row.group(2))
        if not span:
            continue
        start, end = span
        if not (today <= end <= limit) or end in seen:
            continue
        seen.add(end)
        label = f"{start.month}/{start.day}" + (f"~{end.month}/{end.day}" if end != start else "")
        events.append(CalendarEvent(
            day=end, kind="macro", title="FOMC 정례회의",
            detail=f"{label} · 결과 발표는 마지막 날 (한국시간 다음날 새벽)",
            source="연준",
        ))
    return events


def first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def recurring_macro(today: date, horizon_days: int) -> list[CalendarEvent]:
    """날짜 규칙이 확실한 지표만. 미국 고용보고서는 통상 매월 첫째 금요일에 나온다."""
    events: list[CalendarEvent] = []
    limit = today + timedelta(days=horizon_days)
    y, m = today.year, today.month
    for _ in range(4):
        d = first_friday(y, m)
        if today <= d <= limit:
            events.append(CalendarEvent(
                day=d, kind="macro", title="미국 고용보고서 (비농업 고용)",
                detail="통상 매월 첫째 금요일 · 한국시간 밤 9시 30분", source="통상 일정",
            ))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return events


def fetch_earnings(watchlist: list[dict], today: date, horizon_days: int) -> list[CalendarEvent]:
    """관심 종목의 다음 실적 발표일."""
    import yfinance as yf

    limit = today + timedelta(days=horizon_days)
    events: list[CalendarEvent] = []
    for spec in watchlist:
        sym = spec["symbol"]
        try:
            cal = yf.Ticker(sym).calendar or {}
            dates = cal.get("Earnings Date") or []
        except Exception as e:
            log.debug("실적일 조회 실패 %s: %s", sym, e)
            continue

        for d in dates:
            if not isinstance(d, date):
                continue
            if today <= d <= limit:
                est = cal.get("Earnings Average")
                detail = f"주당순이익(EPS) 시장 예상 {est:.2f}달러" if isinstance(est, (int, float)) else ""
                events.append(CalendarEvent(
                    day=d, kind="earnings",
                    title=f"{spec.get('name', sym)} 실적 발표",
                    detail=detail, source=sym,
                ))
                break            # 가장 가까운 1건만
    return events


def user_events(entries: list[dict], today: date, horizon_days: int) -> list[CalendarEvent]:
    """config.yaml 의 calendar.events 항목 — 직접 관리하는 일정."""
    limit = today + timedelta(days=horizon_days)
    out: list[CalendarEvent] = []
    for e in entries or []:
        d = e.get("date")
        if not isinstance(d, date):
            log.warning("일정 날짜 형식 오류 (YYYY-MM-DD 로 적어주세요): %r", e)
            continue
        if today <= d <= limit:
            out.append(CalendarEvent(day=d, kind="macro", title=e.get("title", "일정"),
                                     detail=e.get("detail", ""), source="직접 등록"))
    return out


def collect(cfg, today: date) -> list[CalendarEvent]:
    """모든 소스를 합쳐 날짜순으로 돌려준다."""
    cc = cfg.get("calendar", {}) or {}
    if not cc.get("enabled", True):
        return []
    horizon = cc.get("horizon_days", 10)

    events: list[CalendarEvent] = []
    if cc.get("fomc", True):
        events += fetch_fomc(today, horizon)
    if cc.get("recurring_macro", True):
        events += recurring_macro(today, horizon)
    if cc.get("earnings", True):
        events += fetch_earnings(cfg.watchlist, today, horizon)
    events += user_events(cc.get("events"), today, horizon)

    events.sort(key=lambda e: (e.day, e.kind != "macro", e.title))
    return events
