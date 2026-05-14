from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

try:
    import pandas_ta as ta  # noqa: F401
except Exception:  # pragma: no cover
    ta = None


def f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def col(row: Any, prefix: str, default: float = 0.0) -> float:
    if not hasattr(row, "items"):
        return default
    for key, value in row.items():
        if str(key).startswith(prefix):
            return f(value, default)
    return default


def detect_cross(a: pd.Series, b: pd.Series, direction: str) -> bool:
    if len(a.dropna()) < 2 or len(b.dropna()) < 2:
        return False
    prev = a.iloc[-2] - b.iloc[-2]
    cur = a.iloc[-1] - b.iloc[-1]
    return bool(prev <= 0 < cur) if direction == "up" else bool(prev >= 0 > cur)


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3
    return (typical * df["volume"]).cumsum() / df["volume"].replace(0, np.nan).cumsum()


def signal_range(value: float, low: float, high: float) -> str:
    if value < low:
        return "oversold"
    if value > high:
        return "overbought"
    return "neutral"


def classify_regime(adx: pd.DataFrame, ema_50: pd.Series, ema_200: pd.Series, rsi: pd.Series) -> str:
    adx_val = f(adx.iloc[-1].get("ADX_14") if isinstance(adx, pd.DataFrame) else np.nan)
    up = f(ema_50.iloc[-1]) >= f(ema_200.iloc[-1])
    strong = adx_val >= 25
    if up and strong:
        return "STRONG_UPTREND"
    if up:
        return "WEAK_UPTREND"
    if not up and strong:
        return "STRONG_DOWNTREND"
    if f(rsi.iloc[-1], 50) < 45:
        return "WEAK_DOWNTREND"
    return "RANGING"


def compute_all_indicators(df: pd.DataFrame) -> dict[str, Any]:
    df = df.copy().sort_values("date").reset_index(drop=True)
    if len(df) < 60:
        raise ValueError("At least 60 bars are required")

    # SMA 20, 50, 200: simple averages; price above SMA200 implies long-term uptrend.
    sma_20, sma_50, sma_200 = df.ta.sma(20), df.ta.sma(50), df.ta.sma(200)
    # EMA 12, 26, 50, 200: exponential averages react faster to fresh price action.
    ema_12, ema_26, ema_50, ema_200 = df.ta.ema(12), df.ta.ema(26), df.ta.ema(50), df.ta.ema(200)
    # Golden/death crosses identify medium-term regime shifts against long-term trend.
    golden_cross = detect_cross(ema_50, ema_200, "up")
    death_cross = detect_cross(ema_50, ema_200, "down")
    # VWAP: volume-weighted average price, often used as an institutional anchor.
    vwap = compute_vwap(df)
    # RSI(14): momentum oscillator; below 30 oversold, above 70 overbought.
    rsi = df.ta.rsi(14)
    # MACD(12,26,9): trend-following momentum; positive histogram shows building upside momentum.
    macd = df.ta.macd(12, 26, 9)
    # Stochastic(14,3,3): close position inside recent range; extreme readings flag stretched moves.
    stoch = df.ta.stoch(14, 3, 3)
    # Williams %R(14): inverted momentum range oscillator; below -80 is oversold.
    willr = df.ta.willr(14)
    # ROC(10): ten-day rate of change; positive means recent acceleration upward.
    roc = df.ta.roc(10)
    # Bollinger Bands(20,2): volatility envelope; %B locates price within the band.
    bbands = df.ta.bbands(20, 2)
    # ATR(14): average true range; high ATR means stops need more room.
    atr = df.ta.atr(14)
    # Historical Volatility: annualized 20-day log-return volatility.
    log_returns = np.log(df["close"] / df["close"].shift(1))
    hv_20 = log_returns.rolling(20).std() * np.sqrt(252) * 100
    # Keltner Channels: ATR-based bands that respond differently than standard-deviation bands.
    kc = df.ta.kc(20, 2)
    # OBV: on-balance volume; rising OBV confirms accumulation.
    obv = df.ta.obv()
    # CMF: Chaikin Money Flow; positive values imply buying pressure.
    cmf = df.ta.cmf(20)
    # Volume ratio compares current volume to 20-day average; >1.5x is unusual activity.
    vol_ratio = df["volume"] / df["volume"].rolling(20).mean()
    # ADX(14): trend strength; use +DI and -DI for direction.
    adx = df.ta.adx(14)
    regime = classify_regime(adx, ema_50, ema_200, rsi)

    peaks, _ = find_peaks(df["close"].values, distance=10, prominence=max(df["close"].std() * 0.15, 1))
    troughs, _ = find_peaks(-df["close"].values, distance=10, prominence=max(df["close"].std() * 0.15, 1))
    support = [round(float(x), 2) for x in df["close"].values[troughs[-3:]]] or [80.0, 85.0]
    resistance = [round(float(x), 2) for x in df["close"].values[peaks[-3:]]] or [90.0, 95.0]

    macd_row = macd.iloc[-1] if isinstance(macd, pd.DataFrame) else {}
    stoch_row = stoch.iloc[-1] if isinstance(stoch, pd.DataFrame) else {}
    bb_row = bbands.iloc[-1] if isinstance(bbands, pd.DataFrame) else {}
    adx_row = adx.iloc[-1] if isinstance(adx, pd.DataFrame) else {}
    last_close = f(df["close"].iloc[-1], 85)
    atr_val = f(atr.iloc[-1])

    return {
        "sma": {"20": f(sma_20.iloc[-1]), "50": f(sma_50.iloc[-1]), "200": f(sma_200.iloc[-1])},
        "ema": {"12": f(ema_12.iloc[-1]), "26": f(ema_26.iloc[-1]), "50": f(ema_50.iloc[-1]), "200": f(ema_200.iloc[-1])},
        "golden_cross": golden_cross,
        "death_cross": death_cross,
        "vwap": f(vwap.iloc[-1]),
        "rsi": {"value": f(rsi.iloc[-1], 50), "signal": signal_range(f(rsi.iloc[-1], 50), 30, 70)},
        "macd": {
            "macd": f(macd_row.get("MACD_12_26_9")),
            "line": f(macd_row.get("MACD_12_26_9")),
            "signal_line": f(macd_row.get("MACDs_12_26_9")),
            "histogram": f(macd_row.get("MACDh_12_26_9")),
            "signal": "bullish" if f(macd_row.get("MACDh_12_26_9")) > 0 else "bearish",
        },
        "stoch": {"k": f(stoch_row.get("STOCHk_14_3_3")), "d": f(stoch_row.get("STOCHd_14_3_3")), "signal": signal_range(f(stoch_row.get("STOCHk_14_3_3"), 50), 20, 80)},
        "willr": {"value": f(willr.iloc[-1], -50), "signal": "oversold" if f(willr.iloc[-1], -50) < -80 else "overbought" if f(willr.iloc[-1], -50) > -20 else "neutral"},
        "roc": {"value": f(roc.iloc[-1]), "signal": "bullish" if f(roc.iloc[-1]) > 0 else "bearish"},
        "bbands": {
            "upper": col(bb_row, "BBU_20"),
            "middle": col(bb_row, "BBM_20"),
            "lower": col(bb_row, "BBL_20"),
            "pct_b": col(bb_row, "BBP_20", 0.5),
            "bandwidth": col(bb_row, "BBB_20"),
        },
        "atr": {"value": atr_val, "atr_pct": atr_val / last_close * 100},
        "hv_20": f(hv_20.iloc[-1]),
        "keltner": {"available": kc is not None},
        "obv": {"value": f(obv.iloc[-1]), "trend": "rising" if f(obv.iloc[-1]) > f(obv.iloc[-10]) else "falling"},
        "cmf": {"value": f(cmf.iloc[-1]), "signal": "bullish" if f(cmf.iloc[-1]) > 0 else "bearish"},
        "volume_ratio": f(vol_ratio.iloc[-1], 1),
        "adx": {"value": f(adx_row.get("ADX_14")), "plus_di": f(adx_row.get("DMP_14")), "minus_di": f(adx_row.get("DMN_14"))},
        "regime": regime,
        "support": support,
        "resistance": resistance,
    }
