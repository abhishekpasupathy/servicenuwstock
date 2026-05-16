"use client";

import { useState } from "react";
import { money, pct, useApi } from "@/lib/api";
import type { Prediction } from "@/lib/types";
import { useRealtimeQuote } from "@/hooks/useRealtimeQuote";

function BiasGauge({ bias, label }: { bias: number; label: string }) {
  const angle = bias * 90;
  const color =
    bias >= 0.5
      ? "var(--green)"
      : bias >= 0.2
        ? "#4ade80"
        : bias >= -0.2
          ? "var(--amber)"
          : bias >= -0.5
            ? "#f87171"
            : "var(--red)";
  return (
    <div className="terminal-card p-4">
      <div className="text-xs text-[var(--text-muted)]">Direction Bias</div>
      <div className="relative mx-auto mt-3 h-24 w-48 overflow-hidden">
        <div className="absolute bottom-0 left-1/2 h-24 w-48 -translate-x-1/2 rounded-t-full border border-[var(--border)]" />
        <div
          className="absolute bottom-0 left-1/2 h-1 w-20 origin-bottom -translate-x-1/2"
          style={{ transform: `translateX(-50%) rotate(${angle}deg)`, backgroundColor: color }}
        />
        <div className="absolute bottom-0 left-1/2 h-2 w-2 -translate-x-1/2 rounded-full bg-[var(--text-primary)]" />
      </div>
      <div className="mt-2 text-center font-mono text-sm font-bold" style={{ color }}>
        {label}
      </div>
      <div className="text-center font-mono text-xs text-[var(--text-dim)]">{(bias * 100).toFixed(1)}%</div>
    </div>
  );
}

function RangeCard({
  label,
  low,
  high,
  mid,
  current,
  extra,
}: {
  label: string;
  low: number;
  high: number;
  mid?: number;
  current: number;
  extra?: React.ReactNode;
}) {
  const rangePct = ((high - low) / current) * 100;
  const currentPos = ((current - low) / (high - low)) * 100;
  return (
    <div className="terminal-card p-4">
      <div className="text-xs uppercase text-[var(--text-muted)]">{label}</div>
      <div className="mt-3 flex items-center justify-between font-mono">
        <span className="text-lg text-[var(--red)]">{money(low)}</span>
        {mid !== undefined && <span className="text-sm text-[var(--text-dim)]">{money(mid)}</span>}
        <span className="text-lg text-[var(--green)]">{money(high)}</span>
      </div>
      <div className="relative mt-2 h-2 rounded-full bg-[var(--border)]">
        <div
          className="absolute top-0 h-2 rounded-full bg-gradient-to-r from-[var(--red)] via-[var(--amber)] to-[var(--green)]"
          style={{ width: "100%" }}
        />
        <div
          className="absolute top-0 h-2 w-1 rounded-full bg-white"
          style={{ left: `${Math.max(0, Math.min(100, currentPos))}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-[var(--text-dim)]">
        <span>Range {rangePct.toFixed(1)}%</span>
        <span>Current {money(current)}</span>
      </div>
      {extra}
    </div>
  );
}

function AlgorithmTable({ algorithms }: { algorithms: Record<string, { weight: number; value: string | number; description: string }> }) {
  return (
    <div className="terminal-card p-4">
      <div className="mb-3 text-xs uppercase text-[var(--text-muted)]">Algorithm Breakdown</div>
      <div className="space-y-2">
        {Object.entries(algorithms).map(([name, algo]) => (
          <div key={name} className="flex items-center gap-3 font-mono text-xs">
            <span className="w-32 text-[var(--amber)]">{name.replace(/_/g, " ")}</span>
            <div className="flex-1">
              <div className="h-1.5 rounded-full bg-[var(--border)]">
                <div className="h-1.5 rounded-full bg-[var(--amber)]" style={{ width: `${algo.weight * 100}%` }} />
              </div>
            </div>
            <span className="w-20 text-right text-[var(--text-primary)]">{typeof algo.value === "number" ? algo.value.toFixed(2) : algo.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PredictionPage() {
  const [ticker, setTicker] = useState("NOW");
  const [inputTicker, setInputTicker] = useState("NOW");
  const { data: pred, isLoading } = useApi<Prediction>(`/prediction/${ticker}`);
  const { quote: liveQuote } = useRealtimeQuote(ticker);

  const handlePredict = () => {
    const t = inputTicker.trim().toUpperCase();
    if (t) setTicker(t);
  };

  return (
    <div className="space-y-4">
      {/* Ticker Input */}
      <div className="terminal-card flex items-center gap-3 p-4">
        <span className="font-mono text-xs text-[var(--amber)]">SONSPREDICTION</span>
        <input
          type="text"
          value={inputTicker}
          onChange={(e) => setInputTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handlePredict()}
          placeholder="Enter ticker..."
          className="terminal-input w-32 font-mono text-sm"
        />
        <button onClick={handlePredict} className="terminal-button px-4 py-2 font-mono text-xs">
          PREDICT
        </button>
        {liveQuote?.price && (
          <span className="ml-auto font-mono text-sm text-[var(--text-dim)]">
            Live: {money(liveQuote.price)}
          </span>
        )}
      </div>

      {isLoading && !pred && (
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="terminal-card h-32 animate-pulse p-4" />
          ))}
        </div>
      )}

      {pred && (
        <>
          {/* Summary Bar */}
          <div className="terminal-card flex items-center justify-between p-4">
            <div>
              <span className="font-mono text-lg font-black">{pred.ticker}</span>
              <span className="ml-3 font-mono text-sm text-[var(--text-dim)]">{money(pred.current_price)}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="font-mono text-xs text-[var(--text-muted)]">Regime: {pred.regime.replace(/_/g, " ")}</span>
              <span className="font-mono text-xs">Score: {pred.composite_score}</span>
              <span
                className="font-mono text-sm font-bold"
                style={{
                  color:
                    pred.action.includes("BUY")
                      ? "var(--green)"
                      : pred.action.includes("SELL") || pred.action.includes("REDUCE")
                        ? "var(--red)"
                        : "var(--amber)",
                }}
              >
                {pred.action}
              </span>
            </div>
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-3 gap-4">
            <RangeCard
              label="Day Range Prediction"
              low={pred.day_prediction.predicted_low}
              high={pred.day_prediction.predicted_high}
              mid={pred.day_prediction.predicted_mid}
              current={pred.current_price}
              extra={
                <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[10px] text-[var(--text-dim)]">
                  <span>ATR {money(pred.day_prediction.atr_value)}</span>
                  <span>ATR% {pred.day_prediction.atr_pct.toFixed(2)}%</span>
                </div>
              }
            />
            <RangeCard
              label="Year Range Prediction (95% CI)"
              low={pred.year_prediction.ci_95_low}
              high={pred.year_prediction.ci_95_high}
              mid={pred.year_prediction.median_target}
              current={pred.current_price}
              extra={
                <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-[10px] text-[var(--text-dim)]">
                  <span>Expected {pct(pred.year_prediction.expected_return_pct)}</span>
                  <span>Target {money(pred.year_prediction.base_target)}</span>
                </div>
              }
            />
            <BiasGauge bias={pred.direction_bias} label={pred.direction_label} />
          </div>

          {/* Probability Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="terminal-card p-4 text-center">
              <div className="text-xs text-[var(--text-muted)]">Above Current</div>
              <div className="mt-1 font-mono text-2xl text-[var(--green)]">{pred.year_prediction.prob_above_current}%</div>
            </div>
            <div className="terminal-card p-4 text-center">
              <div className="text-xs text-[var(--text-muted)]">+10% Gain</div>
              <div className="mt-1 font-mono text-2xl text-[var(--green)]">{pred.year_prediction.prob_10pct_gain}%</div>
            </div>
            <div className="terminal-card p-4 text-center">
              <div className="text-xs text-[var(--text-muted)]">+20% Gain</div>
              <div className="mt-1 font-mono text-2xl text-[var(--green)]">{pred.year_prediction.prob_20pct_gain}%</div>
            </div>
            <div className="terminal-card p-4 text-center">
              <div className="text-xs text-[var(--text-muted)]">-10% Loss</div>
              <div className="mt-1 font-mono text-2xl text-[var(--red)]">{pred.year_prediction.prob_10pct_loss}%</div>
            </div>
          </div>

          {/* Support/Resistance + Algorithms */}
          <div className="grid grid-cols-2 gap-4">
            <div className="terminal-card p-4">
              <div className="mb-3 text-xs uppercase text-[var(--text-muted)]">Support & Resistance</div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[10px] text-[var(--text-dim)]">Support Levels</div>
                  {pred.support_levels.map((s, i) => (
                    <div key={i} className="font-mono text-sm text-[var(--green)]">{money(s)}</div>
                  ))}
                </div>
                <div>
                  <div className="text-[10px] text-[var(--text-dim)]">Resistance Levels</div>
                  {pred.resistance_levels.map((r, i) => (
                    <div key={i} className="font-mono text-sm text-[var(--red)]">{money(r)}</div>
                  ))}
                </div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-[10px] text-[var(--text-dim)]">
                <span>Confidence {pred.confidence.toFixed(1)}%</span>
                <span>Source {pred.source}</span>
              </div>
            </div>
            <AlgorithmTable algorithms={pred.algorithms} />
          </div>
        </>
      )}
    </div>
  );
}
