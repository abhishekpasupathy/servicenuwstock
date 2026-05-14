"use client";

import { useEffect, useRef } from "react";
import { ColorType, createChart } from "lightweight-charts";

export function LinePanel({ data, color = "#4488ff", height = 220 }: { data: { time: string; value: number }[]; color?: string; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || data.length === 0) return;
    const chart = createChart(ref.current, { layout: { background: { type: ColorType.Solid, color: "#0d1220" }, textColor: "#8899aa" }, grid: { vertLines: { color: "#1a2535" }, horzLines: { color: "#1a2535" } }, width: ref.current.clientWidth, height });
    chart.addLineSeries({ color, lineWidth: 2 }).setData(data);
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth ?? 0 }));
    ro.observe(ref.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [data, color, height]);
  return <div ref={ref} className="w-full" style={{ height }} />;
}
