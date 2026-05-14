from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import find_peaks


def f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        result = float(value)
        return result if np.isfinite(result) else default
    except Exception:
        return default


def _series(value: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(value, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(default)


def _safe_last(value: pd.Series, default: float = 0.0) -> float:
    return f(value.iloc[-1] if len(value) else default, default)


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = line.ewm(span=9, adjust=False).mean()
    return line, signal, line - signal


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _adx(df: pd.DataFrame, length: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    high, low = df["high"], df["low"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=df.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=df.index)
    atr = _true_range(df).ewm(alpha=1 / length, adjust=False).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
    return dx.ewm(alpha=1 / length, adjust=False).mean().fillna(0), plus_di.fillna(0), minus_di.fillna(0)


def detect_cross(a: pd.Series, b: pd.Series, direction: str) -> bool:
    if len(a.dropna()) < 2 or len(b.dropna()) < 2:
        return False
    prev = a.iloc[-2] - b.iloc[-2]
    cur = a.iloc[-1] - b.iloc[-1]
    return bool(prev <= 0 < cur) if direction == "up" else bool(prev >= 0 > cur)


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3
    volume_sum = df["volume"].replace(0, np.nan).cumsum()
    return ((typical * df["volume"]).cumsum() / volume_sum).ffill().fillna(df["close"])


def signal_range(value: float, low: float, high: float) -> str:
    if value < low:
        return "oversold"
    if value > high:
        return "overbought"
    return "neutral"


def classify_regime(adx: pd.Series, ema_50: pd.Series, ema_200: pd.Series, rsi: pd.Series) -> str:
    adx_val = _safe_last(adx)
    up = _safe_last(ema_50) >= _safe_last(ema_200)
    strong = adx_val >= 25
    if up and strong:
        return "STRONG_UPTREND"
    if up:
        return "WEAK_UPTREND"
    if not up and strong:
        return "STRONG_DOWNTREND"
    if _safe_last(rsi, 50) < 45:
        return "WEAK_DOWNTREND"
    return "RANGING"


def compute_all_indicators(df: pd.DataFrame) -> dict[str, Any]:
    df = df.copy().sort_values("date").reset_index(drop=True)
    for name in ["open", "high", "low", "close", "volume"]:
        df[name] = _series(df[name])
    df = df[(df["close"] > 0) & (df["high"] > 0) & (df["low"] > 0)].reset_index(drop=True)
    if len(df) < 60:
        raise ValueError("At least 60 valid bars are required")

    close = df["close"]
    sma_20, sma_50, sma_200 = close.rolling(20, min_periods=1).mean(), close.rolling(50, min_periods=1).mean(), close.rolling(200, min_periods=1).mean()
    ema_12, ema_26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
    ema_50, ema_200 = close.ewm(span=50, adjust=False).mean(), close.ewm(span=200, adjust=False).mean()
    golden_cross = detect_cross(ema_50, ema_200, "up")
    death_cross = detect_cross(ema_50, ema_200, "down")
    vwap = compute_vwap(df)
    rsi = _rsi(close)
    macd_line, macd_signal, macd_hist = _macd(close)

    lowest_low = df["low"].rolling(14, min_periods=1).min()
    highest_high = df["high"].rolling(14, min_periods=1).max()
    range_14 = (highest_high - lowest_low).replace(0, np.nan)
    stoch_k = ((close - lowest_low) / range_14 * 100).fillna(50)
    stoch_d = stoch_k.rolling(3, min_periods=1).mean()
    willr = (((highest_high - close) / range_14) * -100).fillna(-50)
    roc = close.pct_change(10).fillna(0) * 100

    bb_middle = close.rolling(20, min_periods=1).mean()
    bb_std = close.rolling(20, min_periods=2).std().fillna(0)
    bb_upper = bb_middle + 2 * bb_std
    bb_lower = bb_middle - 2 * bb_std
    bb_width = (bb_upper - bb_lower).replace(0, np.nan)
    bb_pct = ((close - bb_lower) / bb_width).clip(0, 1).fillna(0.5)
    bb_bandwidth = (bb_width / bb_middle.replace(0, np.nan) * 100).fillna(0)

    atr = _true_range(df).ewm(alpha=1 / 14, adjust=False).mean().fillna(0)
    log_returns = np.log(close / close.shift(1)).replace([np.inf, -np.inf], np.nan)
    hv_20 = log_returns.rolling(20, min_periods=2).std() * np.sqrt(252) * 100
    obv = (np.sign(close.diff()).fillna(0) * df["volume"]).cumsum()
    money_flow_multiplier = (((close - df["low"]) - (df["high"] - close)) / (df["high"] - df["low"]).replace(0, np.nan)).fillna(0)
    cmf = (money_flow_multiplier * df["volume"]).rolling(20, min_periods=1).sum() / df["volume"].rolling(20, min_periods=1).sum().replace(0, np.nan)
    volume_ratio = df["volume"] / df["volume"].rolling(20, min_periods=1).mean().replace(0, np.nan)
    adx, plus_di, minus_di = _adx(df)
    regime = classify_regime(adx, ema_50, ema_200, rsi)

    prominence = max(float(close.std() or 0) * 0.15, max(float(close.iloc[-1]) * 0.005, 0.5))
    peaks, _ = find_peaks(close.values, distance=10, prominence=prominence)
    troughs, _ = find_peaks(-close.values, distance=10, prominence=prominence)
    last_close = _safe_last(close, 1)
    support = [round(float(x), 2) for x in close.values[troughs[-3:]]] or [round(last_close * 0.94, 2), round(last_close * 0.9, 2)]
    resistance = [round(float(x), 2) for x in close.values[peaks[-3:]]] or [round(last_close * 1.06, 2), round(last_close * 1.1, 2)]
    atr_val = _safe_last(atr)

    return {
        "sma": {"20": _safe_last(sma_20), "50": _safe_last(sma_50), "200": _safe_last(sma_200)},
        "ema": {"12": _safe_last(ema_12), "26": _safe_last(ema_26), "50": _safe_last(ema_50), "200": _safe_last(ema_200)},
        "golden_cross": golden_cross,
        "death_cross": death_cross,
        "vwap": _safe_last(vwap),
        "rsi": {"value": _safe_last(rsi, 50), "signal": signal_range(_safe_last(rsi, 50), 30, 70)},
        "macd": {
            "macd": _safe_last(macd_line),
            "line": _safe_last(macd_line),
            "signal_line": _safe_last(macd_signal),
            "histogram": _safe_last(macd_hist),
            "signal": "bullish" if _safe_last(macd_hist) > 0 else "bearish",
        },
        "stoch": {"k": _safe_last(stoch_k, 50), "d": _safe_last(stoch_d, 50), "signal": signal_range(_safe_last(stoch_k, 50), 20, 80)},
        "willr": {"value": _safe_last(willr, -50), "signal": "oversold" if _safe_last(willr, -50) < -80 else "overbought" if _safe_last(willr, -50) > -20 else "neutral"},
        "roc": {"value": _safe_last(roc), "signal": "bullish" if _safe_last(roc) > 0 else "bearish"},
        "bbands": {
            "upper": _safe_last(bb_upper),
            "middle": _safe_last(bb_middle),
            "lower": _safe_last(bb_lower),
            "pct_b": _safe_last(bb_pct, 0.5),
            "bandwidth": _safe_last(bb_bandwidth),
        },
        "atr": {"value": atr_val, "atr_pct": atr_val / max(last_close, 0.01) * 100},
        "hv_20": _safe_last(hv_20),
        "keltner": {"available": True},
        "obv": {"value": _safe_last(obv), "trend": "rising" if _safe_last(obv) > f(obv.iloc[-10] if len(obv) >= 10 else obv.iloc[0]) else "falling"},
        "cmf": {"value": _safe_last(cmf), "signal": "bullish" if _safe_last(cmf) > 0 else "bearish"},
        "volume_ratio": _safe_last(volume_ratio, 1),
        "adx": {"value": _safe_last(adx), "plus_di": _safe_last(plus_di), "minus_di": _safe_last(minus_di)},
        "regime": regime,
        "support": support,
        "resistance": resistance,
    }
