from fastapi import APIRouter, Query

from app.services.data_fetcher import bars_to_frame, get_ohlcv, get_quote
from app.services.monte_carlo import run_monte_carlo
from app.services.quant_engine import compute_all_indicators
from app.services.risk_engine import compute_risk_metrics
from app.services.signal_engine import generate_signals

router = APIRouter(tags=["risk"])


@router.get("/risk/{ticker}")
async def risk(ticker: str):
    bars = await get_ohlcv(ticker, "2y", "1d")
    spy_bars = await get_ohlcv("SPY", "2y", "1d")
    quote = await get_quote(ticker)
    quant = compute_all_indicators(bars_to_frame(bars))
    sig = generate_signals(quant, quote["price"])
    return compute_risk_metrics(bars_to_frame(bars), bars_to_frame(spy_bars), sig["buy_prob"] / 100)


@router.get("/monte-carlo/{ticker}")
async def monte_carlo(
    ticker: str,
    simulations: int = Query(2000, ge=100, le=10000),
    days: int = Query(90, ge=10, le=365),
):
    bars = await get_ohlcv(ticker, "1y", "1d")
    return run_monte_carlo(bars_to_frame(bars), simulations, days)
