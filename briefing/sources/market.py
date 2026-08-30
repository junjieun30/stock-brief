"""시세 수집. yfinance 를 1순위로 쓰고, 실패한 심볼만 Finnhub → Alpha Vantage 로 재시도한다."""
from __future__ import annotations

import logging
import time

import requests

from ..models import Quote

log = logging.getLogger(__name__)

# 무료 API 로는 못 가져오는 심볼(지수/선물/환율)은 fallback 대상에서 제외
_FALLBACK_SKIP_PREFIX = ("^",)
_FALLBACK_SKIP_SUFFIX = ("=X", "=F", "-USD", ".NYB")


def _fallback_eligible(symbol: str) -> bool:
    if symbol.startswith(_FALLBACK_SKIP_PREFIX):
        return False
    return not symbol.endswith(_FALLBACK_SKIP_SUFFIX)


# --------------------------------------------------------------------------
# provider 1 : yfinance
# --------------------------------------------------------------------------
def _yfinance_batch(symbols: list[str], want_52w: bool) -> tuple[dict[str, dict], str]:
    """{symbol: {price, prev_close, volume, year_high, year_low}} 와 기준일 문자열을 반환."""
    import yfinance as yf

    out: dict[str, dict] = {}
    market_date = ""
    if not symbols:
        return out, market_date

    try:
        hist = yf.download(
            symbols, period="1mo", interval="1d", progress=False,
            auto_adjust=False, group_by="ticker", threads=True,
        )
    except Exception as e:                                   # 네트워크/파싱 전면 실패
        log.warning("yfinance batch 실패: %s", e)
        return out, market_date

    if hist is None or len(hist) == 0:
        return out, market_date

    single = len(symbols) == 1

    for sym in symbols:
        try:
            frame = hist if single else hist[sym]
            closes = frame["Close"].dropna()
            if len(closes) < 2:
                continue
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            vols = frame["Volume"].dropna()
            rec = {
                "price": price,
                "prev_close": prev,
                "volume": float(vols.iloc[-1]) if len(vols) else None,
            }
            if want_52w:
                # 1개월치 데이터만 받았으므로 52주 고/저는 fast_info 로 별도 조회
                rec["year_high"] = rec["year_low"] = None
            out[sym] = rec
            if not market_date:
                market_date = str(closes.index[-1].date())
        except Exception as e:
            log.debug("yfinance %s 파싱 실패: %s", sym, e)

    if want_52w:
        _attach_52w(out)

    return out, market_date


def _attach_52w(recs: dict[str, dict]) -> None:
    """fast_info 로 52주 고/저를 채운다. 실패해도 리포트는 계속 나가야 하므로 조용히 넘어간다."""
    import yfinance as yf

    for sym, rec in recs.items():
        try:
            fi = yf.Ticker(sym).fast_info
            rec["year_high"] = fi.get("yearHigh")
            rec["year_low"] = fi.get("yearLow")
        except Exception as e:
            log.debug("52w %s 실패: %s", sym, e)


# --------------------------------------------------------------------------
# provider 2 : Finnhub
# --------------------------------------------------------------------------
def _finnhub(symbol: str, key: str) -> dict | None:
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": key},
            timeout=10,
        )
        r.raise_for_status()
        d = r.json()
        if not d.get("c"):
            return None
        return {"price": float(d["c"]), "prev_close": float(d["pc"]),
                "volume": None, "year_high": None, "year_low": None}
    except Exception as e:
        log.debug("finnhub %s 실패: %s", symbol, e)
        return None


# --------------------------------------------------------------------------
# provider 3 : Alpha Vantage  (무료 티어는 분당 5회 제한이라 마지막 수단)
# --------------------------------------------------------------------------
def _alphavantage(symbol: str, key: str) -> dict | None:
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": key},
            timeout=15,
        )
        r.raise_for_status()
        q = r.json().get("Global Quote") or {}
        if not q.get("05. price"):
            return None
        return {"price": float(q["05. price"]), "prev_close": float(q["08. previous close"]),
                "volume": float(q.get("06. volume") or 0) or None,
                "year_high": None, "year_low": None}
    except Exception as e:
        log.debug("alphavantage %s 실패: %s", symbol, e)
        return None


# --------------------------------------------------------------------------
# 공개 API
# --------------------------------------------------------------------------
def fetch_quotes(specs: list[dict], secrets, want_52w: bool = False) -> tuple[list[Quote], str]:
    """specs = [{symbol, name, unit?}, ...] → (Quote 리스트, 기준일)."""
    symbols = [s["symbol"] for s in specs]
    data, market_date = _yfinance_batch(symbols, want_52w)

    missing = [s for s in symbols if s not in data]
    if missing:
        eligible = [s for s in missing if _fallback_eligible(s)]
        if eligible and secrets.finnhub:
            log.info("Finnhub fallback: %s", ", ".join(eligible))
            for sym in eligible:
                rec = _finnhub(sym, secrets.finnhub)
                if rec:
                    rec["_source"] = "finnhub"
                    data[sym] = rec

        still = [s for s in missing if s not in data and _fallback_eligible(s)]
        if still and secrets.alphavantage:
            log.info("AlphaVantage fallback: %s", ", ".join(still[:5]))
            for i, sym in enumerate(still[:5]):          # 분당 5회 제한 준수
                if i:
                    time.sleep(13)
                rec = _alphavantage(sym, secrets.alphavantage)
                if rec:
                    rec["_source"] = "alphavantage"
                    data[sym] = rec

    quotes: list[Quote] = []
    for spec in specs:
        sym = spec["symbol"]
        q = Quote(symbol=sym, name=spec.get("name", sym), unit=spec.get("unit", ""),
                  change_mode=spec.get("change_mode", "pct"),
                  digits=spec.get("digits"))
        rec = data.get(sym)
        if not rec:
            q.error = "시세 조회 실패"
            quotes.append(q)
            continue
        q.source = rec.get("_source", "yfinance")
        q.price = rec["price"]
        q.prev_close = rec["prev_close"]
        q.volume = rec.get("volume")
        q.year_high = rec.get("year_high")
        q.year_low = rec.get("year_low")
        if q.prev_close:
            q.change = q.price - q.prev_close
            q.change_pct = q.change / q.prev_close * 100
        quotes.append(q)

    return quotes, market_date


def scan_movers(universe: list[str], secrets, top_n: int = 7) -> tuple[list[Quote], list[Quote]]:
    """유니버스를 스캔해 상승/하락 상위 종목을 뽑는다."""
    specs = [{"symbol": s, "name": s} for s in universe]
    quotes, _ = fetch_quotes(specs, secrets, want_52w=False)
    valid = [q for q in quotes if q.ok]
    valid.sort(key=lambda q: q.change_pct, reverse=True)
    return valid[:top_n], list(reversed(valid[-top_n:]))
