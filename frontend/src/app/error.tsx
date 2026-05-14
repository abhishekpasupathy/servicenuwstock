"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="terminal-card border-[var(--red)] p-5">
      <div className="text-xs uppercase text-[var(--red)]">Terminal fault</div>
      <h1 className="mt-2 font-mono text-2xl">View failed to render</h1>
      <p className="mt-2 max-w-3xl text-sm text-[var(--text-muted)]">{error.message}</p>
      <button onClick={reset} className="terminal-button mt-4">Retry</button>
    </div>
  );
}
