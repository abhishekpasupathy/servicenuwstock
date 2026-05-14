from fastapi import APIRouter

from app.services.data_fetcher import get_fundamentals, get_ohlcv, get_quote

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
    return await get_quote(ticker)


@router.get("/history/{ticker}")
async def legacy_history(ticker: str, period: str = "1y", interval: str = "1d"):
    return {"ticker": ticker.upper(), "period": period, "interval": interval, "points": await get_ohlcv(ticker, period, interval)}
