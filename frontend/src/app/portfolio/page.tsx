"use client";

import { useState } from "react";
import { api, money, useApi } from "@/lib/api";

type Holding = { id: number; ticker: string; shares: number; avg_buy_price: number; current_price: number; total_value: number; pnl: number; pnl_pct: number };

export default function PortfolioPage() {
  const { data, mutate } = useApi<Holding[]>("/portfolio/holdings");
  const [shares, setShares] = useState("100");
  const [avg, setAvg] = useState("85");
  async function add() {
    await api("/portfolio/holdings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticker: "NOW", shares: Number(shares), avg_buy_price: Number(avg) }) });
    mutate();
  }
  const invested = (data ?? []).reduce((s, h) => s + h.shares * h.avg_buy_price, 0);
  const value = (data ?? []).reduce((s, h) => s + h.total_value, 0);
  return (
    <div className="space-y-4">
      <section className="terminal-card flex gap-3 p-4"><input className="bg-[var(--bg-tertiary)] p-2" value="NOW" readOnly /><input className="bg-[var(--bg-tertiary)] p-2" value={shares} onChange={(e) => setShares(e.target.value)} /><input className="bg-[var(--bg-tertiary)] p-2" value={avg} onChange={(e) => setAvg(e.target.value)} /><button onClick={add} className="rounded bg-[var(--green)] px-4 text-[var(--bg-primary)]">Add Holding</button></section>
      <section className="terminal-card p-4"><div>Total invested {money(invested)} | Current value {money(value)} | P&L <span className={value >= invested ? "positive" : "negative"}>{money(value - invested)}</span></div></section>
      <section className="terminal-card overflow-hidden"><table className="w-full text-sm"><thead><tr className="text-[var(--text-muted)]"><th className="p-3 text-left">Ticker</th><th>Shares</th><th>Avg Buy</th><th>Current</th><th>Total Value</th><th>P&L</th><th>Signal</th></tr></thead><tbody>{(data ?? []).map((h) => <tr key={h.id} className="border-t border-[var(--border)]"><td className="p-3">{h.ticker}</td><td className="text-center">{h.shares}</td><td className="text-center">{money(h.avg_buy_price)}</td><td className="text-center">{money(h.current_price)}</td><td className="text-center">{money(h.total_value)}</td><td className={`text-center ${h.pnl >= 0 ? "positive" : "negative"}`}>{money(h.pnl)} ({h.pnl_pct}%)</td><td className="text-center text-[var(--amber)]">HOLD</td></tr>)}</tbody></table></section>
    </div>
  );
}
