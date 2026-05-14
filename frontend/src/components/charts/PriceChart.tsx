"use client";

import { useEffect, useRef } from "react";
import { ColorType, CrosshairMode, createChart, type CandlestickData, type ISeriesApi, type Time } from "lightweight-charts";
import type { Bar } from "@/lib/types";

export function PriceChart({ bars = [], height = 420, realtimePrice }: { bars?: Bar[]; height?: number; realtimePrice?: number | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lastBarRef = useRef<CandlestickData<Time> | null>(null);

  useEffect(() => {
    if (!ref.current || bars.length === 0) return;
    const chart = createChart(ref.current, {
      layout: { background: { type: ColorType.Solid, color: "#07090b" }, textColor: "#9ba39b", fontFamily: "Menlo, Consolas, monospace" },
      grid: { vertLines: { color: "#151b20" }, horzLines: { color: "#202830" } },
      crosshair: { mode: CrosshairMode.Normal, vertLine: { color: "#ffb000", labelBackgroundColor: "#111" }, horzLine: { color: "#ffb000", labelBackgroundColor: "#111" } },
      rightPriceScale: { borderColor: "#263038" },
      timeScale: { borderColor: "#263038", timeVisible: true, secondsVisible: false },
      width: ref.current.clientWidth,
      height,
    });
    const candle = chart.addCandlestickSeries({ upColor: "#26d07c", downColor: "#ff4f45", borderUpColor: "#26d07c", borderDownColor: "#ff4f45", wickUpColor: "#26d07c", wickDownColor: "#ff4f45" });
    const candleData = bars.map((b) => ({ time: b.date as Time, open: b.open, high: b.high, low: b.low, close: b.close }));
    candle.setData(candleData);
    candleSeriesRef.current = candle;
    lastBarRef.current = candleData.at(-1) ?? null;
    const sma = (n: number) => bars.map((b, i) => ({ time: b.date, value: bars.slice(Math.max(0, i - n + 1), i + 1).reduce((s, x) => s + x.close, 0) / Math.min(i + 1, n) }));
    chart.addLineSeries({ color: "#ffb000", lineWidth: 1, priceLineVisible: false }).setData(sma(50));
    chart.addLineSeries({ color: "#46a6ff", lineWidth: 1, priceLineVisible: false }).setData(sma(200));
    const vol = chart.addHistogramSeries({ color: "#46a6ff", priceFormat: { type: "volume" }, priceScaleId: "volume" });
    vol.setData(bars.map((b) => ({ time: b.date, value: b.volume, color: b.close >= b.open ? "#26d07c55" : "#ff4f4555" })));
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth ?? 0 }));
    ro.observe(ref.current);
    return () => { ro.disconnect(); candleSeriesRef.current = null; lastBarRef.current = null; chart.remove(); };
  }, [bars, height]);

  useEffect(() => {
    if (!candleSeriesRef.current || !lastBarRef.current || !realtimePrice || realtimePrice <= 0) return;
    const lastBar = lastBarRef.current;
    const updatedBar = {
      ...lastBar,
      high: Math.max(lastBar.high, realtimePrice),
      low: Math.min(lastBar.low, realtimePrice),
      close: realtimePrice,
    };
    candleSeriesRef.current.update(updatedBar);
    lastBarRef.current = updatedBar;
  }, [realtimePrice]);

  if (!bars.length) {
    return <div className="grid w-full place-items-center font-mono text-xs text-[var(--text-muted)]" style={{ height }}>NO PRICE DATA</div>;
  }
  return <div ref={ref} className="w-full" style={{ height }} />;
}
