export function DecisionCard({ action, confidence }: { action?: string; confidence?: number }) {
  return <div className="terminal-card p-4"><div className="text-2xl text-[var(--green)]">{action ?? "HOLD"}</div><div className="text-sm text-[var(--text-muted)]">Confidence {confidence ?? 0}%</div></div>;
}
