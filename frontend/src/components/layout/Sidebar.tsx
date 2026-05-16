"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, Brain, Crosshair, Gauge, Home, LineChart, Settings, TrendingUp, WalletCards } from "lucide-react";
import { money } from "@/lib/api";
import { useRealtimeQuote } from "@/hooks/useRealtimeQuote";

const nav = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/signals", label: "Signals", icon: Activity },
  { href: "/risk", label: "Risk Analysis", icon: Gauge },
  { href: "/insights", label: "AI Insights", icon: Brain },
  { href: "/portfolio", label: "Portfolio", icon: WalletCards },
  { href: "/prediction", label: "SonsPrediction", icon: TrendingUp },
  { href: "/trading-system", label: "Trading System", icon: Crosshair },
  { href: "/backtest", label: "Backtest", icon: LineChart },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { quote } = useRealtimeQuote("NOW");
  return (
    <aside className="fixed left-0 top-0 z-20 hidden h-screen w-[232px] flex-col border-r border-[var(--border)] bg-[var(--bg-secondary)] md:flex">
      <div className="border-b border-[var(--border)] px-3 py-4">
        <div className="font-mono text-[11px] font-bold text-[var(--amber)]">DADSTOCK PROFESSIONAL</div>
        <div className="mt-1 font-mono text-xl font-black text-[var(--text-primary)]">NOW &lt;EQUITY&gt;</div>
      </div>
      <nav className="flex-1 p-2">
        {nav.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href} className={`mb-1 flex items-center gap-3 border px-3 py-2 font-mono text-xs ${active ? "border-[var(--border-accent)] bg-[var(--amber-bg)] text-[var(--yellow)]" : "border-transparent text-[var(--text-muted)] hover:border-[var(--border)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"}`}>
              <Icon size={15} /> <span className="flex-1">{item.label}</span><span className="text-[10px] text-[var(--text-dim)]">GO</span>
            </Link>
          );
        })}
      </nav>
      <div className="m-2 border border-[var(--border)] bg-[var(--bg-tertiary)] p-3">
        <div className="font-mono text-xs text-[var(--amber)]">LIVE QUOTE</div>
        <div className="mt-1 flex items-end justify-between">
          <span className="font-mono text-xl">{money(quote?.price)}</span>
          <span className={(quote?.change_pct ?? 0) >= 0 ? "positive text-sm" : "negative text-sm"}>{(quote?.change_pct ?? 0).toFixed(1)}%</span>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-1 font-mono text-[10px] text-[var(--text-dim)]">
          <span>SRC {quote?.provider ?? "--"}</span>
          <span className="text-right">F1 HELP</span>
        </div>
      </div>
    </aside>
  );
}
