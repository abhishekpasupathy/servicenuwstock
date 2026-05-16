"use client";

import { useState } from "react";
import { money, useApi } from "@/lib/api";
import type { TradingSystem } from "@/lib/types";
import { useRealtimeQuote } from "@/hooks/useRealtimeQuote";

function Section({ title, number, children }: { title: string; number: number; children: React.ReactNode }) {
  return (
    <section className="terminal-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded bg-[var(--amber)] font-mono text-[10px] font-bold text-black">{number}</span>
        <h2 className="font-mono text-xs font-bold uppercase text-[var(--amber)]">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function StatusBadge({ value, pass }: { value: string | number | boolean; pass: boolean }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 font-mono text-[10px] ${pass ? "bg-[var(--green)]/20 text-[var(--green)]" : "bg-[var(--red)]/20 text-[var(--red)]"}`}>
      {String(value)}
    </span>
  );
}

function MetricRow({ label, value, status }: { label: string; value: string | number; status?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-[var(--border)] py-1.5 last:border-0">
      <span className="font-mono text-xs text-[var(--text-dim)]">{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-[var(--text-primary)]">{value}</span>
        {status && (
          <span className={`font-mono text-[10px] ${status === "PASS" ? "text-[var(--green)]" : status === "WARNING" ? "text-[var(--amber)]" : "text-[var(--red)]"}`}>
            {status}
          </span>
        )}
      </div>
    </div>
  );
}

function RuleBlock({ rules }: { rules: Record<string, string> }) {
  return (
    <div className="mt-3 space-y-1 rounded border border-[var(--border)] bg-[var(--bg-primary)] p-3">
      <div className="mb-1 font-mono text-[10px] uppercase text-[var(--text-dim)]">Execution Rules</div>
      {Object.entries(rules).map(([key, rule]) => (
        <div key={key} className="font-mono text-[11px] text-[var(--text-primary)]">
          <span className="text-[var(--amber)]">{key}:</span> {rule}
        </div>
      ))}
    </div>
  );
}

export default function TradingSystemPage() {
  const [ticker, setTicker] = useState("NOW");
  const [inputTicker, setInputTicker] = useState("NOW");
  const { data: sys, isLoading } = useApi<TradingSystem>(`/trading-system/${ticker}`);
  const { quote: liveQuote } = useRealtimeQuote(ticker);

  const handleRun = () => {
    const t = inputTicker.trim().toUpperCase();
    if (t) setTicker(t);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="terminal-card flex items-center gap-3 p-4">
        <span className="font-mono text-xs font-bold text-[var(--amber)]">INSTITUTIONAL TRADING SYSTEM</span>
        <input
          type="text"
          value={inputTicker}
          onChange={(e) => setInputTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleRun()}
          placeholder="Ticker..."
          className="terminal-input w-32 font-mono text-sm"
        />
        <button onClick={handleRun} className="terminal-button px-4 py-2 font-mono text-xs">
          EXECUTE
        </button>
        {liveQuote?.price && (
          <span className="ml-auto font-mono text-sm text-[var(--text-dim)]">
            Live: {money(liveQuote.price)}
          </span>
        )}
      </div>

      {isLoading && !sys && (
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="terminal-card h-48 animate-pulse p-4" />
          ))}
        </div>
      )}

      {sys && (
        <>
          {/* Module 1: Signal Stack */}
          <Section title="Signal Stack — Multi-Factor Composite" number={1}>
            <div className="mb-3 flex items-center gap-4">
              <div className="text-center">
                <div className="font-mono text-3xl font-black" style={{ color: sys.module_1_signal_stack.composite_score >= 50 ? "var(--green)" : sys.module_1_signal_stack.composite_score >= 0 ? "var(--amber)" : "var(--red)" }}>
                  {sys.module_1_signal_stack.composite_score}
                </div>
                <div className="font-mono text-[10px] text-[var(--text-dim)]">COMPOSITE</div>
              </div>
              <div className="flex-1">
                <div className="h-2 rounded-full bg-[var(--border)]">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${Math.max(0, Math.min(100, (sys.module_1_signal_stack.composite_score + 100) / 2))}%`,
                      backgroundColor: sys.module_1_signal_stack.composite_score >= 50 ? "var(--green)" : sys.module_1_signal_stack.composite_score >= -25 ? "var(--amber)" : "var(--red)",
                    }}
                  />
                </div>
                <div className="mt-1 flex justify-between font-mono text-[9px] text-[var(--text-dim)]">
                  <span>-100</span>
                  <span>0</span>
                  <span>+100</span>
                </div>
              </div>
              <div className="rounded border px-3 py-1 font-mono text-sm font-bold" style={{ borderColor: "var(--amber)", color: "var(--amber)" }}>
                {sys.module_1_signal_stack.action}
              </div>
            </div>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(sys.module_1_signal_stack.signals).map(([name, sig]) => (
                <div key={name} className="rounded border border-[var(--border)] p-2 text-center">
                  <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">{name.replace(/_/g, " ")}</div>
                  <div className="mt-1 font-mono text-lg" style={{ color: (sig as Record<string, number>).value >= 0 ? "var(--green)" : "var(--red)" }}>{(sig as Record<string, number>).value}</div>
                  <div className="font-mono text-[9px] text-[var(--text-dim)]">w={(sig as Record<string, number>).weight} &middot; c={(sig as Record<string, number>).contribution}</div>
                </div>
              ))}
            </div>
            <RuleBlock rules={Object.fromEntries(Object.entries(sys.module_1_signal_stack.thresholds).map(([k, v]) => [k, `>= ${v}`]))} />
          </Section>

          {/* Module 2: Entry Engine */}
          <Section title="Entry Engine — Tranche DCA System" number={2}>
            <div className="grid grid-cols-4 gap-3">
              <MetricRow label="Deployable" value={`$${sys.module_2_entry_engine.deployable_capital.toLocaleString()}`} />
              <MetricRow label="Deployed" value={`$${sys.module_2_entry_engine.deployed_capital.toLocaleString()}`} />
              <MetricRow label="Dry Powder" value={`$${sys.module_2_entry_engine.dry_powder_reserve.toLocaleString()}`} />
              <MetricRow label="Z-Multiplier" value={`${sys.module_2_entry_engine.z_multiplier}x`} />
            </div>
            <div className="mt-3 grid grid-cols-4 gap-2">
              {sys.module_2_entry_engine.tranche_schedule.map((t: Record<string, unknown>) => (
                <div key={String(t.level)} className={`rounded border p-2 text-center ${sys.current_price <= Number(t.price) ? "border-[var(--green)] bg-[var(--green)]/10" : "border-[var(--border)]"}`}>
                  <div className="font-mono text-[10px] text-[var(--text-dim)]">Tranche {String(t.level)}</div>
                  <div className="font-mono text-sm">{money(Number(t.price))}</div>
                  <div className="font-mono text-[10px] text-[var(--amber)]">{String(t.multiplier)}x</div>
                </div>
              ))}
            </div>
            <div className="mt-2 flex items-center gap-2">
              <StatusBadge value={sys.module_2_entry_engine.can_deploy ? "CAN DEPLOY" : "WAIT"} pass={sys.module_2_entry_engine.can_deploy} />
              <span className="font-mono text-[10px] text-[var(--text-dim)]">
                Days until next entry: {sys.module_2_entry_engine.days_until_next_entry}
              </span>
            </div>
            <RuleBlock rules={sys.module_2_entry_engine.rules} />
          </Section>

          {/* Module 3: Trend Confirmation */}
          <Section title="Trend Confirmation Checklist" number={3}>
            <div className="mb-2 flex items-center gap-3">
              <div className="font-mono text-2xl font-black" style={{ color: sys.module_3_trend_confirmation.trend_confirmed ? "var(--green)" : "var(--red)" }}>
                {sys.module_3_trend_confirmation.passed}/{sys.module_3_trend_confirmation.total}
              </div>
              <StatusBadge value={sys.module_3_trend_confirmation.trend_confirmed ? "CONFIRMED" : "NOT CONFIRMED"} pass={sys.module_3_trend_confirmation.trend_confirmed} />
              <span className="font-mono text-[10px] text-[var(--text-dim)]">{sys.module_3_trend_confirmation.threshold}</span>
            </div>
            <div className="space-y-1">
              {Object.entries(sys.module_3_trend_confirmation.checklist).map(([key, c]) => {
                const check = c as Record<string, unknown>;
                return (
                <div key={key} className="flex items-center gap-2 rounded border border-[var(--border)] p-2">
                  <span className={`font-mono text-sm ${check.passed ? "text-[var(--green)]" : "text-[var(--red)]"}`}>{check.passed ? "PASS" : "FAIL"}</span>
                  <span className="flex-1 font-mono text-[11px] text-[var(--text-dim)]">{String(check.condition)}</span>
                  <span className="font-mono text-[10px] text-[var(--text-primary)]">{String(check.actual)}</span>
                </div>
                );
              })}
            </div>
            <RuleBlock rules={{ R1: sys.module_3_trend_confirmation.rule }} />
          </Section>

          {/* Module 4: Fundamentals Kill Switch */}
          <Section title="Fundamentals Kill Switch" number={4}>
            <div className="mb-2 flex items-center gap-3">
              <StatusBadge value={sys.module_4_fundamentals_kill_switch.response} pass={sys.module_4_fundamentals_kill_switch.response === "NO_ACTION"} />
              <span className="font-mono text-[10px] text-[var(--text-dim)]">
                {sys.module_4_fundamentals_kill_switch.breaches} breaches, {sys.module_4_fundamentals_kill_switch.warnings} warnings
              </span>
            </div>
            <div className="space-y-1">
              {Object.entries(sys.module_4_fundamentals_kill_switch.metrics).map(([key, m]) => {
                const metric = m as Record<string, unknown>;
                return (
                <div key={key} className="flex items-center gap-2 rounded border border-[var(--border)] p-2">
                  <span className="w-32 font-mono text-[11px] text-[var(--amber)]">{key.replace(/_/g, " ")}</span>
                  <span className="flex-1 font-mono text-xs">{String(metric.value)}{String(metric.unit)}</span>
                  <span className="font-mono text-[10px] text-[var(--text-dim)]">floor: {String(metric.floor)}{String(metric.unit)}</span>
                  <StatusBadge value={String(metric.status)} pass={metric.status === "PASS"} />
                </div>
                );
              })}
            </div>
            <RuleBlock rules={sys.module_4_fundamentals_kill_switch.rules} />
          </Section>

          {/* Module 5: Position Sizing */}
          <Section title="Position Sizing — Kelly Criterion" number={5}>
            <div className="mb-3 rounded border border-[var(--border)] bg-[var(--bg-primary)] p-3 font-mono text-xs">
              <span className="text-[var(--amber)]">Formula:</span> {sys.module_5_position_sizing.kelly_formula}
              <br />
              <span className="text-[var(--amber)]">Variables:</span> b={sys.module_5_position_sizing.variables.b_win_loss_ratio}, p={sys.module_5_position_sizing.variables.p_win_probability}, q={sys.module_5_position_sizing.variables.q_loss_probability}
            </div>
            <div className="grid grid-cols-4 gap-3">
              <MetricRow label="Full Kelly" value={`${sys.module_5_position_sizing.full_kelly_pct}%`} />
              <MetricRow label="Fractional (0.25x)" value={`${sys.module_5_position_sizing.fractional_kelly_pct}%`} />
              <MetricRow label="Effective %" value={`${sys.module_5_position_sizing.effective_pct}%`} />
              <MetricRow label="Shares" value={sys.module_5_position_sizing.shares.toLocaleString()} />
            </div>
            <div className="mt-2 grid grid-cols-3 gap-3">
              <MetricRow label="Position Size" value={`$${sys.module_5_position_sizing.position_size_usd.toLocaleString()}`} />
              <MetricRow label="Single Stock Cap" value={sys.module_5_position_sizing.caps.single_stock_max} />
              <MetricRow label="Binding" value={sys.module_5_position_sizing.binding_constraint} />
            </div>
            <RuleBlock rules={sys.module_5_position_sizing.rules} />
          </Section>

          {/* Module 6: Risk Architecture */}
          <Section title="Risk Architecture" number={6}>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded border border-[var(--red)] p-3">
                <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">Initial Hard Stop</div>
                <div className="font-mono text-xl text-[var(--red)]">{money(sys.module_6_risk_architecture.initial_hard_stop.price)}</div>
                <div className="font-mono text-[10px] text-[var(--text-dim)]">{sys.module_6_risk_architecture.initial_hard_stop.pct_below_entry}% below entry</div>
              </div>
              <div className="rounded border border-[var(--amber)] p-3">
                <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">Trailing Stop Activation</div>
                <div className="font-mono text-xl text-[var(--amber)]">{money(sys.module_6_risk_architecture.trailing_stop.activation_price)}</div>
                <div className="font-mono text-[10px] text-[var(--text-dim)]">+{sys.module_6_risk_architecture.trailing_stop.activation_pct}% from entry</div>
              </div>
              <div className="rounded border border-[var(--amber)] p-3">
                <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">Volatility Stop</div>
                <div className="font-mono text-xl text-[var(--amber)]">{money(sys.module_6_risk_architecture.volatility_stop.price)}</div>
                <div className="font-mono text-[10px] text-[var(--text-dim)]">{sys.module_6_risk_architecture.volatility_stop.pct_below_current}% below current</div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-4">
              <div className="rounded border border-[var(--border)] p-3">
                <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">Correlation Hedge</div>
                <div className="font-mono text-sm text-[var(--amber)]">{sys.module_6_risk_architecture.correlation_hedge.primary.ticker} @ {sys.module_6_risk_architecture.correlation_hedge.primary.hedge_ratio * 100}%</div>
                <div className="font-mono text-[10px] text-[var(--text-dim)]">Correlation: {sys.module_6_risk_architecture.correlation_hedge.primary.correlation}</div>
              </div>
              <div className="rounded border border-[var(--border)] p-3">
                <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">Tail Protection</div>
                <div className="font-mono text-sm text-[var(--amber)]">{sys.module_6_risk_architecture.tail_protection.structure}</div>
                <div className="font-mono text-[10px] text-[var(--text-dim)]">Cost: {sys.module_6_risk_architecture.tail_protection.estimated_cost_pct}%/yr</div>
              </div>
            </div>
            <RuleBlock rules={sys.module_6_risk_architecture.rules} />
          </Section>

          {/* Module 7: Exit Playbook */}
          <Section title="Exit Playbook — DCF Scenarios" number={7}>
            <div className="grid grid-cols-3 gap-4">
              {Object.entries(sys.module_7_exit_playbook.dcf_scenarios).map(([name, s]) => {
                const scenario = s as Record<string, unknown>;
                return (
                <div key={name} className={`rounded border p-3 ${name === "bull" ? "border-[var(--green)]" : name === "bear" ? "border-[var(--red)]" : "border-[var(--amber)]"}`}>
                  <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">{name} case</div>
                  <div className={`font-mono text-2xl font-black ${name === "bull" ? "text-[var(--green)]" : name === "bear" ? "text-[var(--red)]" : "text-[var(--amber)]"}`}>
                    {money(Number(scenario.price_target))}
                  </div>
                  <div className="font-mono text-xs text-[var(--text-dim)]">{String(scenario.upside_pct)}% upside</div>
                  <div className="mt-2 space-y-0.5 font-mono text-[9px] text-[var(--text-dim)]">
                    {Object.entries(scenario.assumptions as Record<string, string>).map(([k, v]) => (
                      <div key={k}>{k.replace(/_/g, " ")}: {v}</div>
                    ))}
                  </div>
                </div>
                );
              })}
            </div>
            <div className="mt-3 font-mono text-[10px] uppercase text-[var(--text-dim)]">Momentum Exit Triggers</div>
            <div className="mt-1 space-y-1">
              {Object.entries(sys.module_7_exit_playbook.momentum_exit_triggers).map(([key, t]) => {
                const trigger = t as Record<string, unknown>;
                return (
                <div key={key} className="flex items-center gap-2 rounded border border-[var(--border)] p-2">
                  <StatusBadge value={trigger.currently_triggered ? "TRIGGERED" : "OK"} pass={!trigger.currently_triggered} />
                  <span className="flex-1 font-mono text-[11px] text-[var(--text-dim)]">{String(trigger.condition)}</span>
                  <span className="font-mono text-[10px] text-[var(--amber)]">{String(trigger.action)}</span>
                </div>
                );
              })}
            </div>
            <RuleBlock rules={sys.module_7_exit_playbook.rules} />
          </Section>

          {/* Module 8: Backtesting */}
          <Section title="Backtesting Framework" number={8}>
            <div className="grid grid-cols-5 gap-3">
              {Object.entries(sys.module_8_backtesting.optimization_targets).map(([key, t]) => {
                const target = t as Record<string, unknown>;
                return (
                <div key={key} className="rounded border border-[var(--border)] p-2 text-center">
                  <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">{key.replace(/_/g, " ")}</div>
                  <div className="font-mono text-sm text-[var(--green)]">{String(target.target)}</div>
                  <div className="font-mono text-[9px] text-[var(--text-dim)]">min: {String(target.minimum)}</div>
                </div>
                );
              })}
            </div>
            <div className="mt-3 font-mono text-[10px] uppercase text-[var(--text-dim)]">Stress Scenarios</div>
            <div className="mt-1 space-y-1">
              {sys.module_8_backtesting.stress_scenarios.map((s: Record<string, string>) => (
                <div key={s.name} className="flex items-center gap-2 rounded border border-[var(--border)] p-2">
                  <span className="w-36 font-mono text-[11px] text-[var(--amber)]">{s.name}</span>
                  <span className="flex-1 font-mono text-[10px] text-[var(--text-dim)]">{s.description}</span>
                  <span className="font-mono text-[10px] text-[var(--red)]">{s.expected_drawdown}</span>
                </div>
              ))}
            </div>
            <RuleBlock rules={sys.module_8_backtesting.rules} />
          </Section>

          {/* Module 9: Portfolio Context */}
          <Section title="Portfolio Context Rules" number={9}>
            <div className="grid grid-cols-3 gap-4">
              <MetricRow label="Correlation" value={sys.module_9_portfolio_context.current_correlation} />
              <MetricRow label="Tech Sector %" value={`${sys.module_9_portfolio_context.sector_concentration.current_tech_pct}%`} />
              <MetricRow label="Action" value={sys.module_9_portfolio_context.correlation_action} />
            </div>
            <div className="mt-3 space-y-1">
              {Object.entries(sys.module_9_portfolio_context.macro_conditions).map(([key, c]) => {
                const cond = c as Record<string, unknown>;
                return (
                <div key={key} className="rounded border border-[var(--border)] p-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] text-[var(--amber)]">{key.replace(/_/g, " ")}</span>
                    <span className="font-mono text-[10px] text-[var(--text-primary)]">{String(cond.current)}</span>
                  </div>
                  <div className="font-mono text-[10px] text-[var(--text-dim)]">Re-evaluate: {String(cond.re_evaluate_if)}</div>
                </div>
                );
              })}
            </div>
            <RuleBlock rules={sys.module_9_portfolio_context.rules} />
          </Section>

          {/* Module 10: Execution Protocol */}
          <Section title="Execution Protocol" number={10}>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">Order Types</div>
                {Object.entries(sys.module_10_execution_protocol.order_types).map(([key, o]) => {
                  const order = o as Record<string, string>;
                  return (
                  <div key={key} className="rounded border border-[var(--border)] p-2">
                    <div className="font-mono text-[11px] text-[var(--amber)]">{key}: {order.type}</div>
                    <div className="font-mono text-[10px] text-[var(--text-dim)]">{order.rule}</div>
                  </div>
                  );
                })}
              </div>
              <div className="space-y-2">
                <div className="font-mono text-[10px] uppercase text-[var(--text-dim)]">Optimal Timing</div>
                <div className="rounded border border-[var(--border)] p-2">
                  <MetricRow label="Best Days" value={sys.module_10_execution_protocol.optimal_timing.best_days.join(", ")} />
                  <MetricRow label="Worst Days" value={sys.module_10_execution_protocol.optimal_timing.worst_days.join(", ")} />
                  <MetricRow label="Best Entry" value={sys.module_10_execution_protocol.intraday_patterns.best_entry_window} />
                  <MetricRow label="Avoid" value={sys.module_10_execution_protocol.intraday_patterns.avoid_window} />
                </div>
              </div>
            </div>
            <RuleBlock rules={sys.module_10_execution_protocol.rules} />
          </Section>
        </>
      )}
    </div>
  );
}
