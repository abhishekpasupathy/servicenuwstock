"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";
import type { RealtimeQuote } from "@/lib/types";

function realtimeBaseUrl(path: string): string {
  const base = new URL(API_BASE);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = path;
  base.search = "";
  return base.toString();
}

function normalizeMessage(value: unknown): RealtimeQuote | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const data = value as Record<string, unknown>;
  if (data.type !== "quote") return null;
  const price = Number(data.price);
  if (!Number.isFinite(price) || price <= 0) return null;
  return {
    type: "quote",
    ticker: String(data.ticker ?? ""),
    price,
    change: Number(data.change ?? 0),
    change_pct: Number(data.change_pct ?? 0),
    volume: Number(data.volume ?? 0),
    bid: data.bid === null || data.bid === undefined ? null : Number(data.bid),
    ask: data.ask === null || data.ask === undefined ? null : Number(data.ask),
    timestamp: String(data.timestamp ?? new Date().toISOString()),
    provider: String(data.provider ?? data.source ?? "unknown"),
    source: String(data.source ?? data.provider ?? "unknown"),
    delayed: Boolean(data.delayed),
    stale: Boolean(data.stale),
    signal: typeof data.signal === "string" ? data.signal : null,
    composite_score: typeof data.composite_score === "number" ? data.composite_score : null,
  };
}

export function useRealtimeQuote(ticker: string) {
  const normalizedTicker = ticker.trim().toUpperCase();
  const [quote, setQuote] = useState<RealtimeQuote | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [transport, setTransport] = useState<"websocket" | "sse" | "offline">("offline");
  const wsRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(1000);
  const manuallyClosed = useRef(false);

  const wsUrl = useMemo(() => realtimeBaseUrl(`/ws/quote/${encodeURIComponent(normalizedTicker)}`), [normalizedTicker]);
  const sseUrl = useMemo(() => `${API_BASE.replace(/\/+$/, "")}/sse/quote/${encodeURIComponent(normalizedTicker)}`, [normalizedTicker]);

  const clearReconnect = () => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
  };

  const connectSse = useCallback(() => {
    eventSourceRef.current?.close();
    const source = new EventSource(sseUrl);
    eventSourceRef.current = source;
    source.onopen = () => {
      setConnected(true);
      setTransport("sse");
    };
    source.onmessage = (event) => {
      try {
        const parsed = normalizeMessage(JSON.parse(event.data));
        if (parsed) {
          setQuote(parsed);
          setLastUpdate(new Date());
        }
      } catch {
        // Ignore malformed heartbeat/control frames.
      }
    };
    source.onerror = () => {
      source.close();
      setConnected(false);
      setTransport("offline");
    };
  }, [sseUrl]);

  const connect = useCallback(() => {
    clearReconnect();
    manuallyClosed.current = false;
    wsRef.current?.close();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      setConnected(true);
      setTransport("websocket");
      reconnectDelay.current = 1000;
    };

    ws.onmessage = (event) => {
      try {
        const parsed = normalizeMessage(JSON.parse(event.data));
        if (parsed) {
          setQuote(parsed);
          setLastUpdate(new Date());
        }
      } catch {
        // Ignore malformed heartbeat/control frames.
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (manuallyClosed.current) return;
      reconnectTimeout.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 60000);
        connect();
      }, reconnectDelay.current);
      connectSse();
    };

    ws.onerror = () => ws.close();
  }, [connectSse, wsUrl]);

  useEffect(() => {
    connect();
    return () => {
      manuallyClosed.current = true;
      clearReconnect();
      wsRef.current?.close();
      eventSourceRef.current?.close();
    };
  }, [connect]);

  return { quote, connected, lastUpdate, transport };
}
