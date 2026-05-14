"use client";

import { LinePanel } from "@/components/charts/LinePanel";
import { QuoteCard } from "@/components/dashboard/QuoteCard";
import { useApi } from "@/lib/api";

type Risk = { sharpe_ratio?: number; max_drawdown_all?: number; beta_252?: number; risk_score?: number; volatility_percentile?: number; drawdown_series?: { date: string; value: number }[]; var?: Record<string, number>; kelly?: { full_kelly_pct: number; half_kelly_pct: number } };
type Monte = { percentiles?: Record<string, number[]> };

export default function RiskPage() {
  const { data: risk } = useApi<Risk>("/risk/NOW");
  const { data: monte } = useApi<Monte>("/monte-carlo/NOW");
  const dd = (risk?.drawdown_series ?? []).map((x) => ({ time: x.date, value: x.value }));
  const p50 = (monte?.percentiles?.["50"] ?? []).map((v, i) => ({ time: `2026-05-${String((i % 28) + 1).padStart(2, "0")}`, value: v }));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4"><QuoteCard label="Sharpe Ratio" value={risk?.sharpe_ratio ?? 0} /><QuoteCard label="Max Drawdown" value={`${risk?.max_drawdown_all ?? 0}%`} /><QuoteCard label="Beta vs SPY" value={risk?.beta_252 ?? 0} /><QuoteCard label="VaR 95%" value={`${risk?.var?.historical_95 ?? 0}%`} /></div>
      <div className="grid grid-cols-[3fr_2fr] gap-4"><section className="terminal-card p-3"><LinePanel data={dd} color="#ff4d6d" height={320} /></section><section className="terminal-card p-4"><div className="text-4xl text-[var(--amber)]">{risk?.risk_score ?? 0}/100</div><p className="mt-2 text-sm text-[var(--text-muted)]">Volatility percentile {risk?.volatility_percentile ?? 0}%</p><pre className="mt-4 text-xs text-[var(--text-muted)]">{JSON.stringify(risk?.var ?? {}, null, 2)}</pre></section></div>
      <section className="terminal-card p-3"><h2 className="mb-2 text-sm text-[var(--text-muted)]">Monte Carlo Fan Chart Median</h2><LinePanel data={p50} color="#00d4aa" height={320} /></section>
      <section className="terminal-card p-4">Kelly Calculator: full Kelly {risk?.kelly?.full_kelly_pct ?? 0}% | half Kelly recommended {risk?.kelly?.half_kelly_pct ?? 0}% of portfolio.</section>
    </div>
  );
}
