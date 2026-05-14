export function SignalGauge({ score }: { score: number }) {
  const color = score > 30 ? "var(--green)" : score < -30 ? "var(--red)" : "var(--amber)";
  const deg = ((score + 100) / 200) * 180;
  return (
    <div className="terminal-card p-4">
      <div className="text-xs uppercase text-[var(--text-muted)]">Composite Signal</div>
      <div className="relative mx-auto mt-5 h-32 w-56 overflow-hidden">
        <div className="absolute inset-x-0 bottom-0 h-28 rounded-t-full border-[18px] border-b-0 border-[var(--border)]" />
        <div className="absolute bottom-0 left-1/2 h-1 w-24 origin-left rounded bg-[var(--text-primary)]" style={{ transform: `rotate(${deg + 180}deg)`, background: color }} />
        <div className="absolute bottom-0 left-1/2 h-3 w-3 -translate-x-1/2 rounded-full bg-[var(--text-primary)]" />
      </div>
      <div className="text-center font-mono text-4xl" style={{ color }}>{score.toFixed(0)}</div>
    </div>
  );
}
