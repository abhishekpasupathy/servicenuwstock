import useSWR from "swr";
import type { Bar, Quote, Signals } from "@/lib/types";

const DEFAULT_API_BASE = "/api";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE).replace(
  /\/+$/,
  "",
);

export const WS_BASE = "wss://servicenuwstock-api.onrender.com";

type RecordLike = Record<string, unknown>;

function isRecord(value: unknown): value is RecordLike {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function get(source: RecordLike, ...keys: string[]): unknown {
  for (const key of keys) {
    if (source[key] !== undefined) return source[key];
  }
  return undefined;
}

function tickerFromPath(path: string): string {
  return decodeURIComponent(path.split("?")[0].split("/").filter(Boolean).at(-1) ?? "NOW")
    .trim()
    .toUpperCase();
}

function withQuery(route: string, sourcePath: string): string {
  const query = sourcePath.includes("?") ? `?${sourcePath.split("?")[1]}` : "";
  return `${route}${query}`;
}

function encodeTicker(ticker: string): string {
  return encodeURIComponent(ticker.trim().toUpperCase());
}

function normalizeQuote(payload: unknown, fallbackTicker = "NOW"): Quote {
  const source = isRecord(payload) ? payload : {};
  const price = asNumber(get(source, "price", "currentPrice", "regularMarketPrice"));
  const prevClose = asNumber(get(source, "prev_close", "previous_close", "previousClose"), price);
  const change = asNumber(get(source, "change"), Number((price - prevClose).toFixed(2)));

  return {
    ticker: asString(get(source, "ticker", "symbol"), fallbackTicker),
    price,
    change,
    change_pct: asNumber(
      get(source, "change_pct", "changePercent"),
      prevClose ? Number(((change / prevClose) * 100).toFixed(2)) : 0,
    ),
    volume: asNumber(get(source, "volume", "regularMarketVolume")),
    avg_volume: asNumber(get(source, "avg_volume", "averageVolume", "volume")),
    market_cap: asNumber(get(source, "market_cap", "marketCap")),
    pe_ratio: asNumber(get(source, "pe_ratio", "trailingPE", "forwardPE")),
    week_52_high: asNumber(get(source, "week_52_high", "fifty_two_week_high", "fiftyTwoWeekHigh")),
    week_52_low: asNumber(get(source, "week_52_low", "fifty_two_week_low", "fiftyTwoWeekLow")),
    day_high: asNumber(get(source, "day_high", "dayHigh"), price),
    day_low: asNumber(get(source, "day_low", "dayLow"), price),
    prev_close: prevClose,
    open: asNumber(get(source, "open", "regularMarketOpen"), prevClose),
    source: asString(get(source, "source"), "unknown"),
    timestamp: asString(get(source, "timestamp", "fetched_at", "fetchedAt"), new Date().toISOString()),
    stale: Boolean(get(source, "stale", "is_degraded", "isDegraded")),
  };
}

function normalizeBars(payload: unknown): Bar[] {
  const source = isRecord(payload) ? payload : {};
  const points = Array.isArray(payload)
    ? payload
    : Array.isArray(source.points)
      ? source.points
      : Array.isArray(source.history)
        ? source.history
        : [];

  return points.flatMap((point) => {
    if (!isRecord(point)) return [];
    const date = asString(get(point, "date", "datetime"));
    const close = asNumber(get(point, "close", "adj_close", "adjClose"), NaN);
    if (!date || !Number.isFinite(close) || close <= 0) return [];
    return [
      {
        date,
        open: asNumber(point.open, close),
        high: asNumber(point.high, close),
        low: asNumber(point.low, close),
        close,
        volume: asNumber(point.volume),
      },
    ];
  });
}

function normalizeSignals(payload: unknown): Signals {
  const source = isRecord(payload) ? payload : {};
  const rawBreakdown = isRecord(source.indicator_breakdown) ? source.indicator_breakdown : {};
  const indicator_breakdown: Signals["indicator_breakdown"] = {};
  for (const [name, row] of Object.entries(rawBreakdown)) {
    if (!isRecord(row)) continue;
    indicator_breakdown[name] = {
      score: asNumber(row.score),
      weight: asNumber(row.weight),
      contribution: asNumber(row.contribution),
      signal: asString(row.signal, "neutral"),
    };
  }

  return {
    composite_score: asNumber(source.composite_score),
    buy_prob: asNumber(source.buy_prob),
    hold_prob: asNumber(source.hold_prob),
    sell_prob: asNumber(source.sell_prob),
    action: asString(source.action, "HOLD"),
    confidence: asNumber(source.confidence),
    agreement: asString(source.agreement, "0/10"),
    signal_strength: Math.max(1, Math.min(5, Math.round(asNumber(source.signal_strength, 1)))),
    indicator_breakdown,
  };
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown; message?: unknown; error?: unknown };
    const detail = payload.detail ?? payload.message ?? payload.error;
    if (typeof detail === "string" && detail.trim()) return detail;
  } catch {
    // Fall through to status text.
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function fetchJson(path: string, init?: RequestInit): Promise<unknown> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${API_BASE}${normalizedPath}`;
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  const res = await fetch(url, {
    ...init,
    cache: "no-store",
    headers,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await readErrorMessage(res)}`);
  }
  return res.json();
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const ticker = tickerFromPath(path);

  if (path.startsWith("/market/quote/") || path.startsWith("/quote/")) {
    return normalizeQuote(await fetchJson(`/quote/${encodeTicker(ticker)}`, init), ticker) as T;
  }

  if (path.startsWith("/market/ohlcv/") || path.startsWith("/history/")) {
    return normalizeBars(await fetchJson(withQuery(`/history/${encodeTicker(ticker)}`, path), init)) as T;
  }

  if (path.startsWith("/signals/")) {
    return normalizeSignals(await fetchJson(`/signals/${encodeTicker(ticker)}`, init)) as T;
  }

  if (path.startsWith("/quant/indicators/")) {
    return fetchJson(`/quant/indicators/${encodeTicker(ticker)}`, init) as Promise<T>;
  }

  if (path.startsWith("/risk/")) {
    return fetchJson(`/risk/${encodeTicker(ticker)}`, init) as Promise<T>;
  }

  if (path.startsWith("/monte-carlo/")) {
    return fetchJson(`/monte-carlo/${encodeTicker(ticker)}`, init) as Promise<T>;
  }

  if (path.startsWith("/analytics/")) {
    return fetchJson(`/analytics/${encodeTicker(ticker)}`, init) as Promise<T>;
  }

  if (path.startsWith("/prediction/")) {
    return fetchJson(`/prediction/${encodeTicker(ticker)}`, init) as Promise<T>;
  }

  if (path.startsWith("/trading-system/")) {
    return fetchJson(`/trading-system/${encodeTicker(ticker)}`, init) as Promise<T>;
  }

  if (path.startsWith("/insights/")) {
    return fetchJson(`/insights/${encodeTicker(ticker)}`, init) as Promise<T>;
  }

  return fetchJson(path, init) as Promise<T>;
}

export function useApi<T>(path: string, refreshInterval = 0) {
  return useSWR<T>(path, api, {
    refreshInterval,
    revalidateOnFocus: false,
    shouldRetryOnError: true,
    errorRetryCount: 3,
    errorRetryInterval: 2500,
  });
}

export function money(value?: number | null) {
  return `$${Number(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}

export function pct(value?: number | null) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}
