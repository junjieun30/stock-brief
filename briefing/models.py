"""리포트를 구성하는 데이터 모델."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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
class Brief:
    """하루치 브리핑 전체."""
    generated_at: datetime
    market_date: str = ""
    indices: list[Quote] = field(default_factory=list)
    macro: list[Quote] = field(default_factory=list)
    sectors: list[Quote] = field(default_factory=list)
    watchlist: list[Quote] = field(default_factory=list)
    gainers: list[Quote] = field(default_factory=list)
    losers: list[Quote] = field(default_factory=list)
    news: list[NewsItem] = field(default_factory=list)
    ai_summary: str | None = None       # 시장 총평 (한국어)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_ai(self) -> bool:
        return bool(self.ai_summary)
