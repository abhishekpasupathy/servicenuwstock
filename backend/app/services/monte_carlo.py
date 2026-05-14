from typing import Any

import numpy as np
import pandas as pd


def run_monte_carlo(df: pd.DataFrame, simulations: int = 2000, days: int = 90) -> dict[str, Any]:
    close = pd.to_numeric(df["close"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    close = close[close > 0]
    if len(close) < 3:
        close = pd.Series([100.0, 100.5, 101.0])
    current = float(close.iloc[-1])
    returns = np.log(close / close.shift(1)).dropna().tail(252)
    mu = float(returns.mean() * 252)
    sigma = float(returns.std() * np.sqrt(252))
    if not np.isfinite(mu):
        mu = 0.0
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = 0.18
    dt = 1 / 252
    rng = np.random.default_rng(42)
    shocks = rng.normal((mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), size=(simulations, days))
    paths = current * np.exp(np.cumsum(shocks, axis=1))
    sample_idx = rng.choice(simulations, size=min(50, simulations), replace=False)
    sample = paths[sample_idx]
    percentiles = {str(p): [round(float(x), 2) for x in np.percentile(paths, p, axis=0)] for p in [10, 25, 50, 75, 90]}
    final = paths[:, -1]
    hist, edges = np.histogram(final, bins=20)
    return {
        "current_price": round(current, 2),
        "paths_sample": [[round(float(x), 2) for x in row] for row in sample],
        "percentiles": percentiles,
        "final_day_distribution": [{"bin_start": round(float(edges[i]), 2), "bin_end": round(float(edges[i + 1]), 2), "count": int(hist[i])} for i in range(len(hist))],
        "prob_above_current": round(float((final > current).mean() * 100), 1),
        "prob_10pct_gain": round(float((final > current * 1.1).mean() * 100), 1),
        "prob_20pct_gain": round(float((final > current * 1.2).mean() * 100), 1),
        "prob_10pct_loss": round(float((final < current * 0.9).mean() * 100), 1),
        "expected_return_pct": round(float(((final.mean() - current) / current) * 100), 2),
        "confidence_interval_95": [round(float(np.percentile(final, 2.5)), 2), round(float(np.percentile(final, 97.5)), 2)],
    }
