from fastapi import APIRouter

from app.services.data_fetcher import bars_to_frame, get_ohlcv, get_quote
from app.services.monte_carlo import run_monte_carlo
from app.services.quant_engine import compute_all_indicators
from app.services.risk_engine import compute_risk_metrics
from app.services.signal_engine import generate_signals

router = APIRouter(tags=["quant"])


@router.get("/quant/indicators/{ticker}")
async def indicators(ticker: str):
    bars = await get_ohlcv(ticker, "1y", "1d")
    return compute_all_indicators(bars_to_frame(bars))


@router.get("/signals/{ticker}")
async def signals(ticker: str):
    bars = await get_ohlcv(ticker, "1y", "1d")
    quote = await get_quote(ticker)
    return generate_signals(compute_all_indicators(bars_to_frame(bars)), quote["price"])


@router.get("/analytics/{ticker}")
async def analytics(ticker: str):
    bars = await get_ohlcv(ticker, "2y", "1d")
    df = bars_to_frame(bars)
    quote = await get_quote(ticker)
    quant = compute_all_indicators(df)
    signals_payload = generate_signals(quant, quote["price"])
    risk = compute_risk_metrics(df, None, signals_payload["buy_prob"] / 100)
    monte = run_monte_carlo(df, 1000, 90)
    return {
        "ticker": quote["ticker"],
        "quote": quote,
        "indicators": quant,
        "signals": signals_payload,
        "risk": risk,
        "monte_carlo": monte,
        "source": quote.get("source", "unknown"),
        "stale": bool(quote.get("stale")),
    }
