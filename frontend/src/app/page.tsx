"use client";

import { PriceChart } from "@/components/charts/PriceChart";
import { LinePanel } from "@/components/charts/LinePanel";
import { QuoteCard } from "@/components/dashboard/QuoteCard";
import { SignalGauge } from "@/components/dashboard/SignalGauge";
import { money, useApi } from "@/lib/api";
import type { Bar, Quote, Signals } from "@/lib/types";
import { useRealtimeQuote } from "@/hooks/useRealtimeQuote";

export default function Dashboard() {
  const { data: quote, isLoading: quoteLoading } = useApi<Quote>("/quote/NOW");
  const { quote: liveQuote } = useRealtimeQuote("NOW");
  const { data: bars } = useApi<Bar[]>("/history/NOW?period=1y&interval=1d");
  const { data: signals } = useApi<Signals>("/signals/NOW");
  const line = (bars ?? []).map((b) => ({ time: b.date, value: b.close }));
  const displayQuote = liveQuote ?? quote;
  const isFallback = Boolean(liveQuote?.delayed || liveQuote?.stale || quote?.stale || quote?.source === "sample" || quote?.source === "cache");
  const isLoading = quoteLoading && !displayQuote?.price;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="terminal-card p-4 animate-pulse">
              <div className="h-3 w-16 rounded bg-[var(--border)]" />
              <div className="mt-2 h-8 w-24 rounded bg-[var(--border)]" />
            </div>
          ))}
        </div>
        <div className="terminal-card h-[400px] animate-pulse p-3" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {isFallback ? (
        <section className="terminal-card border-[var(--amber)] p-3 text-sm text-[var(--amber)]">
          Fallback/Sample Data
        </section>
      ) : null}
      <div className="grid grid-cols-4 gap-4">
        <QuoteCard label="Volume" value={displayQuote?.volume ? displayQuote.volume.toLocaleString() : "--"} />
        <QuoteCard label="Prev Close" value={quote?.prev_close ? money(quote.prev_close) : "--"} />
        <QuoteCard label="Day Range" value={quote?.day_low ? `${money(quote.day_low)} - ${money(quote.day_high)}` : "--"} />
        <QuoteCard label="52W Range" value={quote?.week_52_low ? `${money(quote.week_52_low)} - ${money(quote.week_52_high)}` : "--"} />
      </div>
      <div className="grid grid-cols-[minmax(0,7fr)_minmax(280px,3fr)] gap-4">
        <section className="terminal-card p-3"><PriceChart bars={bars} realtimePrice={liveQuote?.price} /></section>
        <aside className="space-y-4">
          <SignalGauge score={signals?.composite_score ?? 0} />
          <div className="terminal-card p-4"><div className="text-xs text-[var(--text-muted)]">Action</div><div className="mt-2 text-3xl font-semibold text-[var(--green)]">{signals?.action ?? "LOADING"}</div><div className="text-sm text-[var(--text-muted)]">Confidence {signals?.confidence ?? 0}%</div></div>
          <div className="terminal-card grid grid-cols-2 gap-3 p-4 text-sm"><span>P/E {quote?.pe_ratio?.toFixed(1) ?? "--"}</span><span>Market Cap {quote?.market_cap ? `${money(quote.market_cap / 1e9)}B` : "--"}</span><span>Avg Vol {quote?.avg_volume ? quote.avg_volume.toLocaleString() : "--"}</span><span>Source {liveQuote?.provider ?? quote?.source ?? "--"}</span></div>
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
