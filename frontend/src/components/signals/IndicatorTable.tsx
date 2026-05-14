import type { Signals } from "@/lib/types";

export function IndicatorTable({ signals }: { signals?: Signals }) {
  const rows = Object.entries(signals?.indicator_breakdown ?? {});
  return (
    <div className="terminal-card overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-[var(--bg-tertiary)] text-xs uppercase text-[var(--text-muted)]">
          <tr><th className="p-3 text-left">Indicator</th><th>Raw Score</th><th>Weight</th><th>Contribution</th><th>Signal</th></tr>
        </thead>
        <tbody>
          {rows.map(([name, r]) => (
            <tr key={name} className="border-t border-[var(--border)]">
              <td className="p-3 font-mono">{name}</td><td className="text-center">{r.score}</td><td className="text-center">{r.weight}</td><td className="text-center">{r.contribution}</td><td className={`text-center ${r.signal === "bullish" ? "positive" : r.signal === "bearish" ? "negative" : "neutral"}`}>{r.signal}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
