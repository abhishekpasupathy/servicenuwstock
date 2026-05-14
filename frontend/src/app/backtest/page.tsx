"use client";

import { useState } from "react";
import { LinePanel } from "@/components/charts/LinePanel";
import { api } from "@/lib/api";

type BacktestResult = { total_return_pct: number; win_rate_pct: number; max_drawdown_pct: number; sharpe_ratio: number; equity_curve: { date: string; value: number }[]; comparison: { strategy: number; buy_and_hold: number; spy_benchmark: number } };

export default function BacktestPage() {
  const [result, setResult] = useState<BacktestResult>();
  const [loading, setLoading] = useState(false);
  async function run() {
    setLoading(true);
    try {
      setResult(await api<BacktestResult>("/backtest?ticker=NOW&strategy=composite&from=2022-01-01&to=2024-12-31", { method: "POST" }));
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="space-y-4">
      <section className="terminal-card flex flex-wrap items-center gap-3 p-3"><select className="terminal-input"><option>Composite Score</option><option>SMA Crossover</option><option>RSI Mean Reversion</option><option>MACD Signal</option></select><input type="date" defaultValue="2022-01-01" className="terminal-input" /><input type="date" defaultValue="2024-12-31" className="terminal-input" /><input defaultValue="10000" className="terminal-input" /><button onClick={run} className="terminal-button">{loading ? "Running..." : "Run Backtest"}</button></section>
      {result ? <><div className="grid grid-cols-4 gap-4">{(["total_return_pct", "win_rate_pct", "max_drawdown_pct", "sharpe_ratio"] as const).map((k) => <div key={k} className="terminal-card p-4"><div className="text-xs text-[var(--text-muted)]">{k}</div><div className="mt-2 font-mono text-2xl">{result[k]}</div></div>)}</div><section className="terminal-card p-3"><LinePanel data={result.equity_curve.map((x) => ({ time: x.date, value: x.value }))} height={320} /></section><section className="terminal-card p-4">Strategy ${result.comparison.strategy} vs Buy-and-Hold ${result.comparison.buy_and_hold} vs SPY ${result.comparison.spy_benchmark}</section></> : <section className="terminal-card p-6 text-[var(--text-muted)]">Run a backtest to see results.</section>}
    </div>
  );
}
