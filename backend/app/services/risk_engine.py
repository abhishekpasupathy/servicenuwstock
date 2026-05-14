from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm


RF = 0.0525


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1


def compute_risk_metrics(df: pd.DataFrame, spy: pd.DataFrame | None = None, win_prob: float = 0.5) -> dict[str, Any]:
    close = df["close"].astype(float)
    returns = close.pct_change().dropna()
    equity = (1 + returns).cumprod()
    dd = drawdown(equity)
    downside = returns[returns < 0]
    sharpe = ((returns.mean() * 252) - RF) / (returns.std() * np.sqrt(252) or np.nan)
    sortino = ((returns.mean() * 252) - RF) / (downside.std() * np.sqrt(252) or np.nan)
    cagr = equity.iloc[-1] ** (252 / max(len(returns), 1)) - 1
    beta = 1.05
    if spy is not None and not spy.empty:
        joined = pd.DataFrame({"asset": returns, "spy": spy["close"].pct_change()}).dropna()
        if len(joined) > 20:
            model = sm.OLS(joined["asset"], sm.add_constant(joined["spy"])).fit()
            beta = float(model.params.get("spy", beta))
    var95_p = float(-(returns.mean() - returns.std() * 1.645) * 100)
    var99_p = float(-(returns.mean() - returns.std() * 2.326) * 100)
    var95_h = float(-np.percentile(returns, 5) * 100)
    var99_h = float(-np.percentile(returns, 1) * 100)
    cvar = float(-returns[returns <= np.percentile(returns, 5)].mean() * 100)
    hv20 = returns.rolling(20).std() * np.sqrt(252) * 100
    vol_pct = float((hv20.dropna() <= hv20.iloc[-1]).mean() * 100) if hv20.notna().any() else 50.0
    avg_win = returns[returns > 0].mean() or 0.02
    avg_loss = abs(returns[returns < 0].mean() or -0.015)
    full_kelly = max(0, (win_prob - (1 - win_prob) / (avg_win / avg_loss if avg_loss else 1))) * 100
    full_kelly = min(25, full_kelly)
    return {
        "max_drawdown_252": round(float(dd.tail(252).min() * 100), 2),
        "max_drawdown_all": round(float(dd.min() * 100), 2),
        "drawdown_series": [{"date": str(d.date() if hasattr(d, "date") else d), "value": round(float(v * 100), 2)} for d, v in zip(df["date"].iloc[-len(dd):], dd)],
        "sharpe_ratio": round(float(np.nan_to_num(sharpe)), 2),
        "sortino_ratio": round(float(np.nan_to_num(sortino)), 2),
        "beta_252": round(beta, 2),
        "var": {"parametric_95": round(var95_p, 2), "parametric_99": round(var99_p, 2), "historical_95": round(var95_h, 2), "historical_99": round(var99_h, 2), "ten_day_95": round(var95_h * np.sqrt(10), 2)},
        "cvar_95": round(cvar, 2),
        "calmar_ratio": round(float(np.nan_to_num(cagr / abs(dd.min()))), 2),
        "volatility_percentile": round(vol_pct, 1),
        "risk_score": round(min(100, max(0, abs(dd.tail(252).min() * 100) * 1.5 + vol_pct * 0.4)), 1),
        "kelly": {"full_kelly_pct": round(full_kelly, 2), "half_kelly_pct": round(full_kelly / 2, 2), "cap_pct": 25},
    }
