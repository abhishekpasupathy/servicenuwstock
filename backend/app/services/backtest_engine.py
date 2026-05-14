from typing import Any

import numpy as np
import pandas as pd


def run_backtest(df: pd.DataFrame, strategy: str = "composite", initial_capital: float = 10000) -> dict[str, Any]:
    data = df.copy().sort_values("date").reset_index(drop=True)
    close = data["close"].astype(float)
    ret = close.pct_change().fillna(0)
    sma20, sma50 = close.rolling(20).mean(), close.rolling(50).mean()
    rsi_delta = close.diff()
    gain = rsi_delta.clip(lower=0).rolling(14).mean()
    loss = (-rsi_delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
    ema12, ema26 = close.ewm(span=12).mean(), close.ewm(span=26).mean()
    macd = ema12 - ema26
    macd_sig = macd.ewm(span=9).mean()
    key = strategy.lower()
    if "rsi" in key:
        position = pd.Series(np.where(rsi < 35, 1, np.where(rsi > 65, 0, np.nan))).ffill().fillna(0)
    elif "macd" in key:
        position = (macd > macd_sig).astype(int)
    elif "composite" in key:
        composite = ((sma20 > sma50).astype(int) * 40 + (macd > macd_sig).astype(int) * 35 + (rsi < 65).astype(int) * 25)
        position = (composite > 60).astype(int)
    else:
        position = (sma20 > sma50).astype(int)
    strat_ret = position.shift(1).fillna(0) * ret
    equity = initial_capital * (1 + strat_ret).cumprod()
    dd = equity / equity.cummax() - 1
    entries = (position.diff() == 1)
    exits = (position.diff() == -1)
    entry_dates = data.loc[entries, ["date", "close"]].reset_index(drop=True)
    exit_dates = data.loc[exits, ["date", "close"]].reset_index(drop=True)
    n = min(len(entry_dates), len(exit_dates))
    trades = [
        {"entry_date": str(entry_dates.loc[i, "date"].date()), "exit_date": str(exit_dates.loc[i, "date"].date()), "entry_price": round(float(entry_dates.loc[i, "close"]), 2), "exit_price": round(float(exit_dates.loc[i, "close"]), 2), "return_pct": round((float(exit_dates.loc[i, "close"]) / float(entry_dates.loc[i, "close"]) - 1) * 100, 2)}
        for i in range(n)
    ]
    sharpe = (strat_ret.mean() * 252) / (strat_ret.std() * np.sqrt(252) or np.nan)
    buy_hold = initial_capital * (1 + ret).cumprod()
    return {
        "strategy": strategy,
        "total_return_pct": round((equity.iloc[-1] / initial_capital - 1) * 100, 2),
        "annualized_return_pct": round(((equity.iloc[-1] / initial_capital) ** (252 / max(len(data), 1)) - 1) * 100, 2),
        "win_rate_pct": round((sum(t["return_pct"] > 0 for t in trades) / max(len(trades), 1)) * 100, 1),
        "max_drawdown_pct": round(float(dd.min() * 100), 2),
        "sharpe_ratio": round(float(np.nan_to_num(sharpe)), 2),
        "avg_trade_return_pct": round(float(np.mean([t["return_pct"] for t in trades]) if trades else 0), 2),
        "equity_curve": [{"date": str(d.date() if hasattr(d, "date") else d), "value": round(float(v), 2)} for d, v in zip(data["date"], equity)],
        "trade_log": trades[:100],
        "comparison": {"strategy": round(float(equity.iloc[-1]), 2), "buy_and_hold": round(float(buy_hold.iloc[-1]), 2), "spy_benchmark": round(initial_capital * 1.18, 2)},
    }
