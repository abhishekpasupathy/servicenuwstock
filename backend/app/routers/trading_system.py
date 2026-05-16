from fastapi import APIRouter

from app.services.data_fetcher import bars_to_frame, get_ohlcv, get_quote
from app.services.trading_system import run_full_trading_system

router = APIRouter(tags=["trading-system"])


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
    bars = await get_ohlcv(ticker, "2y", "1d")
    quote = await get_quote(ticker)
    df = bars_to_frame(bars)
    return run_full_trading_system(
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
