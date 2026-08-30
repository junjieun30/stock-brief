"""리포트를 구성하는 데이터 모델."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Quote:
    """한 종목/지수의 전일 마감 스냅샷."""
    symbol: str
    name: str
    price: float | None = None
    prev_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    year_high: float | None = None
    year_low: float | None = None
    unit: str = ""
    digits: int | None = None   # 표시 소수점 자리수 (환율처럼 정밀도가 필요한 경우)
    change_mode: str = "pct"   # "pct" = 등락률, "bp" = 금리 변동폭(베이시스포인트)
    source: str = ""          # 어느 provider 에서 왔는지 (fallback 추적용)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.change_pct is not None

    @property
    def direction(self) -> str:
        if self.change_pct is None:
            return "flat"
        if self.change_pct > 0:
            return "up"
        if self.change_pct < 0:
            return "down"
        return "flat"

    @property
    def pct_from_high(self) -> float | None:
        """52주 고점 대비 위치(%). -12.3 이면 고점 대비 12.3% 아래."""
        if self.price and self.year_high:
            return (self.price / self.year_high - 1) * 100
        return None

    @property
    def range_position(self) -> float | None:
        """52주 레인지 내 위치 0~100."""
        if self.price and self.year_high and self.year_low and self.year_high > self.year_low:
            return (self.price - self.year_low) / (self.year_high - self.year_low) * 100
        return None


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published: datetime | None = None
    summary_ko: str | None = None   # Claude 가 채움


@dataclass
class CalendarEvent:
    """앞으로 예정된 일정. 예측이 아니라 공표된 사실만 담는다."""
    day: date
    kind: str                  # "macro" | "earnings"
    title: str
    detail: str = ""
    source: str = ""

    def d_day(self, today: date) -> str:
        n = (self.day - today).days
        return "오늘" if n == 0 else ("내일" if n == 1 else f"D-{n}")


@dataclass
class Alert:
    """관심 종목의 급등락. 임계값을 넘은 것만 만든다."""
    quote: Quote
    threshold: float

    @property
    def direction(self) -> str:
        return self.quote.direction


@dataclass
class FutureChapter:
    """내일의 기술 — 미래학자들이 말한 흐름을 책 한 챕터처럼 읽는 자리."""
    part: str                  # "1부 · 계산하는 기계" 등
    title: str
    subtitle: str
    horizon: str               # "이미 진행 중" / "5~10년" / "10년 이상"
    body: tuple[str, ...]      # 본문 문단들
    voices: str                # 누가 어떤 관점으로 봤나
    counter: str               # 다르게 보는 시각
    where: str                 # 어느 산업에서 관찰되는가
    number: int = 0            # 오늘이 몇 번째 편인지
    total: int = 0


@dataclass
class Lesson:
    """주식 용어 · 투자 심리 학습 카드."""
    term: str
    kind: str                  # "term" | "psychology"
    plain: str                 # 쉬운 설명
    why: str                   # 왜 알아둬야 하는지


@dataclass
class Brief:
    """하루치 브리핑 전체."""
    generated_at: datetime
    market_date: str = ""
    indices: list[Quote] = field(default_factory=list)
    global_indices: list[Quote] = field(default_factory=list)
    fx: list[Quote] = field(default_factory=list)
    macro: list[Quote] = field(default_factory=list)
    sectors: list[Quote] = field(default_factory=list)
    watchlist: list[Quote] = field(default_factory=list)
    gainers: list[Quote] = field(default_factory=list)
    losers: list[Quote] = field(default_factory=list)
    news: list[NewsItem] = field(default_factory=list)
    ai_summary: str | None = None       # 시장 총평 (한국어)
    calendar: list[CalendarEvent] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    ticker_news: dict[str, list[NewsItem]] = field(default_factory=dict)
    lessons: list[Lesson] = field(default_factory=list)
    future: FutureChapter | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def has_ai(self) -> bool:
        return bool(self.ai_summary)
