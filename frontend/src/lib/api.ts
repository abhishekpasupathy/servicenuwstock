import useSWR from "swr";
import type { Bar, Quote, Signals } from "@/lib/types";

const DEFAULT_API_BASE = "https://servicenuwstock-api.onrender.com/api/v1";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE).replace(
  /\/+$/,
  "",
);

type Snapshot = {
  quote?: Record<string, unknown>;
  history?: { points?: Record<string, unknown>[] };
  profile?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
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

function encodeTicker(ticker: string): string {
  return encodeURIComponent(ticker.trim().toUpperCase());
}

function tickerFromPath(path: string): string {
  return decodeURIComponent(path.split("?")[0].split("/").filter(Boolean).at(-1) ?? "NOW");
}

function withQuery(route: string, sourcePath: string): string {
  const query = sourcePath.includes("?") ? `?${sourcePath.split("?")[1]}` : "";
  return `${route}${query}`;
}

function normalizeQuote(payload: unknown, fallbackTicker = "NOW"): Quote {
  const source = isRecord(payload) ? payload : {};
  const price = asNumber(source.price);
  const prevClose = asNumber(source.prev_close ?? source.previous_close, price);

  return {
    ticker: asString(source.ticker, fallbackTicker),
    price,
    change: asNumber(source.change, Number((price - prevClose).toFixed(2))),
    change_pct: asNumber(
      source.change_pct,
      prevClose ? Number((((price - prevClose) / prevClose) * 100).toFixed(2)) : 0,
    ),
    volume: asNumber(source.volume),
    avg_volume: asNumber(source.avg_volume ?? source.volume),
    market_cap: asNumber(source.market_cap),
    pe_ratio: asNumber(source.pe_ratio),
    week_52_high: asNumber(source.week_52_high ?? source.fifty_two_week_high),
    week_52_low: asNumber(source.week_52_low ?? source.fifty_two_week_low),
    day_high: asNumber(source.day_high),
    day_low: asNumber(source.day_low),
    prev_close: prevClose,
    open: asNumber(source.open, prevClose),
    source: asString(source.source, "unknown"),
    timestamp: asString(source.timestamp ?? source.fetched_at, new Date().toISOString()),
    stale: Boolean(source.stale ?? source.is_degraded),
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
    return [
      {
        date: asString(point.date),
        open: asNumber(point.open),
        high: asNumber(point.high),
        low: asNumber(point.low),
        close: asNumber(point.close),
        volume: asNumber(point.volume),
      },
    ];
  });
}

function deriveSignals(snapshot: Snapshot): Signals {
  const bars = normalizeBars(snapshot.history ?? {});
  const quote = normalizeQuote(snapshot.quote, "NOW");
  const closes = bars.map((bar) => bar.close).filter((value) => value > 0);
  const first = closes[0] ?? quote.prev_close;
  const last = closes.at(-1) ?? quote.price;
  const momentum = first ? ((last - first) / first) * 100 : quote.change_pct;
  const score = Math.max(-100, Math.min(100, Math.round(momentum * 3 + quote.change_pct * 4)));
  const buyProb = Math.max(5, Math.min(90, Math.round(50 + score / 2)));
  const sellProb = Math.max(5, Math.min(90, Math.round(50 - score / 2)));
  const holdProb = Math.max(0, 100 - buyProb - sellProb);
  const action = score > 15 ? "BUY" : score < -15 ? "SELL" : "HOLD";

  return {
    composite_score: score,
    buy_prob: buyProb,
    hold_prob: holdProb,
    sell_prob: sellProb,
    action,
    confidence: Math.min(95, Math.max(35, Math.abs(score) + 45)),
    agreement: `${Math.min(10, Math.max(1, Math.round(Math.abs(score) / 10) + 3))}/10`,
    signal_strength: Math.min(5, Math.max(1, Math.round(Math.abs(score) / 25) + 1)),
    indicator_breakdown: {
      momentum: { score, weight: 40, contribution: score * 0.4, signal: action },
      daily_change: {
        score: Math.round(quote.change_pct * 10),
        weight: 25,
        contribution: quote.change_pct * 2.5,
        signal: quote.change_pct >= 0 ? "BUY" : "SELL",
      },
      trend: {
        score: Math.round(momentum),
        weight: 35,
        contribution: momentum * 0.35,
        signal: momentum >= 0 ? "BUY" : "SELL",
      },
    },
  };
}

function deriveRisk(snapshot: Snapshot) {
  const bars = normalizeBars(snapshot.history ?? {});
  const closes = bars.map((bar) => bar.close).filter((value) => value > 0);
  const returns = closes.slice(1).map((close, index) => (close - closes[index]) / closes[index]);
  const avg = returns.reduce((sum, value) => sum + value, 0) / (returns.length || 1);
  const variance =
    returns.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (returns.length || 1);
  const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100;
  let peak = closes[0] ?? 0;
  const drawdown_series = bars.map((bar) => {
    peak = Math.max(peak, bar.close);
    return { date: bar.date, value: peak ? Number((((bar.close - peak) / peak) * 100).toFixed(2)) : 0 };
  });
  const maxDrawdown = Math.min(0, ...drawdown_series.map((point) => point.value));

  return {
    sharpe_ratio: volatility ? Number(((avg * 252 * 100) / volatility).toFixed(2)) : 0,
    max_drawdown_all: maxDrawdown,
    beta_252: 1,
    risk_score: Math.min(100, Math.round(Math.abs(maxDrawdown) * 1.5 + volatility * 0.4)),
    volatility_percentile: Math.min(100, Math.round(volatility)),
    drawdown_series,
    var: { historical_95: Number((Math.abs(avg - 1.65 * Math.sqrt(variance)) * 100).toFixed(2)) },
    kelly: { full_kelly_pct: 0, half_kelly_pct: 0 },
  };
}

function deriveMonte(snapshot: Snapshot) {
  const quote = normalizeQuote(snapshot.quote, "NOW");
  const bars = normalizeBars(snapshot.history ?? {});
  const closes = bars.map((bar) => bar.close).filter((value) => value > 0);
  const start = closes.at(-1) || quote.price || quote.prev_close || 1;
  const returns = closes.slice(1).map((close, index) => (close - closes[index]) / closes[index]);
  const avg = returns.reduce((sum, value) => sum + value, 0) / (returns.length || 1);
  const variance =
    returns.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (returns.length || 1);
  const dailyVolatility = Math.max(0.003, Math.min(0.025, Math.sqrt(variance)));
  const boundedDrift = Math.max(-0.0004, Math.min(0.0004, avg));
  const percentiles = {
    "25": Array.from({ length: 90 }, (_, index) =>
      Number((start * (1 + boundedDrift * index - dailyVolatility * Math.sqrt(index) * 0.7)).toFixed(2)),
    ),
    "50": Array.from({ length: 90 }, (_, index) =>
      Number((start * (1 + boundedDrift * index)).toFixed(2)),
    ),
    "75": Array.from({ length: 90 }, (_, index) =>
      Number((start * (1 + boundedDrift * index + dailyVolatility * Math.sqrt(index) * 0.7)).toFixed(2)),
    ),
  };
  return { current_price: start, prob_above_current: 50, percentiles };
}

function deriveInsight(snapshot: Snapshot) {
  const quote = normalizeQuote(snapshot.quote, "NOW");
  const signals = deriveSignals(snapshot);
  const profile = isRecord(snapshot.profile) ? snapshot.profile : {};

  return {
    verdict: signals.action,
    confidence: signals.confidence,
    generated_at: asString(snapshot.metadata?.fetched_at ?? quote.timestamp, new Date().toISOString()),
    plain_english_summary: `${quote.ticker} is trading at ${money(quote.price)} with a ${quote.change_pct.toFixed(2)}% daily move. ${asString(profile.business_summary, "Live backend data is available for quote, profile, and history.")}`,
    bullish_reasons: ["Live quote and history are connected.", "Trend is calculated from backend history."],
    bearish_risks: quote.stale ? ["Backend is serving degraded upstream market data."] : ["Market data can change quickly."],
    key_levels: { day_low: quote.day_low, day_high: quote.day_high, previous_close: quote.prev_close },
    monte_carlo_narrative: "Scenario data is derived client-side from the live quote until the backend exposes a Monte Carlo route.",
    technical_summary: `Composite=${signals.composite_score}; source=${quote.source}.`,
  };
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown; message?: unknown };
    const detail = payload.detail ?? payload.message;
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
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  try {
    const res = await fetch(url, {
      ...init,
      cache: "no-store",
      headers,
    });
    if (!res.ok) {
      const message = await readErrorMessage(res);
      console.error("[api] Request failed", { url, status: res.status, message });
      throw new Error(`API ${res.status}: ${message}`);
    }
    return res.json();
  } catch (error) {
    console.error("[api] Request error", { url, error });
    throw error;
  }
}

async function fetchSnapshot(ticker: string): Promise<Snapshot> {
  return fetchJson(`/snapshot/${encodeTicker(ticker)}?period=1y&interval=1d`) as Promise<Snapshot>;
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
    return deriveSignals(await fetchSnapshot(ticker)) as T;
  }

  if (path.startsWith("/quant/indicators/")) {
    const snapshot = await fetchSnapshot(ticker);
    return { regime: deriveSignals(snapshot).action, adx: { value: Math.abs(deriveSignals(snapshot).composite_score) } } as T;
  }

  if (path.startsWith("/risk/")) {
    return deriveRisk(await fetchSnapshot(ticker)) as T;
  }

  if (path.startsWith("/monte-carlo/")) {
    return deriveMonte(await fetchSnapshot(ticker)) as T;
  }

  if (path.startsWith("/insights/")) {
    return deriveInsight(await fetchSnapshot(ticker)) as T;
  }

  return fetchJson(path, init) as Promise<T>;
}

export function useApi<T>(path: string, refreshInterval = 60000) {
  return useSWR<T>(path, api, { refreshInterval, revalidateOnFocus: false });
}

export function money(value?: number | null) {
  return `$${Number(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}

export function pct(value?: number | null) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}
