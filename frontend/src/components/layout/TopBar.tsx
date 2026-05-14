"use client";

import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { money, useApi } from "@/lib/api";
import type { MarketStatus } from "@/lib/types";
import { useRealtimeQuote } from "@/hooks/useRealtimeQuote";

function relativeTime(date: Date | null, tick: number): string {
  void tick;
  if (!date) return "waiting";
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 2) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  return `${Math.floor(seconds / 60)}m ago`;
}

export function TopBar() {
  const { quote, connected, lastUpdate, transport } = useRealtimeQuote("NOW");
  const { data: marketStatus, mutate } = useApi<MarketStatus>("/market/status");
  const [tick, setTick] = useState(0);
  const previousPrice = useRef<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    const id = setInterval(() => setTick((value) => value + 1), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!quote) return;
    if (previousPrice.current !== null && quote.price !== previousPrice.current) {
      setFlash(quote.price > previousPrice.current ? "up" : "down");
      const timeout = setTimeout(() => setFlash(null), 500);
      previousPrice.current = quote.price;
      return () => clearTimeout(timeout);
    }
    previousPrice.current = quote.price;
  }, [quote]);

  const positive = (quote?.change ?? 0) >= 0;
  const status = useMemo(() => {
    if (!connected) return { label: "OFFLINE", className: "negative", dot: "bg-[var(--red)]" };
    if (marketStatus && !marketStatus.is_open) return { label: marketStatus.status.replace("_", " "), className: "neutral", dot: "bg-[var(--amber)]" };
    if (quote?.stale) return { label: "OFFLINE", className: "negative", dot: "bg-[var(--red)]" };
    if (quote?.delayed || transport === "sse") return { label: "DELAYED", className: "neutral", dot: "bg-[var(--amber)]" };
    return { label: "LIVE", className: "positive", dot: "bg-[var(--green)]" };
  }, [connected, marketStatus, quote?.delayed, quote?.stale, transport]);
  const priceClass = flash === "up" ? "text-[var(--green)]" : flash === "down" ? "text-[var(--red)]" : "text-[var(--yellow)]";

  return (
    <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="flex h-11 items-center justify-between px-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="font-mono text-xs text-[var(--amber)]">DADSTOCK</span>
          <span className="hidden font-mono text-xs text-[var(--text-muted)] sm:inline">REALTIME EQUITY</span>
          <span className="font-mono text-lg font-black">NOW</span>
          <span className={`font-mono text-lg transition-colors duration-300 ${priceClass}`}>{money(quote?.price)}</span>
          <span className={`font-mono text-sm ${positive ? "positive" : "negative"}`}>{positive ? "+" : ""}{quote?.change_pct?.toFixed(2) ?? "0.00"}%</span>
          <span className={`h-2 w-2 rounded-full ${status.dot} ${connected ? "animate-pulse" : ""}`} />
          <span className={`font-mono text-[11px] ${status.className}`}>{status.label}</span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-[var(--text-muted)]">
          {quote?.bid && quote?.ask ? <span className="hidden sm:inline">Bid {money(quote.bid)} · Ask {money(quote.ask)}</span> : null}
          <span className="hidden border border-[var(--border)] px-2 py-1 sm:inline">{quote?.provider ?? "connecting"}</span>
          <span>Updated {relativeTime(lastUpdate, tick)}</span>
          <button aria-label="Refresh market status" onClick={() => mutate()} className="terminal-button !p-2"><RefreshCw size={13} /></button>
        </div>
      </div>
      <div className="flex h-7 items-center gap-4 overflow-hidden border-t border-[var(--border)] px-3 font-mono text-[11px] text-[var(--text-muted)]">
        <span className="text-[var(--amber)]">F1 HELP</span>
        <span>WS {connected ? "CONNECTED" : "RECONNECTING"}</span>
        <span>ALT+S SIGNALS</span>
        <span>ALT+R RISK</span>
        <span>{marketStatus?.message ?? "Checking NYSE session"}</span>
      </div>
    </header>
  );
}
