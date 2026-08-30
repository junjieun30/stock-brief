"""설정 로딩. config.yaml + .env 를 합쳐 하나의 Config 로 만든다."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Secrets:
    """API 키는 전부 .env 에서만 읽는다. 코드/리포트에 절대 기록하지 않는다."""
    anthropic: str | None = None
    finnhub: str | None = None
    alphavantage: str | None = None
    telegram_token: str | None = None
    telegram_chat: str | None = None

    @classmethod
    def load(cls) -> "Secrets":
        load_dotenv(ROOT / ".env")
        return cls(
            anthropic=os.getenv("ANTHROPIC_API_KEY") or None,
            finnhub=os.getenv("FINNHUB_API_KEY") or None,
            alphavantage=os.getenv("ALPHAVANTAGE_API_KEY") or None,
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat=os.getenv("TELEGRAM_CHAT_ID") or None,
        )


@dataclass
class Config:
    raw: dict[str, Any]
    secrets: Secrets = field(default_factory=Secrets.load)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        p = Path(path) if path else ROOT / "config.yaml"
        with open(p, encoding="utf-8") as f:
            return cls(raw=yaml.safe_load(f))

    # --- 편의 접근자 -------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)

    @property
    def indices(self) -> list[dict]:
        return self.raw["market"]["indices"]

    @property
    def macro(self) -> list[dict]:
        return self.raw["market"]["macro"]

    @property
    def global_indices(self) -> list[dict]:
        return self.raw["market"].get("global_indices", [])

    @property
    def fx(self) -> list[dict]:
        return self.raw["market"].get("fx", [])

    @property
    def sectors(self) -> list[dict]:
        return self.raw["market"]["sectors"]

    @property
    def watchlist(self) -> list[dict]:
        return self.raw.get("watchlist", [])

    @property
    def outdir(self) -> Path:
        # GitHub Actions 에서는 BRIEF_OUTPUT_DIR=docs 로 덮어써 Pages 가 서빙하게 한다
        name = os.getenv("BRIEF_OUTPUT_DIR") or self.raw["output"].get("dir", "report")
        d = ROOT / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def ai_enabled(self) -> bool:
        return bool(self.raw.get("ai", {}).get("enabled")) and bool(self.secrets.anthropic)
