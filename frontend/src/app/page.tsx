"use client";

import { PriceChart } from "@/components/charts/PriceChart";
import { LinePanel } from "@/components/charts/LinePanel";
import { QuoteCard } from "@/components/dashboard/QuoteCard";
import { SignalGauge } from "@/components/dashboard/SignalGauge";
import { money, useApi } from "@/lib/api";
import type { Bar, Quote, Signals } from "@/lib/types";

export default function Dashboard() {
  const { data: quote } = useApi<Quote>("/quote/NOW");
  const { data: bars } = useApi<Bar[]>("/history/NOW?period=1y&interval=1d");
  const { data: signals } = useApi<Signals>("/signals/NOW");
  const line = (bars ?? []).map((b) => ({ time: b.date, value: b.close }));
  const isFallback = Boolean(quote?.stale || quote?.source === "sample" || quote?.source === "cache");
  return (
    <div className="space-y-4">
      {isFallback ? (
        <section className="terminal-card border-[var(--amber)] p-3 text-sm text-[var(--amber)]">
          Fallback/Sample Data
        </section>
      ) : null}
      <div className="grid grid-cols-4 gap-4">
        <QuoteCard label="Volume" value={(quote?.volume ?? 0).toLocaleString()} />
        <QuoteCard label="Prev Close" value={quote?.prev_close ?? 0} />
        <QuoteCard label="Day Range" value={`${money(quote?.day_low)} - ${money(quote?.day_high)}`} />
        <QuoteCard label="52W Range" value={`${money(quote?.week_52_low)} - ${money(quote?.week_52_high)}`} />
      </div>
      <div className="grid grid-cols-[minmax(0,7fr)_minmax(280px,3fr)] gap-4">
        <section className="terminal-card p-3"><PriceChart bars={bars} /></section>
        <aside className="space-y-4">
          <SignalGauge score={signals?.composite_score ?? 0} />
          <div className="terminal-card p-4"><div className="text-xs text-[var(--text-muted)]">Action</div><div className="mt-2 text-3xl font-semibold text-[var(--green)]">{signals?.action ?? "LOADING"}</div><div className="text-sm text-[var(--text-muted)]">Confidence {signals?.confidence ?? 0}%</div></div>
          <div className="terminal-card grid grid-cols-2 gap-3 p-4 text-sm"><span>P/E {quote?.pe_ratio?.toFixed(1) ?? "--"}</span><span>Market Cap {money((quote?.market_cap ?? 0) / 1e9)}B</span><span>Avg Vol {(quote?.avg_volume ?? 0).toLocaleString()}</span><span>Source {quote?.source}</span></div>
        </aside>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <section className="terminal-card p-3"><h2 className="mb-2 text-sm text-[var(--text-muted)]">RSI Proxy</h2><LinePanel data={line.slice(-120)} color="#f0c040" /></section>
        <section className="terminal-card p-3"><h2 className="mb-2 text-sm text-[var(--text-muted)]">MACD Proxy</h2><LinePanel data={line.slice(-120).map((x, i) => ({ ...x, value: i ? x.value - line.slice(-120)[i - 1].value : 0 }))} color="#00d4aa" /></section>
        <section className="terminal-card p-3"><h2 className="mb-2 text-sm text-[var(--text-muted)]">Close Trend</h2><LinePanel data={line.slice(-120)} color="#4488ff" /></section>
      </div>
    </div>
  );
}
