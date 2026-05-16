import asyncio
import math
from typing import Any

from fastapi import APIRouter

from app.cache import cache_set
from app.services.data_fetcher import _fast_get, _fast_set, bars_to_frame, get_ohlcv, get_quote
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
    bars, quote = await asyncio.gather(
        get_ohlcv(ticker, "1y", "1d"),
        get_quote(ticker),
    )
    payload = generate_signals(compute_all_indicators(bars_to_frame(bars)), quote["price"])
    await cache_set(f"signals:{ticker.upper()}", payload, 300)
    return payload


@router.get("/analytics/{ticker}")
async def analytics(ticker: str):
    bars, quote = await asyncio.gather(
        get_ohlcv(ticker, "2y", "1d"),
        get_quote(ticker),
    )
    df = bars_to_frame(bars)
    quant = compute_all_indicators(df)
    signals_payload = generate_signals(quant, quote["price"])
    risk = compute_risk_metrics(df, None, signals_payload["buy_prob"] / 100)
    monte = run_monte_carlo(df, 500, 90)  # Reduced from 1000 to 500
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


@router.get("/prediction/{ticker}")
async def prediction(ticker: str):
    ticker = ticker.strip().upper()
    cache_key = f"prediction:{ticker}"
    cached = _fast_get(cache_key, 120)
    if cached:
        return cached

    bars, quote = await asyncio.gather(
        get_ohlcv(ticker, "2y", "1d"),
        get_quote(ticker),
    )
    df = bars_to_frame(bars)
    price = float(quote["price"])
    quant = compute_all_indicators(df)
    signals_payload = generate_signals(quant, price)
    monte_year = run_monte_carlo(df, 500, 252)  # Reduced from 2000 to 500

    # Day range prediction using ATR + Bollinger Bands
    atr_val = float(quant["atr"]["value"])
    atr_pct = float(quant["atr"]["atr_pct"])
    bb = quant["bbands"]
    bb_width = float(bb["upper"]) - float(bb["lower"])
    bb_mid = float(bb["middle"])

    # Blend ATR and Bollinger width for intraday range
    day_range_half = (atr_val * 0.6 + bb_width * 0.4) / 2
    day_high_pred = round(price + day_range_half, 2)
    day_low_pred = round(price - day_range_half, 2)

    # Regime-adjusted bias
    regime = quant["regime"]
    bias_map = {
        "STRONG_UPTREND": 0.7,
        "WEAK_UPTREND": 0.3,
        "RANGING": 0.0,
        "WEAK_DOWNTREND": -0.3,
        "STRONG_DOWNTREND": -0.7,
    }
    regime_bias = bias_map.get(regime, 0.0)

    # Composite signal direction
    composite = float(signals_payload["composite_score"])
    signal_bias = max(-1.0, min(1.0, composite / 100))

    # Combined directional bias (-1 to +1)
    direction_bias = round(regime_bias * 0.4 + signal_bias * 0.6, 3)

    # Year range from Monte Carlo
    mc_ci_95 = monte_year["confidence_interval_95"]
    mc_ci_68 = [
        round(float(math.exp(math.log(price) + 0.5 * (math.log(mc_ci_95[1]) - math.log(mc_ci_95[0])) / 1.96)), 2),
        round(float(math.exp(math.log(price) - 0.5 * (math.log(mc_ci_95[1]) - math.log(mc_ci_95[0])) / 1.96)), 2),
    ]
    # Use actual percentile data for 68% CI
    final_paths = monte_year.get("percentiles", {})
    p50 = final_paths.get("50", [price])
    year_median = round(p50[-1], 2) if isinstance(p50, list) and p50 else price

    # Year targets using Bollinger + trend extrapolation
    ema_50 = float(quant["ema"]["50"])
    ema_200 = float(quant["ema"]["200"])
    trend_slope = (ema_50 - ema_200) / max(ema_200, 1)
    year_base_target = round(price * (1 + trend_slope * 2 + direction_bias * 0.15), 2)

    # Support and resistance as additional context
    support_levels = quant["support"]
    resistance_levels = quant["resistance"]

    # Algorithm weights for transparency
    algorithms = {
        "atr_true_range": {"weight": 0.35, "value": round(atr_val, 2), "description": "Average True Range for intraday volatility"},
        "bollinger_width": {"weight": 0.25, "value": round(bb_width, 2), "description": "Bollinger Band width for expected range"},
        "regime_detection": {"weight": 0.15, "value": regime, "description": "ADX + EMA trend regime classification"},
        "rsi_momentum": {"weight": 0.10, "value": round(float(quant["rsi"]["value"]), 2), "description": "RSI momentum indicator"},
        "macd_signal": {"weight": 0.10, "value": round(float(quant["macd"]["histogram"]), 4), "description": "MACD histogram for trend direction"},
        "monte_carlo": {"weight": 0.05, "value": f"{monte_year['prob_above_current']}% above current", "description": "Monte Carlo simulation (500 paths, 252 days)"},
    }

    # Direction label
    if direction_bias >= 0.5:
        direction_label = "STRONG BULLISH"
    elif direction_bias >= 0.2:
        direction_label = "BULLISH"
    elif direction_bias >= -0.2:
        direction_label = "NEUTRAL"
    elif direction_bias >= -0.5:
        direction_label = "BEARISH"
    else:
        direction_label = "STRONG BEARISH"

    result = {
        "ticker": ticker,
        "current_price": price,
        "day_prediction": {
            "predicted_high": day_high_pred,
            "predicted_low": day_low_pred,
            "predicted_mid": round((day_high_pred + day_low_pred) / 2, 2),
            "atr_value": round(atr_val, 2),
            "atr_pct": round(atr_pct, 2),
        },
        "year_prediction": {
            "median_target": year_median,
            "base_target": year_base_target,
            "ci_95_low": mc_ci_95[0],
            "ci_95_high": mc_ci_95[1],
            "prob_above_current": monte_year["prob_above_current"],
            "prob_10pct_gain": monte_year["prob_10pct_gain"],
            "prob_20pct_gain": monte_year["prob_20pct_gain"],
            "prob_10pct_loss": monte_year["prob_10pct_loss"],
            "expected_return_pct": monte_year["expected_return_pct"],
        },
        "direction_bias": direction_bias,
        "direction_label": direction_label,
        "regime": regime,
        "composite_score": round(composite, 2),
        "action": signals_payload["action"],
        "confidence": signals_payload["confidence"],
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
        "algorithms": algorithms,
        "source": quote.get("source", "unknown"),
        "stale": bool(quote.get("stale")),
    }
    _fast_set(cache_key, result, 120)
    return result
