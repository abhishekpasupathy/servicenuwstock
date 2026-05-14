import asyncio
import math
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import numpy as np
import pandas as pd
import yfinance as yf

from app.cache import cache_get, cache_set
from app.config import get_settings


settings = get_settings()
DEMO_PRICE = 85.0


def _ticker(ticker: str) -> str:
    value = ticker.strip().upper()
    if not value or len(value) > 12:
        raise ValueError("Invalid ticker")
    return value


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except Exception:
        return default


def _int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


async def _retry(fn, retries: int = 3):
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return await asyncio.to_thread(fn)
        except Exception as exc:
            last = exc
            await asyncio.sleep(0.4 * (2**attempt))
    raise RuntimeError(str(last))


async def _alpha_daily(ticker: str) -> pd.DataFrame:
    if not settings.alpha_vantage_key:
        raise RuntimeError("Alpha Vantage key not configured")
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": ticker,
        "apikey": settings.alpha_vantage_key,
        "outputsize": "full",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        data = (await client.get("https://www.alphavantage.co/query", params=params)).json()
    series = data.get("Time Series (Daily)")
    if not series:
        raise RuntimeError(data.get("Note") or data.get("Error Message") or "Alpha Vantage failed")
    rows = [
        {
            "date": k,
            "open": float(v["1. open"]),
            "high": float(v["2. high"]),
            "low": float(v["3. low"]),
            "close": float(v["4. close"]),
            "volume": int(v["6. volume"]),
        }
        for k, v in series.items()
    ]
    return pd.DataFrame(rows).sort_values("date")


def _demo_bars(days: int = 520) -> list[dict[str, Any]]:
    start = datetime.now(UTC).date() - timedelta(days=days)
    bars: list[dict[str, Any]] = []
    for i in range(days):
        if i % 7 in (5, 6):
            continue
        wave = math.sin(i / 18) * 1.4 + math.sin(i / 55) * 2.4
        close = max(20, DEMO_PRICE + wave)
        open_ = close * (1 + math.sin(i) * 0.004)
        high = max(open_, close) * 1.01
        low = min(open_, close) * 0.99
        bars.append(
            {
                "date": str(start + timedelta(days=i)),
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": int(1_350_000 + (math.sin(i / 9) + 1) * 450_000),
            }
        )
    return bars


async def get_ohlcv(ticker: str, period: str = "1y", interval: str = "1d") -> list[dict[str, Any]]:
    ticker = _ticker(ticker)
    ttl = settings.cache_ohlcv_ttl if interval == "1d" else 3600
    key = f"ohlcv:{ticker}:{period}:{interval}"
    cached = await cache_get(key)
    if cached:
        return cached
    stale_key = f"stale:{key}"
    try:
        frame = await _retry(lambda: yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False))
        if frame.empty:
            raise RuntimeError("empty yfinance history")
        frame = frame.reset_index()
        bars = [
            {
                "date": str((row.get("Date") or row.get("Datetime")).date()),
                "open": _num(row["Open"], 0),
                "high": _num(row["High"], 0),
                "low": _num(row["Low"], 0),
                "close": _num(row["Close"], 0),
                "volume": _int(row["Volume"], 0),
            }
            for _, row in frame.iterrows()
        ]
        for bar in bars:
            bar["source"] = "yfinance"
        await cache_set(key, bars, ttl)
        await cache_set(stale_key, bars, 86400 * 7)
        return bars
    except Exception:
        try:
            frame = await _alpha_daily(ticker)
            if period != "max":
                days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}.get(period, 365)
                frame = frame.tail(days)
            bars = frame.to_dict("records")
            for bar in bars:
                bar["source"] = "alpha_vantage"
            await cache_set(key, bars, ttl)
            await cache_set(stale_key, bars, 86400 * 7)
            return bars
        except Exception:
            stale = await cache_get(stale_key)
            if stale:
                return [{**bar, "source": "cache", "stale": True} for bar in stale]
            return [{**bar, "source": "demo", "stale": True} for bar in _demo_bars()]


async def get_quote(ticker: str) -> dict[str, Any]:
    ticker = _ticker(ticker)
    key = f"quote:{ticker}"
    cached = await cache_get(key)
    if cached:
        return cached
    stale_key = f"stale:{key}"
    try:
        info = await _retry(lambda: yf.Ticker(ticker).info)
        price = _num(info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"), DEMO_PRICE)
        prev = _num(info.get("previousClose"), price)
        quote = {
            "ticker": ticker,
            "price": price,
            "change": round((price or 0) - (prev or 0), 2),
            "change_pct": round((((price or 0) - (prev or 0)) / (prev or 1)) * 100, 2),
            "volume": _int(info.get("volume"), 0),
            "avg_volume": _int(info.get("averageVolume"), 0),
            "market_cap": _int(info.get("marketCap"), 0),
            "pe_ratio": _num(info.get("trailingPE") or info.get("forwardPE")),
            "week_52_high": _num(info.get("fiftyTwoWeekHigh"), (price or DEMO_PRICE) * 1.25),
            "week_52_low": _num(info.get("fiftyTwoWeekLow"), (price or DEMO_PRICE) * 0.72),
            "day_high": _num(info.get("dayHigh"), (price or DEMO_PRICE) * 1.01),
            "day_low": _num(info.get("dayLow"), (price or DEMO_PRICE) * 0.99),
            "prev_close": prev,
            "open": _num(info.get("open"), prev),
            "source": "yfinance",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await cache_set(key, quote, settings.cache_quote_ttl)
        await cache_set(stale_key, quote, 86400 * 7)
        return quote
    except Exception:
        stale = await cache_get(stale_key)
        if stale:
            return {**stale, "source": "cache", "stale": True}
        bars = await get_ohlcv(ticker)
        last = bars[-1]
        prev = bars[-2]["close"]
        price = float(last["close"])
        recent = bars[-252:] if len(bars) >= 252 else bars
        return {
            "ticker": ticker,
            "price": price,
            "change": round(price - prev, 2),
            "change_pct": round((price - prev) / prev * 100, 2),
            "volume": last["volume"],
            "avg_volume": int(np.mean([b["volume"] for b in bars[-20:]])),
            "market_cap": 17_500_000_000,
            "pe_ratio": 38.0,
            "week_52_high": round(max(float(b["high"]) for b in recent), 2),
            "week_52_low": round(min(float(b["low"]) for b in recent), 2),
            "day_high": round(max(float(last["high"]), price), 2),
            "day_low": round(min(float(last["low"]), price), 2),
            "prev_close": prev,
            "open": last["open"],
            "source": "demo",
            "stale": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }


async def get_fundamentals(ticker: str) -> dict[str, Any]:
    ticker = _ticker(ticker)
    key = f"fundamentals:{ticker}"
    cached = await cache_get(key)
    if cached:
        return cached
    try:
        info = await _retry(lambda: yf.Ticker(ticker).info)
        data = {
            "ticker": ticker,
            "pe": _num(info.get("trailingPE") or info.get("forwardPE"), 38.0),
            "eps": _num(info.get("trailingEps"), 2.1),
            "revenue_growth_yoy": _num(info.get("revenueGrowth"), 0.21),
            "gross_margin": _num(info.get("grossMargins"), 0.78),
            "operating_margin": _num(info.get("operatingMargins"), 0.12),
            "debt_to_equity": _num(info.get("debtToEquity"), 0.0),
            "current_ratio": _num(info.get("currentRatio"), 1.1),
            "return_on_equity": _num(info.get("returnOnEquity"), 0.18),
            "beta": _num(info.get("beta"), 1.05),
            "sector": info.get("sector") or "Technology",
            "employees": _int(info.get("fullTimeEmployees"), None),
            "source": "yfinance",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception:
        data = {
            "ticker": ticker,
            "pe": 38.0,
            "eps": 2.1,
            "revenue_growth_yoy": 0.21,
            "gross_margin": 0.78,
            "operating_margin": 0.12,
            "debt_to_equity": 0.32,
            "current_ratio": 1.1,
            "return_on_equity": 0.18,
            "beta": 1.05,
            "sector": "Technology",
            "employees": 26000,
            "source": "demo",
            "stale": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    await cache_set(key, data, settings.cache_fundamentals_ttl)
    return data


def bars_to_frame(bars: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(bars).rename(columns=str.lower)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["close"]).reset_index(drop=True)
