"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, Brain, Gauge, Home, LineChart, Settings, WalletCards } from "lucide-react";
import { money, useApi } from "@/lib/api";
import type { Quote } from "@/lib/types";

const nav = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/signals", label: "Signals", icon: Activity },
  { href: "/risk", label: "Risk Analysis", icon: Gauge },
  { href: "/insights", label: "AI Insights", icon: Brain },
  { href: "/portfolio", label: "Portfolio", icon: WalletCards },
  { href: "/backtest", label: "Backtest", icon: LineChart },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data } = useApi<Quote>("/market/quote/NOW");
  return (
    <aside className="fixed left-0 top-0 z-20 flex h-screen w-[220px] flex-col border-r border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="border-b border-[var(--border)] px-4 py-5 font-mono text-lg font-bold text-[var(--green)]">NOW TERMINAL</div>
      <nav className="flex-1 p-2">
        {nav.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href} className={`mb-1 flex items-center gap-3 rounded-md px-3 py-2 text-sm ${active ? "bg-[var(--bg-hover)] text-[var(--green)]" : "text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"}`}>
              <Icon size={16} /> {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="m-3 rounded-md border border-[var(--border)] bg-[var(--bg-tertiary)] p-3">
        <div className="text-xs text-[var(--text-muted)]">NOW LIVE</div>
        <div className="mt-1 flex items-end justify-between">
          <span className="font-mono text-xl">{money(data?.price)}</span>
          <span className={(data?.change_pct ?? 0) >= 0 ? "positive text-sm" : "negative text-sm"}>{(data?.change_pct ?? 0).toFixed(1)}%</span>
        </div>
      </div>
    </aside>
  );
}
