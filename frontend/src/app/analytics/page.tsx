"use client";

import { LinePanel } from "@/components/charts/LinePanel";
import { IndicatorTable } from "@/components/signals/IndicatorTable";
import { useApi } from "@/lib/api";
import type { Bar, Signals } from "@/lib/types";

type Quant = { regime?: string; adx?: { value?: number } };

export default function Analytics() {
  const { data: bars } = useApi<Bar[]>("/market/ohlcv/NOW?period=1y&interval=1d");
  const { data: quant } = useApi<Quant>("/quant/indicators/NOW");
  const { data: signals } = useApi<Signals>("/signals/NOW");
  const line = (bars ?? []).map((b) => ({ time: b.date, value: b.close }));
  return (
    <div className="space-y-4">
      <section className="terminal-card p-4"><div className="text-xs uppercase text-[var(--text-muted)]">Regime</div><div className="mt-2 text-3xl text-[var(--green)]">{quant?.regime ?? "LOADING"}</div><p className="mt-2 text-sm text-[var(--text-muted)]">ADX {quant?.adx?.value?.toFixed?.(1) ?? "--"} shows current trend strength in plain English: higher values mean the move is more defined.</p></section>
      <div className="grid grid-cols-5 gap-2 text-sm">{["Trend", "Momentum", "Volatility", "Volume", "Regime"].map((x) => <div key={x} className="terminal-card p-3 text-center text-[var(--text-muted)]">{x}</div>)}</div>
      <section className="terminal-card p-3"><LinePanel data={line} height={360} /></section>
      <IndicatorTable signals={signals} />
    </div>
  );
}
