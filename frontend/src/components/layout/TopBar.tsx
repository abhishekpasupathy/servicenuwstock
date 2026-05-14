"use client";

import { RefreshCw } from "lucide-react";
import { money, useApi } from "@/lib/api";
import type { Quote } from "@/lib/types";

export function TopBar() {
  const { data, mutate } = useApi<Quote>("/quote/NOW");
  const positive = (data?.change ?? 0) >= 0;
  return (
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-secondary)] px-5">
      <div>
        <div className="text-sm text-[var(--text-muted)]">ServiceNow Inc.</div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-xl font-semibold">NOW</span>
          <span className="font-mono">{money(data?.price)}</span>
          <span className={positive ? "positive" : "negative"}>{positive ? "+" : ""}{data?.change_pct?.toFixed(2) ?? "0.00"}%</span>
          <span className="live-dot" />
          <span className="text-xs text-[var(--green)]">LIVE</span>
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
        {data?.stale ? <span className="rounded bg-[var(--amber-bg)] px-2 py-1 text-[var(--amber)]">Using last known data</span> : null}
        <span className="rounded border border-[var(--border)] px-2 py-1">{data?.source ?? "loading"}</span>
        <span>{data?.timestamp ? new Date(data.timestamp).toLocaleTimeString() : "--"}</span>
        <button aria-label="Refresh quote" onClick={() => mutate()} className="rounded border border-[var(--border)] p-2 hover:bg-[var(--bg-hover)]"><RefreshCw size={14} /></button>
      </div>
    </header>
  );
}
