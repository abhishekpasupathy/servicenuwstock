"use client";

import { useEffect, useRef } from "react";
import { ColorType, createChart } from "lightweight-charts";

export function LinePanel({ data, color = "#4488ff", height = 220 }: { data: { time: string; value: number }[]; color?: string; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    const chart = createChart(ref.current, {
      layout: { background: { type: ColorType.Solid, color: "#07090b" }, textColor: "#9ba39b", fontFamily: "Menlo, Consolas, monospace" },
      grid: { vertLines: { color: "#151b20" }, horzLines: { color: "#202830" } },
      rightPriceScale: { borderColor: "#263038" },
      timeScale: { borderColor: "#263038" },
      width: ref.current.clientWidth,
      height,
    });
    chart.addLineSeries({ color, lineWidth: 2 }).setData(data);
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth ?? 0 }));
    ro.observe(ref.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [data, color, height]);
  if (!data.length) {
    return <div className="grid w-full place-items-center font-mono text-xs text-[var(--text-muted)]" style={{ height }}>NO SERIES DATA</div>;
  }
  return <div ref={ref} className="w-full" style={{ height }} />;
}
