"use client";

import { money } from "@/lib/api";
import { useRealtimeQuote } from "@/hooks/useRealtimeQuote";

const WATCHLIST = ["NOW", "CRM", "SNOW", "WDAY", "MSFT", "SPY"];

function LiveTickerItem({ ticker }: { ticker: string }) {
  const { quote, connected } = useRealtimeQuote(ticker);
  const positive = (quote?.change_pct ?? 0) >= 0;
  return (
    <span className="mx-5 inline-flex items-center gap-2 whitespace-nowrap font-mono text-[11px]">
      <span className="text-[var(--amber)]">{ticker}</span>
      <span className="text-[var(--text-primary)]">{quote ? money(quote.price) : "--"}</span>
      <span className={positive ? "positive" : "negative"}>{positive ? "+" : ""}{quote?.change_pct?.toFixed(2) ?? "0.00"}%</span>
      <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-[var(--green)]" : "bg-[var(--red)]"}`} />
    </span>
  );
}

export function LiveTickerBar() {
  const row = WATCHLIST.map((ticker) => <LiveTickerItem key={ticker} ticker={ticker} />);
  return (
    <div className="sticky top-0 z-20 overflow-hidden border-b border-[var(--border)] bg-[#030405] py-1.5">
      <div className="ticker-marquee hover:[animation-play-state:paused]">
        {row}
        {row.map((item, index) => <span key={`copy-${index}`}>{item}</span>)}
      </div>
    </div>
  );
}
