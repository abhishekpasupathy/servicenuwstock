"""
Institutional-Grade Algorithmic Trading System for ServiceNow (NOW)
===================================================================
A $50B multi-strategy hedge fund long/short equity playbook.
Every rule is executable by algorithm — no human interpretation required.
"""

import math
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from app.services.quant_engine import compute_all_indicators
from app.services.signal_engine import generate_signals, WEIGHTS


# ─── MODULE 1: SIGNAL STACK ───────────────────────────────────────────────────

SIGNAL_WEIGHTS = {
    "momentum_zscore": 0.30,       # Price momentum z-score (20/50/200d)
    "rsi_reversion": 0.20,         # RSI mean-reversion trigger
    "macd_slope": 0.20,            # MACD histogram slope change
    "put_call_skew": 0.15,         # Options put/call OI skew
    "dark_pool_volume": 0.15,      # Dark pool print vs 30d avg
}

COMPOSITE_THRESHOLDS = {
    "strong_accumulate": 75,       # Score >= 75: deploy full tranche sizing
    "accumulate": 50,              # Score >= 50: standard DCA accumulation
    "hold": 25,                    # Score >= 25: hold existing, no new adds
    "reduce": -25,                 # Score <= -25: begin position reduction
    "strong_reduce": -50,          # Score <= -50: aggressive reduction
    "exit": -75,                   # Score <= -75: full exit
}


def _zscore(series: pd.Series, window: int) -> float:
    """Rolling z-score of latest value vs window."""
    if len(series) < window:
        return 0.0
    tail = series.tail(window)
    mean = tail.mean()
    std = tail.std()
    if std == 0 or not np.isfinite(std):
        return 0.0
    return float((series.iloc[-1] - mean) / std)


def compute_signal_stack(df: pd.DataFrame, quote_price: float, quant: dict[str, Any]) -> dict[str, Any]:
    """MODULE 1: Weighted multi-factor signal stack."""
    close = pd.to_numeric(df["close"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()

    # (a) Price momentum z-score on 20/50/200 day windows
    z20 = _zscore(close, 20)
    z50 = _zscore(close, 50)
    z200 = _zscore(close, 200)
    momentum_zscore = (z20 * 0.5 + z50 * 0.3 + z200 * 0.2)
    momentum_signal = max(-100, min(100, momentum_zscore * 25))

    # (b) RSI mean-reversion trigger
    rsi_val = float(quant["rsi"]["value"])
    if rsi_val <= 25:
        rsi_signal = 90            # Extreme oversold: strong buy
    elif rsi_val <= 30:
        rsi_signal = 70            # Oversold: buy
    elif rsi_val <= 40:
        rsi_signal = 30            # Below mid: mild buy
    elif rsi_val <= 60:
        rsi_signal = 0             # Neutral
    elif rsi_val <= 70:
        rsi_signal = -30           # Above mid: mild sell
    elif rsi_val <= 75:
        rsi_signal = -70           # Overbought: sell
    else:
        rsi_signal = -90           # Extreme overbought: strong sell

    # (c) MACD histogram slope change detection
    macd_hist = float(quant["macd"]["histogram"])
    macd_prev = float(quant["macd"].get("prev_histogram", macd_hist))
    macd_slope = macd_hist - macd_prev
    if macd_hist > 0 and macd_slope > 0:
        macd_signal = 80           # Positive and accelerating
    elif macd_hist > 0 and macd_slope <= 0:
        macd_signal = 30           # Positive but decelerating
    elif macd_hist < 0 and macd_slope < 0:
        macd_signal = -80          # Negative and accelerating down
    elif macd_hist < 0 and macd_slope >= 0:
        macd_signal = 50           # Negative but reversing (early positive divergence)
    else:
        macd_signal = 0

    # (d) Options put/call OI skew (simulated from RSI + regime)
    regime = quant["regime"]
    regime_skew = {"STRONG_UPTREND": -20, "WEAK_UPTREND": -10, "RANGING": 0, "WEAK_DOWNTREND": 15, "STRONG_DOWNTREND": 30}
    pcr_signal = regime_skew.get(regime, 0) + (40 - rsi_val) * 0.5
    pcr_signal = max(-100, min(100, pcr_signal))

    # (e) Dark pool print volume vs 30-day average (volume ratio proxy)
    vol_ratio = float(quant.get("volume_ratio", 1.0))
    if vol_ratio >= 2.0:
        dark_pool_signal = 60      # Heavy institutional accumulation
    elif vol_ratio >= 1.5:
        dark_pool_signal = 40
    elif vol_ratio >= 1.2:
        dark_pool_signal = 20
    elif vol_ratio >= 0.8:
        dark_pool_signal = 0       # Normal
    elif vol_ratio >= 0.5:
        dark_pool_signal = -30     # Below average: distribution
    else:
        dark_pool_signal = -60     # Very low: no interest

    # Composite
    raw_signals = {
        "momentum_zscore": momentum_signal,
        "rsi_reversion": rsi_signal,
        "macd_slope": macd_signal,
        "put_call_skew": pcr_signal,
        "dark_pool_volume": dark_pool_signal,
    }
    composite = sum(raw_signals[k] * SIGNAL_WEIGHTS[k] for k in SIGNAL_WEIGHTS)
    composite = max(-100, min(100, composite))

    # Action determination
    if composite >= COMPOSITE_THRESHOLDS["strong_accumulate"]:
        action = "STRONG_ACCUMULATE"
    elif composite >= COMPOSITE_THRESHOLDS["accumulate"]:
        action = "ACCUMULATE"
    elif composite >= COMPOSITE_THRESHOLDS["hold"]:
        action = "HOLD"
    elif composite >= COMPOSITE_THRESHOLDS["reduce"]:
        action = "REDUCE"
    elif composite >= COMPOSITE_THRESHOLDS["strong_reduce"]:
        action = "STRONG_REDUCE"
    else:
        action = "EXIT"

    return {
        "signals": {k: {"value": round(v, 2), "weight": SIGNAL_WEIGHTS[k], "contribution": round(v * SIGNAL_WEIGHTS[k], 2)} for k, v in raw_signals.items()},
        "composite_score": round(composite, 2),
        "action": action,
        "thresholds": COMPOSITE_THRESHOLDS,
        "raw_momentum": {"z20": round(z20, 3), "z50": round(z50, 3), "z200": round(z200, 3)},
    }


# ─── MODULE 2: ENTRY ENGINE ──────────────────────────────────────────────────

TRANCHES = [
    {"level": 1, "price": 95.0, "multiplier": 1.0, "label": "Base entry"},
    {"level": 2, "price": 85.0, "multiplier": 1.5, "label": "10.5% below — scale up"},
    {"level": 3, "price": 75.0, "multiplier": 2.0, "label": "21% below — deep value"},
    {"level": 4, "price": 65.0, "multiplier": 3.0, "label": "31.5% below — maximum conviction"},
]

DRY_POWDER_PCT = 0.40  # 40% stays undeployed until trend confirms
TIME_SPACING_DAYS = 14  # Minimum 14 calendar days between tranches


def compute_entry_engine(
    current_price: float,
    signal_score: float,
    total_capital: float,
    deployed_capital: float,
    trend_confirmed: bool,
    days_since_last_entry: int,
    last_entry_price: float,
) -> dict[str, Any]:
    """MODULE 2: Tranche-based DCA entry engine."""
    deployable = total_capital * (1 - DRY_POWDER_PCT) if not trend_confirmed else total_capital
    remaining = deployable - deployed_capital

    # Z-score deviation sizing
    deviation_pct = (95.0 - current_price) / 95.0  # vs reference price $95
    z_multiplier = 1.0 + max(0, deviation_pct * 3)  # 3x leverage per 100% drop

    # Determine which tranche we're in
    active_tranche = None
    for t in reversed(TRANCHES):
        if current_price <= t["price"]:
            active_tranche = t
            break
    if active_tranche is None:
        active_tranche = {"level": 0, "price": current_price, "multiplier": 0.5, "label": "Above all tranche levels"}

    # Size calculation
    base_tranche_size = deployable / len(TRANCHES)
    adjusted_size = base_tranche_size * active_tranche["multiplier"] * min(z_multiplier, 3.0)

    # Can we deploy?
    can_deploy = (
        remaining > 0
        and days_since_last_entry >= TIME_SPACING_DAYS
        and signal_score >= COMPOSITE_THRESHOLDS["accumulate"]
        and adjusted_size <= remaining
    )

    # Dry powder status
    dry_powder = total_capital - deployable
    if trend_confirmed:
        dry_powder = 0
        deployable = total_capital

    return {
        "total_capital": round(total_capital, 2),
        "deployable_capital": round(deployable, 2),
        "deployed_capital": round(deployed_capital, 2),
        "remaining_capital": round(remaining, 2),
        "dry_powder_reserve": round(dry_powder, 2),
        "dry_powder_pct": round(DRY_POWDER_PCT * 100 if not trend_confirmed else 0, 1),
        "active_tranche": active_tranche,
        "next_tranche_price": next((t["price"] for t in TRANCHES if t["price"] < current_price), None),
        "tranche_schedule": TRANCHES,
        "z_multiplier": round(z_multiplier, 2),
        "adjusted_tranche_size": round(adjusted_size, 2),
        "can_deploy": can_deploy,
        "days_until_next_entry": max(0, TIME_SPACING_DAYS - days_since_last_entry),
        "signal_score": round(signal_score, 2),
        "signal_threshold": COMPOSITE_THRESHOLDS["accumulate"],
        "rules": {
            "R1": f"IF signal_score >= {COMPOSITE_THRESHOLDS['accumulate']} AND days_since_last >= {TIME_SPACING_DAYS} THEN deploy tranche",
            "R2": f"IF price drops to next tranche level THEN size = base × multiplier × z_multiplier",
            "R3": f"IF trend NOT confirmed THEN hold {DRY_POWDER_PCT*100:.0f}% as dry powder reserve",
            "R4": "IF z_multiplier > 3.0 THEN cap at 3.0 (no unlimited averaging down)",
        },
    }


# ─── MODULE 3: TREND CONFIRMATION CHECKLIST ──────────────────────────────────

def compute_trend_confirmation(df: pd.DataFrame, quant: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    """MODULE 3: Binary trend confirmation checklist."""
    close = pd.to_numeric(df["close"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    ema_50 = float(quant["ema"]["50"])
    ema_200 = float(quant["ema"]["200"])
    price = float(close.iloc[-1])

    # 50MA direction (slope over 10 days)
    if len(close) >= 60:
        ma50_series = close.rolling(50).mean().dropna()
        ma50_slope = float(ma50_series.iloc[-1] - ma50_series.iloc[-10])
    else:
        ma50_slope = 0.0

    # Volume on up days vs down days (20-day)
    returns = close.pct_change().dropna().tail(20)
    up_days = returns[returns > 0]
    down_days = returns[returns < 0]
    # Use volume from df if available
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce").tail(20)
        up_vol = vol[returns > 0].sum() if len(up_days) > 0 else 0
        down_vol = vol[returns < 0].sum() if len(down_days) > 0 else 1
        vol_ratio = float(up_vol / max(down_vol, 1))
    else:
        vol_ratio = 1.0

    # Weekly MACD crossover (approximate from daily)
    macd_line = float(quant["macd"]["macd"])
    macd_signal = float(quant["macd"]["signal"])
    weekly_macd_bullish = macd_line > macd_signal

    # Institutional flow (volume ratio proxy)
    volume_ratio = float(quant.get("volume_ratio", 1.0))

    checklist = {
        "C1_price_above_200ma": {
            "condition": "Price > 200-day EMA",
            "actual": round(price, 2),
            "threshold": round(ema_200, 2),
            "passed": price > ema_200,
        },
        "C2_50ma_rising": {
            "condition": "50-day EMA slope > 0 (rising over 10 days)",
            "actual": round(ma50_slope, 4),
            "threshold": 0,
            "passed": ma50_slope > 0,
        },
        "C3_50ma_above_200ma": {
            "condition": "50-day EMA > 200-day EMA (golden cross)",
            "actual": round(ema_50, 2),
            "threshold": round(ema_200, 2),
            "passed": ema_50 > ema_200,
        },
        "C4_up_volume_dominance": {
            "condition": "Volume on up days / Volume on down days > 1.2 (20-day)",
            "actual": round(vol_ratio, 2),
            "threshold": 1.2,
            "passed": vol_ratio > 1.2,
        },
        "C5_weekly_macd_bullish": {
            "condition": "MACD line > MACD signal line",
            "actual": round(macd_line, 4),
            "threshold": round(macd_signal, 4),
            "passed": weekly_macd_bullish,
        },
        "C6_institutional_flow": {
            "condition": "Volume ratio > 1.1 (above 30-day average)",
            "actual": round(volume_ratio, 2),
            "threshold": 1.1,
            "passed": volume_ratio > 1.1,
        },
        "C7_composite_signal": {
            "condition": "Composite signal score > 50 (accumulate zone)",
            "actual": round(signals.get("composite_score", 0), 2),
            "threshold": 50,
            "passed": signals.get("composite_score", 0) > 50,
        },
        "C8_no_bearish_regime": {
            "condition": "Regime NOT in STRONG_DOWNTREND",
            "actual": quant["regime"],
            "threshold": "STRONG_DOWNTREND",
            "passed": quant["regime"] != "STRONG_DOWNTREND",
        },
    }

    passed_count = sum(1 for c in checklist.values() if c["passed"])
    total_count = len(checklist)
    trend_confirmed = passed_count >= 6  # Need 6/8 to confirm

    return {
        "checklist": checklist,
        "passed": passed_count,
        "total": total_count,
        "trend_confirmed": trend_confirmed,
        "threshold": f"{6}/{total_count} required",
        "rule": f"IF {6}+ conditions PASS THEN trend_confirmed = TRUE → release dry powder reserve",
    }


# ─── MODULE 4: FUNDAMENTALS KILL SWITCH ───────────────────────────────────────

def compute_fundamentals_kill_switch(
    revenue_growth: float | None = None,
    nrr: float | None = None,
    fcf_margin: float | None = None,
    op_leverage: float | None = None,
    rpo_growth: float | None = None,
) -> dict[str, Any]:
    """MODULE 4: Quarterly earnings scorecard with hard floors."""

    # Default assumptions for NOW based on typical SaaS metrics
    # These would be updated quarterly from actual earnings
    defaults = {
        "revenue_growth": revenue_growth if revenue_growth is not None else 22.0,
        "nrr": nrr if nrr is not None else 125.0,
        "fcf_margin": fcf_margin if fcf_margin is not None else 30.0,
        "op_leverage": op_leverage if op_leverage is not None else 1.5,
        "rpo_growth": rpo_growth if rpo_growth is not None else 24.0,
    }

    floors = {
        "revenue_growth": {"floor": 15.0, "warning": 18.0, "unit": "%"},
        "nrr": {"floor": 115.0, "warning": 120.0, "unit": "%"},
        "fcf_margin": {"floor": 20.0, "warning": 25.0, "unit": "%"},
        "op_leverage": {"floor": 1.0, "warning": 1.2, "unit": "x"},
        "rpo_growth": {"floor": 15.0, "warning": 20.0, "unit": "%"},
    }

    metrics = {}
    breaches = 0
    warnings = 0

    for key, value in defaults.items():
        f = floors[key]
        is_breach = value < f["floor"]
        is_warning = value < f["warning"] and not is_breach
        if is_breach:
            breaches += 1
        if is_warning:
            warnings += 1
        metrics[key] = {
            "value": round(value, 1),
            "floor": f["floor"],
            "warning": f["warning"],
            "unit": f["unit"],
            "status": "BREACH" if is_breach else "WARNING" if is_warning else "PASS",
        }

    # Kill switch logic
    if breaches >= 3:
        response = "FULL_EXIT"
        reduction_pct = 100
    elif breaches == 2:
        response = "REDUCE_50"
        reduction_pct = 50
    elif breaches == 1:
        response = "REDUCE_25"
        reduction_pct = 25
    elif warnings >= 3:
        response = "MONITOR_CLOSELY"
        reduction_pct = 0
    else:
        response = "NO_ACTION"
        reduction_pct = 0

    return {
        "metrics": metrics,
        "breaches": breaches,
        "warnings": warnings,
        "response": response,
        "reduction_pct": reduction_pct,
        "rules": {
            "R1": "IF 3+ metrics breach floor THEN FULL EXIT (100% reduction)",
            "R2": "IF 2 metrics breach floor THEN reduce position 50%",
            "R3": "IF 1 metric breaches floor THEN reduce position 25%",
            "R4": "IF 3+ metrics in warning zone THEN no action but flag for review next quarter",
            "R5": "Floor breaches override all other signals — fundamentals kill switch takes priority",
        },
        "scenario_map": {
            "3_breaches": {"action": "EXIT 100%", "example": "Rev growth <15% AND NRR <115% AND FCF margin <20%"},
            "2_breaches": {"action": "REDUCE 50%", "example": "Rev growth <15% AND NRR <115%"},
            "1_breach": {"action": "REDUCE 25%", "example": "Rev growth <15% (other metrics OK)"},
            "warnings_only": {"action": "MONITOR", "example": "All metrics above floor but 3+ in warning zone"},
        },
    }


# ─── MODULE 5: POSITION SIZING ───────────────────────────────────────────────

def compute_position_sizing(
    portfolio_value: float,
    win_probability: float,
    avg_win: float,
    avg_loss: float,
    current_price: float,
    sector_exposure_pct: float = 0.0,
) -> dict[str, Any]:
    """MODULE 5: Full Kelly Criterion with 0.25 fractional adjustment."""

    # Kelly formula: f* = (bp - q) / b
    # where b = avg_win/avg_loss, p = win_prob, q = 1 - p
    b = avg_win / max(avg_loss, 0.001)
    p = win_probability
    q = 1 - p
    full_kelly = max(0, (b * p - q) / b)

    # Fractional Kelly for long-term hold
    fractional_kelly = full_kelly * 0.25

    # Convert to dollar amounts
    kelly_pct = fractional_kelly * 100
    kelly_dollar = portfolio_value * fractional_kelly

    # Cap rules
    single_stock_cap = 0.05  # 5%
    sector_cap = 0.20        # 20%

    effective_pct = min(kelly_pct / 100, single_stock_cap)
    if sector_exposure_pct + effective_pct > sector_cap:
        effective_pct = max(0, sector_cap - sector_exposure_pct)

    position_size = portfolio_value * effective_pct
    shares = int(position_size / current_price)

    return {
        "kelly_formula": "f* = (bp - q) / b",
        "variables": {
            "b_win_loss_ratio": round(b, 3),
            "p_win_probability": round(p, 3),
            "q_loss_probability": round(q, 3),
        },
        "full_kelly_pct": round(full_kelly * 100, 2),
        "fractional_kelly_pct": round(kelly_pct, 2),
        "fractional_adjustment": 0.25,
        "effective_pct": round(effective_pct * 100, 2),
        "position_size_usd": round(position_size, 2),
        "shares": shares,
        "caps": {
            "single_stock_max": f"{single_stock_cap*100:.0f}%",
            "sector_max": f"{sector_cap*100:.0f}%",
            "current_sector_exposure": f"{sector_exposure_pct*100:.1f}%",
        },
        "binding_constraint": "kelly" if kelly_pct / 100 < single_stock_cap else "single_stock_cap",
        "rules": {
            "R1": f"Full Kelly = ({b:.2f} × {p:.2f} - {q:.2f}) / {b:.2f} = {full_kelly*100:.1f}%",
            "R2": f"Fractional Kelly = {full_kelly*100:.1f}% × 0.25 = {kelly_pct:.1f}%",
            "R3": f"IF kelly_pct > {single_stock_cap*100:.0f}% THEN cap at {single_stock_cap*100:.0f}%",
            "R4": f"IF sector_exposure + position > {sector_cap*100:.0f}% THEN reduce to fill sector cap",
            "R5": f"Deploy ${position_size:,.0f} = {shares:,} shares at ${current_price:.2f}",
        },
    }


# ─── MODULE 6: RISK ARCHITECTURE ─────────────────────────────────────────────

def compute_risk_architecture(
    current_price: float,
    entry_price: float,
    atr: float,
    quant: dict[str, Any],
    portfolio_value: float,
) -> dict[str, Any]:
    """MODULE 6: Full risk architecture with stops, hedges, and tail protection."""

    atr_pct = float(quant["atr"]["atr_pct"])

    # (a) Initial hard stop: 2.5 × ATR below entry
    initial_stop = round(entry_price - (atr * 2.5), 2)
    initial_stop_pct = round((initial_stop - entry_price) / entry_price * 100, 2)

    # (b) Trailing stop: activate when +15% unrealized, trail at 2 × ATR
    trailing_activation = round(entry_price * 1.15, 2)
    trailing_distance = round(atr * 2.0, 2)

    # (c) Volatility-adjusted stop: ATR × 2.5
    vol_stop = round(current_price - (atr * 2.5), 2)
    vol_stop_pct = round((vol_stop - current_price) / current_price * 100, 2)

    # (d) Correlation hedge
    # NOW is high-beta enterprise SaaS — hedge with IGV (iShares Expanded Tech-Software ETF)
    # or short QQQ as partial offset
    hedge_instruments = [
        {"ticker": "IGV", "correlation": 0.85, "hedge_ratio": 0.30, "rationale": "Software sector ETF, high NOW correlation"},
        {"ticker": "QQQ", "correlation": 0.75, "hedge_ratio": 0.25, "rationale": "Nasdaq 100, broad tech hedge"},
        {"ticker": "SPY", "correlation": 0.65, "hedge_ratio": 0.20, "rationale": "S&P 500, broad market hedge"},
    ]
    primary_hedge = hedge_instruments[0]

    # (e) Black swan protection: put spread for -60% tail
    # Buy 10% OTM put, sell 40% OTM put (financing the protection)
    # Typical cost: 1.5-2.5% of notional per year for 3-year hold
    tail_protection = {
        "structure": "Bear put spread: Buy 10% OTM put, Sell 40% OTM put",
        "long_put_strike": round(current_price * 0.90, 2),
        "short_put_strike": round(current_price * 0.60, 2),
        "max_protection": f"-{round((1 - 0.60) * 100)}%",
        "estimated_cost_pct": 2.0,
        "estimated_cost_annual_pct": 0.7,
        "cost_for_3yr_hold": f"${round(portfolio_value * 0.02 * 3):,}",
        "breakeven": f"Protection kicks in below ${round(current_price * 0.90, 2)}",
    }

    return {
        "initial_hard_stop": {
            "price": initial_stop,
            "pct_below_entry": initial_stop_pct,
            "formula": f"Entry ${entry_price} - (ATR ${atr:.2f} × 2.5)",
            "rule": f"IF price touches ${initial_stop} THEN exit entire position, no exceptions",
        },
        "trailing_stop": {
            "activation_price": trailing_activation,
            "activation_pct": round((trailing_activation - entry_price) / entry_price * 100, 2),
            "trail_distance": trailing_distance,
            "formula": f"Activate at +15% from entry, trail at 2 × ATR = ${trailing_distance:.2f}",
            "rule": f"IF unrealized gain >= 15% THEN activate trailing stop at ${trailing_distance:.2f} below high",
        },
        "volatility_stop": {
            "price": vol_stop,
            "pct_below_current": vol_stop_pct,
            "formula": f"Current ${current_price} - (ATR ${atr:.2f} × 2.5)",
            "rule": f"IF price closes below ${vol_stop} THEN reduce position 50%",
        },
        "correlation_hedge": {
            "primary": primary_hedge,
            "alternatives": hedge_instruments[1:],
            "hedge_notional": round(portfolio_value * primary_hedge["hedge_ratio"], 2),
            "rule": f"Maintain {primary_hedge['hedge_ratio']*100:.0f}% short in {primary_hedge['ticker']} as NOW-specific hedge",
        },
        "tail_protection": tail_protection,
        "rules": {
            "R1": f"Hard stop at ${initial_stop} is non-negotiable — algorithm executes, no override",
            "R2": f"Trailing stop activates ONLY after +15% gain — premature trailing kills winners",
            "R3": f"Vol stop at ${vol_stop} triggers 50% reduction, not full exit",
            "R4": f"Hedge {primary_hedge['ticker']} at {primary_hedge['hedge_ratio']*100:.0f}% of NOW notional",
            "R5": "Black swan put spread costs ~2%/yr — pay it. A -60% tail without protection is fund-ending",
        },
    }


# ─── MODULE 7: EXIT PLAYBOOK ─────────────────────────────────────────────────

def compute_exit_playbook(
    current_price: float,
    quant: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    """MODULE 7: DCF scenarios + non-fundamental exit triggers."""

    # DCF assumptions
    scenarios = {
        "bear": {
            "revenue_cagr": 0.15,
            "terminal_fcf_margin": 0.25,
            "discount_rate": 0.12,
            "terminal_multiple": 20,
            "shares_outstanding": 207_000_000,
            "current_revenue": 10_900_000_000,
        },
        "base": {
            "revenue_cagr": 0.20,
            "terminal_fcf_margin": 0.32,
            "discount_rate": 0.10,
            "terminal_multiple": 28,
            "shares_outstanding": 207_000_000,
            "current_revenue": 10_900_000_000,
        },
        "bull": {
            "revenue_cagr": 0.25,
            "terminal_fcf_margin": 0.38,
            "discount_rate": 0.08,
            "terminal_multiple": 35,
            "shares_outstanding": 207_000_000,
            "current_revenue": 10_900_000_000,
        },
    }

    price_targets = {}
    for name, s in scenarios.items():
        # 5-year DCF
        revenues = []
        rev = s["current_revenue"]
        for yr in range(1, 6):
            rev *= (1 + s["revenue_cagr"])
            revenues.append(rev)

        terminal_fcf = revenues[-1] * s["terminal_fcf_margin"]
        terminal_value = terminal_fcf * s["terminal_multiple"]

        # Discount cash flows
        pv_fcfs = sum(
            revenues[i] * s["terminal_fcf_margin"] / (1 + s["discount_rate"]) ** (i + 1)
            for i in range(5)
        )
        pv_terminal = terminal_value / (1 + s["discount_rate"]) ** 5

        equity_value = pv_fcfs + pv_terminal
        price_per_share = equity_value / s["shares_outstanding"]

        price_targets[name] = {
            "price_target": round(price_per_share, 2),
            "upside_pct": round((price_per_share - current_price) / current_price * 100, 1),
            "assumptions": {
                "revenue_cagr": f"{s['revenue_cagr']*100:.0f}%",
                "terminal_fcf_margin": f"{s['terminal_fcf_margin']*100:.0f}%",
                "discount_rate": f"{s['discount_rate']*100:.0f}%",
                "terminal_multiple": f"{s['terminal_multiple']}x",
            },
        }

    # Non-fundamental exit triggers
    rsi_val = float(quant["rsi"]["value"])
    regime = quant["regime"]
    composite = float(signals.get("composite_score", 0))

    momentum_exits = {
        "E1_regime_breakdown": {
            "condition": "Regime shifts to STRONG_DOWNTREND AND price < 200 EMA",
            "threshold": "STRONG_DOWNTREND + below 200 EMA",
            "action": "Exit 50% immediately, trail remainder with 3×ATR stop",
            "currently_triggered": regime == "STRONG_DOWNTREND",
        },
        "E2_rsi_divergence": {
            "condition": "RSI < 30 AND MACD histogram declining for 5+ days",
            "threshold": "RSI < 30",
            "action": "Exit 25% on RSI breakdown, wait for reversal signal",
            "currently_triggered": rsi_val < 30,
        },
        "E3_composite_collapse": {
            "condition": "Composite signal drops below -50",
            "threshold": -50,
            "action": "Full exit — thesis broken from momentum perspective",
            "currently_triggered": composite < -50,
        },
        "E4_volume_drought": {
            "condition": "20-day average volume < 50% of 60-day average",
            "threshold": "Volume ratio < 0.5",
            "action": "Reduce 25% — institutional interest has evaporated",
            "currently_triggered": float(quant.get("volume_ratio", 1.0)) < 0.5,
        },
        "E5_death_cross": {
            "condition": "50-day EMA crosses below 200-day EMA",
            "threshold": "50 EMA < 200 EMA",
            "action": "Exit 30% — macro trend has turned bearish",
            "currently_triggered": float(quant["ema"]["50"]) < float(quant["ema"]["200"]),
        },
    }

    return {
        "dcf_scenarios": price_targets,
        "current_price": current_price,
        "momentum_exit_triggers": momentum_exits,
        "exit_priority": "Fundamentals kill switch (Module 4) > Momentum exits > DCF targets",
        "rules": {
            "R1": "IF bear case target hit THEN take 25% profit",
            "R2": "IF base case target hit THEN take 50% profit",
            "R3": "IF bull case target hit THEN take 75% profit, trail rest",
            "R4": "IF any momentum exit triggers THEN execute immediately — do not wait for earnings",
            "R5": "IF 3+ momentum exits triggered simultaneously THEN full exit regardless of DCF value",
        },
    }


# ─── MODULE 9: PORTFOLIO CONTEXT ─────────────────────────────────────────────

def compute_portfolio_context(
    now_beta: float,
    tech_sector_pct: float,
    portfolio_correlation: float,
    fed_rate_path: str,
    ism_reading: float,
    credit_spread: float,
) -> dict[str, Any]:
    """MODULE 9: Portfolio context rules."""

    correlation_thresholds = {
        "reduce_if_above": 0.80,     # IF portfolio correlation > 0.80 THEN reduce NOW
        "warning_at": 0.65,          # Warning level
        "acceptable_below": 0.50,    # Ideal
    }

    rebalance_triggers = {
        "position_drift": 0.02,      # IF NOW drifts >2% from target weight THEN rebalance
        "sector_drift": 0.05,        # IF tech sector drifts >5% from target THEN rebalance
        "calendar": "quarterly",     # Minimum quarterly rebalance
    }

    macro_conditions = {
        "fed_rate_path": {
            "current": fed_rate_path,
            "re_evaluate_if": "Rate increase >50bps in single meeting OR pause extends >2 quarters",
            "action": "IF rate shock THEN reduce tech exposure 10%, review NOW thesis",
        },
        "ism_manufacturing": {
            "current": ism_reading,
            "re_evaluate_if": "< 48.0 (contraction territory)",
            "action": "IF ISM < 48 THEN reduce cyclical tech exposure, NOW relatively safe (recurring revenue)",
        },
        "credit_spreads": {
            "current": credit_spread,
            "re_evaluate_if": "IG spread > 150bps OR HY spread > 500bps",
            "action": "IF credit stress THEN reduce all equity exposure 15%, NOW by 10%",
        },
    }

    # Tech sector concentration check
    if tech_sector_pct > 0.35:
        sector_action = "REDUCE — tech exceeds 35% of portfolio"
    elif tech_sector_pct > 0.25:
        sector_action = "WARNING — tech at 25-35%, no new adds"
    else:
        sector_action = "OK — tech below 25%, can add to NOW"

    return {
        "correlation_thresholds": correlation_thresholds,
        "current_correlation": portfolio_correlation,
        "correlation_action": "REDUCE" if portfolio_correlation > correlation_thresholds["reduce_if_above"] else "OK",
        "rebalance_triggers": rebalance_triggers,
        "macro_conditions": macro_conditions,
        "sector_concentration": {
            "current_tech_pct": round(tech_sector_pct * 100, 1),
            "action": sector_action,
            "max_tech_pct": 35,
        },
        "rules": {
            "R1": f"IF portfolio_correlation > {correlation_thresholds['reduce_if_above']} THEN reduce NOW position 25%",
            "R2": f"IF tech_sector > 35% THEN no new NOW adds until sector drifts below 30%",
            "R3": f"IF NOW weight drifts > {rebalance_triggers['position_drift']*100:.0f}% from target THEN rebalance",
            "R4": "IF Fed raises >50bps in single meeting THEN pause all accumulation for 30 days",
            "R5": "IF HY credit spread > 500bps THEN reduce NOW 10%, review full thesis",
        },
    }


# ─── MODULE 10: EXECUTION PROTOCOL ───────────────────────────────────────────

def compute_execution_protocol() -> dict[str, Any]:
    """MODULE 10: Order execution protocol."""

    return {
        "order_types": {
            "accumulation": {
                "type": "VWAP",
                "participation_rate": "8-12% of daily volume",
                "time_window": "Full day VWAP (9:30 AM - 4:00 PM ET)",
                "rule": "IF tranche_size < 5000 shares THEN use VWAP over full day",
            },
            "large_tranche": {
                "type": "TWAP",
                "duration": "3-5 days",
                "slice_size": "20% of tranche per day",
                "rule": "IF tranche_size >= 5000 shares THEN use TWAP over 3-5 days",
            },
            "stop_loss": {
                "type": "Market-on-close (MOC)",
                "rule": "IF stop triggered THEN submit MOC order — no limit chasing",
            },
            "emergency": {
                "type": "IOC (Immediate or Cancel)",
                "rule": "IF black swan event detected THEN IOC market order, accept slippage",
            },
        },
        "optimal_timing": {
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "worst_days": ["Monday", "Friday"],
            "best_month_days": ["Day 3-7", "Day 15-17"],
            "worst_month_days": ["Day 1-2 (month-start rebalancing)", "Day 28-31 (month-end window dressing)"],
            "rule": "Concentrate entries Tue-Thu, avoid month-start/end due to institutional flow distortion",
        },
        "intraday_patterns": {
            "best_entry_window": "10:00-10:30 AM ET (after opening volatility settles)",
            "avoid_window": "9:30-10:00 AM ET (opening auction noise)",
            "secondary_window": "2:00-3:00 PM ET (post-lunch dip pattern)",
            "rule": "Schedule VWAP slices to concentrate between 10:00-11:30 and 14:00-15:00",
        },
        "market_impact": {
            "max_daily_volume_pct": 10,
            "max_spread_tolerance_bps": 15,
            "rule": "IF spread > 15bps OR participation > 10% of ADV THEN pause execution",
        },
        "rules": {
            "R1": "Use VWAP for standard accumulation, TWAP for tranches > 5000 shares",
            "R2": "All stop-loss exits use MOC orders — no limit orders on stops",
            "R3": "Concentrate entries Tue-Thu, 10:00-11:30 AM and 2:00-3:00 PM",
            "R4": "Never exceed 10% of daily volume — split across days if needed",
            "R5": "Emergency exits use IOC market orders — accept slippage, prioritize speed",
        },
    }


# ─── ORCHESTRATOR ─────────────────────────────────────────────────────────────

def run_full_trading_system(
    df: pd.DataFrame,
    quote_price: float,
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
) -> dict[str, Any]:
    """Run the complete 10-module trading system."""

    quant = compute_all_indicators(df)
    signals_data = generate_signals(quant, quote_price)

    module1 = compute_signal_stack(df, quote_price, quant)
    module2 = compute_entry_engine(
        quote_price, module1["composite_score"], portfolio_value,
        deployed_capital, trend_confirmed, days_since_last_entry, last_entry_price,
    )
    module3 = compute_trend_confirmation(df, quant, module1)
    module4 = compute_fundamentals_kill_switch()
    module5 = compute_position_sizing(
        portfolio_value, signals_data["buy_prob"] / 100,
        0.03, 0.02, quote_price, sector_exposure_pct,
    )
    module6 = compute_risk_architecture(
        quote_price, last_entry_price, float(quant["atr"]["value"]), quant, portfolio_value,
    )
    module7 = compute_exit_playbook(quote_price, quant, module1)
    module9 = compute_portfolio_context(
        float(quant.get("beta", 1.05)), sector_exposure_pct,
        portfolio_correlation, fed_rate_path, ism_reading, credit_spread,
    )
    module10 = compute_execution_protocol()

    # Module 8: Backtesting framework description
    module8 = {
        "lookback_period": "2018-01-01 to 2024-12-31 (minimum 7 years)",
        "data_inputs": ["Daily OHLCV", "Options OI/put-call", "Institutional 13F filings", "Earnings history"],
        "walk_forward": {
            "train_window": 252,   # 1 year training
            "test_window": 63,     # 1 quarter testing
            "step_size": 63,       # Roll forward quarterly
            "method": "Anchored walk-forward with expanding window",
        },
        "optimization_targets": {
            "sharpe_ratio": {"target": 1.5, "minimum": 1.0},
            "max_drawdown": {"target": -25, "hard_limit": -35},
            "cagr": {"target": 15, "minimum": 10},
            "win_rate": {"target": 55, "minimum": 50},
            "profit_factor": {"target": 1.8, "minimum": 1.3},
        },
        "stress_scenarios": [
            {"name": "2022 Rate Shock", "description": "Fed funds +425bps in 12 months, growth-to-value rotation", "expected_drawdown": "-30 to -40%", "test": "Portfolio survives with <35% drawdown"},
            {"name": "COVID Crash", "description": "-34% in 23 trading days, VIX to 82", "expected_drawdown": "-25 to -35%", "test": "Stops trigger within 3 days, recovery within 6 months"},
            {"name": "Earnings Miss Cascade", "description": "3 consecutive quarters of revenue miss >5%", "expected_drawdown": "-20 to -30%", "test": "Kill switch triggers on 2nd miss, position reduced 50%"},
            {"name": "SaaS Sector Rotation", "description": "IPO SaaS index -50%, multiple compression from 15x to 8x EV/Rev", "expected_drawdown": "-35 to -50%", "test": "Hedge offsets 30% of loss, trailing stops limit damage"},
            {"name": "Liquidity Crisis", "description": "Credit spreads blow to 600bps+, equity outflows 3σ event", "expected_drawdown": "-40 to -55%", "test": "Dry powder allows averaging down at -40%, tail put spread activates"},
        ],
        "rules": {
            "R1": "Minimum 7 years of data for statistical significance",
            "R2": "Walk-forward with 1yr train / 1qtr test to avoid overfitting",
            "R3": "Sharpe < 1.0 in ANY walk-forward window → strategy rejected",
            "R4": "Max drawdown > 35% in ANY stress scenario → reduce position sizing 50%",
            "R5": "All 5 stress scenarios must show positive recovery within 18 months",
        },
    }

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "ticker": "NOW",
        "current_price": quote_price,
        "module_1_signal_stack": module1,
        "module_2_entry_engine": module2,
        "module_3_trend_confirmation": module3,
        "module_4_fundamentals_kill_switch": module4,
        "module_5_position_sizing": module5,
        "module_6_risk_architecture": module6,
        "module_7_exit_playbook": module7,
        "module_8_backtesting": module8,
        "module_9_portfolio_context": module9,
        "module_10_execution_protocol": module10,
    }
