import math
from typing import Any


WEIGHTS = {
    "regime": 20,
    "macd": 15,
    "rsi": 12,
    "ema_cross": 12,
    "bollinger": 8,
    "volume": 8,
    "atr_risk": 8,
    "obv": 7,
    "roc": 5,
    "support_res": 5,
}


def _clamp(v: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _score(name: str, q: dict[str, Any], price: float) -> float:
    if name == "regime":
        return {"STRONG_UPTREND": 85, "WEAK_UPTREND": 35, "RANGING": 0, "WEAK_DOWNTREND": -35, "STRONG_DOWNTREND": -85}.get(q["regime"], 0)
    if name == "macd":
        return _clamp(q["macd"]["histogram"] * 35)
    if name == "rsi":
        rsi = q["rsi"]["value"]
        return 65 if rsi < 30 else -65 if rsi > 70 else _clamp((55 - abs(rsi - 50)) * 1.5)
    if name == "ema_cross":
        if q["golden_cross"]:
            return 100
        if q["death_cross"]:
            return -100
        return 45 if q["ema"]["50"] > q["ema"]["200"] else -45
    if name == "bollinger":
        pct = q["bbands"]["pct_b"]
        return 55 if pct < 0.15 else -55 if pct > 0.9 else _clamp((0.55 - pct) * -80)
    if name == "volume":
        return 35 if q["volume_ratio"] > 1.2 and q["roc"]["value"] > 0 else -25 if q["volume_ratio"] > 1.2 else 0
    if name == "atr_risk":
        return -70 if q["atr"]["atr_pct"] > 5 else -25 if q["atr"]["atr_pct"] > 3 else 20
    if name == "obv":
        return 45 if q["obv"]["trend"] == "rising" else -45
    if name == "roc":
        return _clamp(q["roc"]["value"] * 8)
    if name == "support_res":
        support = max([x for x in q["support"] if x <= price], default=min(q["support"], default=price))
        resistance = min([x for x in q["resistance"] if x >= price], default=max(q["resistance"], default=price))
        if abs(price - support) / price < 0.03:
            return 40
        if abs(resistance - price) / price < 0.03:
            return -35
    return 0


def generate_signals(quant: dict[str, Any], price: float) -> dict[str, Any]:
    breakdown = {}
    total = 0.0
    votes: list[int] = []
    for name, weight in WEIGHTS.items():
        raw = _score(name, quant, price)
        contribution = raw * weight / 100
        total += contribution
        votes.append(1 if raw > 10 else -1 if raw < -10 else 0)
        breakdown[name] = {"score": round(raw, 2), "weight": weight, "contribution": round(contribution, 2), "signal": "bullish" if raw > 10 else "bearish" if raw < -10 else "neutral"}
    composite = _clamp(total)
    buy_raw = 1 / (1 + math.exp(-(composite - 8) / 22))
    sell_raw = 1 / (1 + math.exp(-(-composite - 8) / 22))
    hold_raw = max(0.25, 1 - abs(composite) / 100)
    denom = buy_raw + sell_raw + hold_raw
    buy, sell, hold = buy_raw / denom * 100, sell_raw / denom * 100, hold_raw / denom * 100
    action = "STRONG BUY" if composite >= 65 else "ACCUMULATE" if composite >= 25 else "SELL" if composite <= -65 else "REDUCE" if composite <= -25 else "HOLD"
    dominant = 1 if action in ("STRONG BUY", "ACCUMULATE") else -1 if action in ("REDUCE", "SELL") else 0
    agree = sum(1 for v in votes if v == dominant or (dominant == 0 and v == 0))
    confidence = agree / len(votes) * 100
    strength = max(1, min(5, round((confidence / 25 + abs(composite) / 35) / 2)))
    return {
        "composite_score": round(composite, 2),
        "buy_prob": round(buy, 1),
        "hold_prob": round(hold, 1),
        "sell_prob": round(sell, 1),
        "action": action,
        "confidence": round(confidence, 1),
        "agreement": f"{agree}/{len(votes)}",
        "signal_strength": strength,
        "indicator_breakdown": breakdown,
    }
