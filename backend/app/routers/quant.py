from fastapi import APIRouter

from app.services.data_fetcher import bars_to_frame, get_ohlcv, get_quote
from app.services.quant_engine import compute_all_indicators
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
