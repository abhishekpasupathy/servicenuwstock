export function ProbabilityBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="terminal-card p-4 text-center">
      <div className="mx-auto grid h-28 w-28 place-items-center rounded-full border-8" style={{ borderColor: color }}>
        <div>
          <div className="font-mono text-2xl" style={{ color }}>{value.toFixed(0)}%</div>
          <div className="text-xs text-[var(--text-muted)]">{label}</div>
        </div>
      </div>
    </div>
  );
}
