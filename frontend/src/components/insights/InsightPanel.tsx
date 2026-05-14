export function InsightPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="terminal-card p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase text-[var(--text-muted)]">{title}</h2>
      {children}
    </section>
  );
}
