"use client";

import { InsightPanel } from "@/components/insights/InsightPanel";
import { API_BASE, useApi } from "@/lib/api";

type Insight = { verdict?: string; confidence?: number; generated_at?: string; plain_english_summary?: string; bullish_reasons?: string[]; bearish_risks?: string[]; key_levels?: Record<string, number>; monte_carlo_narrative?: string; technical_summary?: string };

export default function InsightsPage() {
  const { data, mutate } = useApi<Insight>("/insights/NOW");
  return (
    <div className="space-y-4">
      <section className="terminal-card p-6">
        <div className="text-3xl font-semibold text-[var(--green)]">{data?.verdict ?? "Loading analysis"}</div>
        <div className="mt-2 text-sm text-[var(--text-muted)]">Confidence {data?.confidence ?? 0}% | Updated {data?.generated_at ? new Date(data.generated_at).toLocaleTimeString() : "--"}</div>
        <button onClick={() => mutate()} className="terminal-button mt-4">Refresh Analysis</button>
      </section>
      <InsightPanel title="Plain English Summary"><p className="text-base leading-8 text-[var(--text-primary)]">{data?.plain_english_summary}</p></InsightPanel>
      <div className="grid grid-cols-2 gap-4">
        <InsightPanel title="Bullish Signals"><ul className="space-y-2">{(data?.bullish_reasons ?? []).map((x: string) => <li key={x} className="positive">✓ {x}</li>)}</ul></InsightPanel>
        <InsightPanel title="Key Risks"><ul className="space-y-2">{(data?.bearish_risks ?? []).map((x: string) => <li key={x} className="negative">! {x}</li>)}</ul></InsightPanel>
      </div>
      <InsightPanel title="Key Price Levels"><div className="grid grid-cols-4 gap-3 font-mono">{Object.entries(data?.key_levels ?? {}).map(([k, v]) => <div key={k}>{k}: ${Number(v).toFixed(2)}</div>)}</div></InsightPanel>
      <InsightPanel title="Monte Carlo Summary"><p className="leading-7 text-[var(--text-muted)]">{data?.monte_carlo_narrative}</p></InsightPanel>
      <a className="terminal-button inline-block" href={`${API_BASE}/insights/NOW/pdf`}>Export PDF</a>
      <details className="terminal-card p-4"><summary>Show Technical Details</summary><p className="mt-3 text-sm text-[var(--text-muted)]">{data?.technical_summary}</p></details>
    </div>
  );
}
