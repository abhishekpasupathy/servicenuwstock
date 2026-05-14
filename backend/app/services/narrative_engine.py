from datetime import UTC, datetime
from typing import Any


def _money(v: float | int | None) -> str:
    return f"${float(v or 0):,.2f}"


def generate_insight(quant: dict[str, Any], signals: dict[str, Any], risk: dict[str, Any], monte: dict[str, Any], quote: dict[str, Any] | None = None) -> dict[str, Any]:
    quote = quote or {}
    price = quote.get("price") or monte.get("current_price") or 85
    action = signals["action"]
    verdicts = {
        "STRONG BUY": "Strong Buy - High conviction entry point",
        "ACCUMULATE": "Accumulate - Add to position on dips",
        "HOLD": "Hold - Maintain current position",
        "REDUCE": "Reduce - Trim position, raise cash",
        "SELL": "Sell - Exit or significantly reduce exposure",
    }
    bullish: list[str] = []
    bearish: list[str] = []
    if quant["rsi"]["value"] < 65:
        bullish.append(f"RSI at {quant['rsi']['value']:.1f} is not overheated, leaving room for upside.")
    if quant["macd"]["histogram"] > 0:
        bullish.append(f"MACD histogram is positive at {quant['macd']['histogram']:.2f}, showing improving momentum.")
    if quant["obv"]["trend"] == "rising":
        bullish.append("On-balance volume is rising, which supports accumulation.")
    if quant["ema"]["50"] > quant["ema"]["200"]:
        bullish.append("EMA50 is above EMA200, keeping the medium-term trend constructive.")
    if price < quant["sma"]["200"]:
        bearish.append(f"NOW trades below the 200-day moving average at {_money(quant['sma']['200'])}, so the long-term trend still needs repair.")
    if quant["atr"]["atr_pct"] > 3:
        bearish.append(f"ATR is {quant['atr']['atr_pct']:.1f}% of price, which means daily swings can be meaningful.")
    if risk["max_drawdown_252"] < -20:
        bearish.append(f"The past-year max drawdown was {risk['max_drawdown_252']:.1f}%, so position size matters.")
    if quant["rsi"]["value"] > 70:
        bearish.append(f"RSI at {quant['rsi']['value']:.1f} is overbought.")
    support = max([x for x in quant["support"] if x <= price], default=min(quant["support"], default=price * 0.94))
    resistance = min([x for x in quant["resistance"] if x >= price], default=max(quant["resistance"], default=price * 1.08))
    stop = price - 1.5 * quant["atr"]["value"]
    summary = (
        f"ServiceNow (NOW) is trading at {_money(price)}, {quote.get('change_pct', 0):+.1f}% today. "
        f"The stock is in a {quant['regime'].lower().replace('_', ' ')} with a composite score of {signals['composite_score']:+.0f}/100. "
        f"RSI at {quant['rsi']['value']:.1f} is {quant['rsi']['signal']}, while MACD is {quant['macd']['signal']}. "
        f"The model assigns {signals['buy_prob']:.0f}% buy, {signals['hold_prob']:.0f}% hold, and {signals['sell_prob']:.0f}% sell probability. "
        f"Suggested action: {action}. Watch support near {_money(support)} and resistance near {_money(resistance)}."
    )
    mc = (
        f"Over the next 90 trading days, 2,000 simulated paths show a base case near {_money(monte['percentiles']['50'][-1])}, "
        f"a bull case near {_money(monte['percentiles']['75'][-1])}, and a bear case near {_money(monte['percentiles']['25'][-1])}. "
        f"The probability of finishing above the current price is {monte['prob_above_current']:.1f}%."
    )
    return {
        "verdict": verdicts[action],
        "confidence": signals["confidence"],
        "plain_english_summary": summary,
        "bullish_reasons": bullish or ["No major bullish signal is dominant right now."],
        "bearish_risks": bearish or ["No major technical risk is dominant right now."],
        "key_levels": {"support": round(support, 2), "resistance": round(resistance, 2), "stop_loss": round(stop, 2), "target": round(resistance, 2)},
        "monte_carlo_narrative": mc,
        "suggested_action": action,
        "technical_summary": f"Regime={quant['regime']}; ADX={quant['adx']['value']:.1f}; HV20={quant['hv_20']:.1f}%; beta={risk['beta_252']:.2f}; Sharpe={risk['sharpe_ratio']:.2f}.",
        "generated_at": datetime.now(UTC).isoformat(),
    }
