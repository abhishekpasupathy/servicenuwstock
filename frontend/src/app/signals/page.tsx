"use client";

import { ProbabilityBar } from "@/components/signals/ProbabilityBar";
import { IndicatorTable } from "@/components/signals/IndicatorTable";
import { useApi } from "@/lib/api";
import type { Signals } from "@/lib/types";

export default function SignalsPage() {
  const { data } = useApi<Signals>("/signals/NOW");
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <ProbabilityBar label="BUY" value={data?.buy_prob ?? 0} color="#00d4aa" />
        <ProbabilityBar label="HOLD" value={data?.hold_prob ?? 0} color="#f0c040" />
        <ProbabilityBar label="SELL" value={data?.sell_prob ?? 0} color="#ff4d6d" />
      </div>
      <section className="terminal-card p-5">
        <div className="h-3 rounded bg-gradient-to-r from-[var(--red)] via-[var(--amber)] to-[var(--green)]" />
        <div className="mt-3 flex items-center justify-between"><span>Composite {data?.composite_score ?? 0}</span><span className="text-2xl">{data?.action}</span><span>{"★".repeat(data?.signal_strength ?? 1)}{"☆".repeat(5 - (data?.signal_strength ?? 1))}</span></div>
        <p className="mt-2 text-sm text-[var(--text-muted)]">Confidence based on {data?.agreement ?? "0/10"} indicators in agreement.</p>
      </section>
      <IndicatorTable signals={data} />
      <section className="terminal-card p-4 text-sm text-[var(--text-muted)]">Based on backtested data from 2020-2024, this signal pattern is estimated from local strategy simulation rather than a paid prediction API.</section>
    </div>
  );
}
