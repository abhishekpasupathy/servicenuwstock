import { money } from "@/lib/api";

export function QuoteCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="terminal-card p-4">
      <div className="text-xs uppercase text-[var(--text-muted)]">{label}</div>
      <div className="mt-2 font-mono text-2xl">{typeof value === "number" ? money(value) : value}</div>
      {sub ? <div className="mt-1 text-xs text-[var(--text-dim)]">{sub}</div> : null}
    </div>
  );
}
