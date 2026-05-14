"use client";

import { useEffect, useRef } from "react";
import { ColorType, CrosshairMode, createChart } from "lightweight-charts";
import type { Bar } from "@/lib/types";

export function PriceChart({ bars = [], height = 420 }: { bars?: Bar[]; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current || bars.length === 0) return;
    const chart = createChart(ref.current, {
      layout: { background: { type: ColorType.Solid, color: "#0d1220" }, textColor: "#8899aa" },
      grid: { vertLines: { color: "#1a2535" }, horzLines: { color: "#1a2535" } },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: "#556677" }, horzLine: { color: "#556677" } },
      rightPriceScale: { borderColor: "#1a2535" },
      timeScale: { borderColor: "#1a2535", timeVisible: true, secondsVisible: false },
      width: ref.current.clientWidth,
      height,
    });
    const candle = chart.addCandlestickSeries({ upColor: "#00d4aa", downColor: "#ff4d6d", borderUpColor: "#00d4aa", borderDownColor: "#ff4d6d", wickUpColor: "#00d4aa", wickDownColor: "#ff4d6d" });
    candle.setData(bars.map((b) => ({ time: b.date, open: b.open, high: b.high, low: b.low, close: b.close })));
    const sma = (n: number) => bars.map((b, i) => ({ time: b.date, value: bars.slice(Math.max(0, i - n + 1), i + 1).reduce((s, x) => s + x.close, 0) / Math.min(i + 1, n) }));
    chart.addLineSeries({ color: "#f0c040", lineWidth: 1 }).setData(sma(50));
    chart.addLineSeries({ color: "#a855f7", lineWidth: 1 }).setData(sma(200));
    const vol = chart.addHistogramSeries({ color: "#4488ff", priceFormat: { type: "volume" }, priceScaleId: "volume" });
    vol.setData(bars.map((b) => ({ time: b.date, value: b.volume, color: b.close >= b.open ? "#00d4aa55" : "#ff4d6d55" })));
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth ?? 0 }));
    ro.observe(ref.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [bars, height]);
  return <div ref={ref} className="w-full" style={{ height }} />;
}
