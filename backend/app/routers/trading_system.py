import asyncio
import time
from typing import Any

from fastapi import APIRouter

from app.services.data_fetcher import _fast_get, _fast_set, bars_to_frame, get_ohlcv, get_quote
from app.services.trading_system import run_full_trading_system

router = APIRouter(tags=["trading-system"])

_TRADING_SYSTEM_CACHE_TTL = 120  # 2 minutes


@router.get("/trading-system/{ticker}")
async def trading_system(
    ticker: str,
    portfolio_value: float = 1_000_000,
    deployed_capital: float = 0,
    trend_confirmed: bool = False,
    days_since_last_entry: int = 30,
    last_entry_price: float = 95.0,
    sector_exposure_pct: float = 0.10,
    fed_rate_path: str = "HOLD",
    ism_reading: float = 50.0,
    credit_spread: float = 100.0,
    portfolio_correlation: float = 0.60,
):
    ticker = ticker.strip().upper()
    cache_key = f"trading_system:{ticker}:{portfolio_value}"
    cached = _fast_get(cache_key, _TRADING_SYSTEM_CACHE_TTL)
    if cached:
        return cached

    # Parallel fetch: OHLCV + quote at the same time
    bars, quote = await asyncio.gather(
        get_ohlcv(ticker, "2y", "1d"),
        get_quote(ticker),
    )
    df = bars_to_frame(bars)
    result = run_full_trading_system(
        df,
        float(quote["price"]),
        portfolio_value,
        deployed_capital,
        trend_confirmed,
        days_since_last_entry,
        last_entry_price,
        sector_exposure_pct,
        fed_rate_path,
        ism_reading,
        credit_spread,
        portfolio_correlation,
    )
    _fast_set(cache_key, result, _TRADING_SYSTEM_CACHE_TTL)
    return result
