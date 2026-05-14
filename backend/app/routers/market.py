from fastapi import APIRouter

from app.services.data_fetcher import get_fundamentals, get_ohlcv, get_quote
from app.services.market_data import (
    get_history as get_market_history,
    get_profile as get_market_profile,
    get_quote as get_market_quote,
    get_snapshot,
)
from app.services.market_hours import get_market_status

router = APIRouter(tags=["market"])


@router.get("/market/quote/{ticker}")
async def market_quote(ticker: str):
    return await get_quote(ticker)


@router.get("/market/ohlcv/{ticker}")
async def market_ohlcv(ticker: str, period: str = "1y", interval: str = "1d"):
    return await get_ohlcv(ticker, period, interval)


@router.get("/market/fundamentals/{ticker}")
async def market_fundamentals(ticker: str):
    return await get_fundamentals(ticker)


@router.get("/quote/{ticker}")
async def legacy_quote(ticker: str):
    return get_market_quote(ticker)


@router.get("/history/{ticker}")
async def legacy_history(ticker: str, period: str = "1y", interval: str = "1d"):
    return get_market_history(ticker, period, interval)


@router.get("/profile/{ticker}")
async def profile(ticker: str):
    return get_market_profile(ticker)


@router.get("/snapshot/{ticker}")
async def snapshot(ticker: str, period: str = "1y", interval: str = "1d"):
    return get_snapshot(ticker, period, interval)


@router.get("/market/status")
async def market_status():
    return get_market_status()
