"use client";

import { RefreshCw } from "lucide-react";
import { money, useApi } from "@/lib/api";
import type { Quote } from "@/lib/types";

export function TopBar() {
  const { data, mutate } = useApi<Quote>("/quote/NOW");
  const positive = (data?.change ?? 0) >= 0;
  return (
    <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="flex h-11 items-center justify-between px-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="font-mono text-xs text-[var(--amber)]">DADSTOCK</span>
          <span className="hidden font-mono text-xs text-[var(--text-muted)] sm:inline">EQUITY ANALYTICS</span>
          <span className="font-mono text-lg font-black">NOW</span>
          <span className="font-mono text-lg text-[var(--yellow)]">{money(data?.price)}</span>
          <span className={`font-mono text-sm ${positive ? "positive" : "negative"}`}>{positive ? "+" : ""}{data?.change_pct?.toFixed(2) ?? "0.00"}%</span>
          <span className="live-dot" />
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-[var(--text-muted)]">
          {data?.stale ? <span className="bg-[var(--amber-bg)] px-2 py-1 text-[var(--amber)]">DEGRADED</span> : <span className="text-[var(--green)]">LIVE</span>}
          <span className="hidden border border-[var(--border)] px-2 py-1 sm:inline">{data?.source ?? "loading"}</span>
          <span>{data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : "--"}</span>
          <button aria-label="Refresh quote" onClick={() => mutate()} className="terminal-button !p-2"><RefreshCw size={13} /></button>
        </div>
      </div>
      <div className="flex h-7 items-center gap-4 overflow-hidden border-t border-[var(--border)] px-3 font-mono text-[11px] text-[var(--text-muted)]">
        <span className="text-[var(--amber)]">F1 HELP</span>
        <span>F5 REFRESH</span>
        <span>ALT+S SIGNALS</span>
        <span>ALT+R RISK</span>
        <span>DATA: {data?.stale ? "FALLBACK" : "REALTIME/DELAYED"}</span>
      </div>
    </header>
  );
}
