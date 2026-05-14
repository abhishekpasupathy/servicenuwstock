"use client";

import { useApi } from "@/lib/api";

type Diagnostics = {
  status?: string;
  environment?: string;
  api_prefix?: string;
  default_ticker?: string;
  checks?: Record<string, string | boolean | number>;
};

export default function SettingsPage() {
  const { data, mutate } = useApi<Diagnostics>("/health/diagnostics", 30000);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="terminal-card space-y-3 p-4">
        <h2 className="font-mono text-sm uppercase text-[var(--amber)]">System Diagnostics</h2>
        <div className="grid grid-cols-2 gap-2 font-mono text-xs">
          <span>Status</span><span className={data?.status === "ok" ? "positive" : "neutral"}>{data?.status ?? "--"}</span>
          <span>Environment</span><span>{data?.environment ?? "--"}</span>
          <span>API Prefix</span><span>{data?.api_prefix ?? "--"}</span>
          <span>Default Ticker</span><span>{data?.default_ticker ?? "--"}</span>
        </div>
        <button className="terminal-button" onClick={() => mutate()}>Run Check</button>
      </section>
      <section className="terminal-card space-y-3 p-4">
        <h2 className="font-mono text-sm uppercase text-[var(--amber)]">Data Checks</h2>
        <div className="space-y-2 font-mono text-xs">
          {Object.entries(data?.checks ?? {}).map(([key, value]) => (
            <div key={key} className="flex justify-between border-b border-[var(--border)] pb-2">
              <span>{key.toUpperCase()}</span>
              <span className={value === true || value === "yfinance" ? "positive" : value ? "neutral" : "negative"}>{String(value)}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="terminal-card space-y-3 p-4">
        <h2 className="font-mono text-sm uppercase text-[var(--amber)]">Terminal Preferences</h2>
        <select className="terminal-input w-full"><option>60s refresh</option><option>30s refresh</option><option>5min refresh</option></select>
        <select className="terminal-input w-full"><option>1Y default range</option><option>6M default range</option></select>
      </section>
      <section className="terminal-card space-y-3 p-4">
        <h2 className="font-mono text-sm uppercase text-[var(--amber)]">Alert Template</h2>
        <input className="terminal-input w-full" defaultValue="NOW crosses previous close by 2%" />
        <input className="terminal-input w-full" defaultValue="Composite signal moves below -25" />
      </section>
    </div>
  );
}
