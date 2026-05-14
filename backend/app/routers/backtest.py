from fastapi import APIRouter, Query

from app.services.backtest_engine import run_backtest
from app.services.data_fetcher import bars_to_frame, get_ohlcv

router = APIRouter(tags=["backtest"])


@router.post("/backtest")
async def backtest(
    ticker: str = "NOW",
    strategy: str = "composite",
    from_: str = Query("2022-01-01", alias="from"),
    to: str = "2024-12-31",
    initial_capital: float = 10000,
):
    bars = await get_ohlcv(ticker, "5y", "1d")
    df = bars_to_frame(bars)
    df = df[(df["date"] >= from_) & (df["date"] <= to)]
    if len(df) < 80:
        df = bars_to_frame(bars).tail(500)
    return run_backtest(df, strategy, initial_capital)
