export type QuoteResponse = {
  ticker: string;
  name: string | null;
  currency: string | null;
  exchange: string | null;
  price: number | null;
  previous_close: number | null;
  open: number | null;
  day_high: number | null;
  day_low: number | null;
  volume: number | null;
  market_cap: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  source: string;
  is_degraded: boolean;
  provider_message: string | null;
  fetched_at: string;
};

export type HistoryPoint = {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  adj_close: number | null;
  volume: number | null;
};

export type HistoryResponse = {
  ticker: string;
  period: string;
  interval: string;
  points: HistoryPoint[];
  source: string;
  is_degraded: boolean;
  provider_message: string | null;
  fetched_at: string;
};

export type ProfileResponse = {
  ticker: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  country: string | null;
  website: string | null;
  employees: number | null;
  business_summary: string | null;
  source: string;
  is_degraded: boolean;
  provider_message: string | null;
  fetched_at: string;
};

export type ChartPeriod = "1mo" | "3mo" | "6mo" | "1y" | "max";

export type SnapshotMetadata = {
  ticker: string;
  period: string;
  interval: string;
  source: string;
  is_degraded: boolean;
  provider_message: string | null;
  fetched_at: string;
};

export type MarketSnapshot = {
  quote: QuoteResponse;
  history: HistoryResponse;
  profile: ProfileResponse;
  metadata: SnapshotMetadata;
};

const DEFAULT_API_BASE_URL = "https://servicenuwstock-api.onrender.com/api/v1";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;

function getApiBaseUrl(): string {
  return API_BASE_URL.replace(/\/+$/, "");
}

async function readErrorMessage(response: Response): Promise<string> {
  let message = `Market data request failed (${response.status}).`;

  try {
    const payload = (await response.json()) as { detail?: unknown; message?: unknown };
    const detail = payload.detail ?? payload.message;
    if (typeof detail === "string" && detail.trim()) {
      message = detail;
    }
  } catch {
    message = response.statusText || message;
  }

  return message;
}

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  try {
    const response = await fetch(url, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const message = await readErrorMessage(response);
      console.error("[market-api] Request failed", {
        url,
        status: response.status,
        message,
      });
      throw new Error(message);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    console.error("[market-api] Request error", { url, error });
    throw error;
  }
}

export function normalizeTicker(value: string): string {
  return value.trim().toUpperCase();
}

export function validateTicker(value: string): string | null {
  const ticker = normalizeTicker(value);

  if (!ticker) {
    return "Enter a ticker symbol.";
  }

  if (!/^[A-Z0-9.-]{1,12}$/.test(ticker)) {
    return "Use 1-12 letters, numbers, dots, or hyphens.";
  }

  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getValue(source: Record<string, unknown>, ...keys: string[]): unknown {
  for (const key of keys) {
    if (source[key] !== undefined) {
      return source[key];
    }
  }

  return undefined;
}

function toStringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function toBoolean(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}

function toFetchedAt(value: unknown): string {
  return toStringOrNull(value) ?? new Date().toISOString();
}

function normalizeQuote(payload: unknown, fallbackTicker: string): QuoteResponse {
  const source = isRecord(payload) ? payload : {};

  return {
    ticker: toStringOrNull(getValue(source, "ticker", "symbol")) ?? fallbackTicker,
    name: toStringOrNull(getValue(source, "name", "companyName", "longName", "shortName")),
    currency: toStringOrNull(source.currency),
    exchange: toStringOrNull(getValue(source, "exchange", "exchangeName")),
    price: toNumberOrNull(getValue(source, "price", "currentPrice", "regularMarketPrice")),
    previous_close: toNumberOrNull(
      getValue(source, "previous_close", "previousClose", "regularMarketPreviousClose"),
    ),
    open: toNumberOrNull(getValue(source, "open", "regularMarketOpen")),
    day_high: toNumberOrNull(getValue(source, "day_high", "dayHigh", "regularMarketDayHigh")),
    day_low: toNumberOrNull(getValue(source, "day_low", "dayLow", "regularMarketDayLow")),
    volume: toNumberOrNull(getValue(source, "volume", "regularMarketVolume")),
    market_cap: toNumberOrNull(getValue(source, "market_cap", "marketCap")),
    fifty_two_week_high: toNumberOrNull(
      getValue(source, "fifty_two_week_high", "fiftyTwoWeekHigh"),
    ),
    fifty_two_week_low: toNumberOrNull(
      getValue(source, "fifty_two_week_low", "fiftyTwoWeekLow"),
    ),
    source: toStringOrNull(source.source) ?? "unknown",
    is_degraded: toBoolean(getValue(source, "is_degraded", "isDegraded")),
    provider_message: toStringOrNull(getValue(source, "provider_message", "providerMessage")),
    fetched_at: toFetchedAt(getValue(source, "fetched_at", "fetchedAt")),
  };
}

function normalizeHistory(
  payload: unknown,
  fallbackTicker: string,
  period: ChartPeriod,
): HistoryResponse {
  const source = isRecord(payload) ? payload : {};
  const rawPoints = getValue(source, "points", "history", "prices");
  const points = Array.isArray(rawPoints) ? rawPoints : [];

  return {
    ticker: toStringOrNull(getValue(source, "ticker", "symbol")) ?? fallbackTicker,
    period: toStringOrNull(source.period) ?? period,
    interval: toStringOrNull(source.interval) ?? "1d",
    points: points.flatMap((point) => {
      if (!isRecord(point)) {
        return [];
      }

      const date = toStringOrNull(getValue(point, "date", "datetime"));
      const close = toNumberOrNull(getValue(point, "close", "adj_close", "adjClose"));
      if (!date || close === null) {
        return [];
      }

      return [
        {
          date,
          open: toNumberOrNull(point.open),
          high: toNumberOrNull(point.high),
          low: toNumberOrNull(point.low),
          close,
          adj_close: toNumberOrNull(getValue(point, "adj_close", "adjClose")),
          volume: toNumberOrNull(point.volume),
        },
      ];
    }),
    source: toStringOrNull(source.source) ?? "unknown",
    is_degraded: toBoolean(getValue(source, "is_degraded", "isDegraded")),
    provider_message: toStringOrNull(getValue(source, "provider_message", "providerMessage")),
    fetched_at: toFetchedAt(getValue(source, "fetched_at", "fetchedAt")),
  };
}

function normalizeProfile(payload: unknown, fallbackTicker: string): ProfileResponse {
  const source = isRecord(payload) ? payload : {};

  return {
    ticker: toStringOrNull(getValue(source, "ticker", "symbol")) ?? fallbackTicker,
    name: toStringOrNull(getValue(source, "name", "companyName", "longName", "shortName")),
    sector: toStringOrNull(source.sector),
    industry: toStringOrNull(source.industry),
    country: toStringOrNull(source.country),
    website: toStringOrNull(source.website),
    employees: toNumberOrNull(getValue(source, "employees", "fullTimeEmployees")),
    business_summary: toStringOrNull(
      getValue(source, "business_summary", "businessSummary", "longBusinessSummary"),
    ),
    source: toStringOrNull(source.source) ?? "unknown",
    is_degraded: toBoolean(getValue(source, "is_degraded", "isDegraded")),
    provider_message: toStringOrNull(getValue(source, "provider_message", "providerMessage")),
    fetched_at: toFetchedAt(getValue(source, "fetched_at", "fetchedAt")),
  };
}

function normalizeSnapshotMetadata(
  payload: unknown,
  fallbackTicker: string,
  period: ChartPeriod,
  quote: QuoteResponse,
  history: HistoryResponse,
  profile: ProfileResponse,
): SnapshotMetadata {
  const source = isRecord(payload) ? payload : {};
  const providerMessage =
    toStringOrNull(getValue(source, "provider_message", "providerMessage")) ??
    quote.provider_message ??
    history.provider_message ??
    profile.provider_message;

  return {
    ticker: toStringOrNull(getValue(source, "ticker", "symbol")) ?? fallbackTicker,
    period: toStringOrNull(source.period) ?? period,
    interval: toStringOrNull(source.interval) ?? history.interval ?? "1d",
    source:
      toStringOrNull(source.source) ??
      Array.from(new Set([quote.source, history.source, profile.source])).join(","),
    is_degraded:
      toBoolean(getValue(source, "is_degraded", "isDegraded")) ||
      quote.is_degraded ||
      history.is_degraded ||
      profile.is_degraded,
    provider_message: providerMessage,
    fetched_at: toFetchedAt(getValue(source, "fetched_at", "fetchedAt")),
  };
}

function normalizeMarketSnapshot(
  payload: unknown,
  fallbackTicker: string,
  period: ChartPeriod,
): MarketSnapshot {
  const source = isRecord(payload) ? payload : {};
  const quote = normalizeQuote(source.quote ?? payload, fallbackTicker);
  const history = normalizeHistory(source.history, quote.ticker, period);
  const profile = normalizeProfile(source.profile ?? payload, quote.ticker);

  return {
    quote,
    history,
    profile,
    metadata: normalizeSnapshotMetadata(
      source.metadata,
      quote.ticker,
      period,
      quote,
      history,
      profile,
    ),
  };
}

export async function getMarketSnapshot(
  ticker: string,
  period: ChartPeriod,
): Promise<MarketSnapshot> {
  const normalizedTicker = normalizeTicker(ticker);
  const encodedTicker = encodeURIComponent(normalizedTicker);

  try {
    const payload = await fetchJson<unknown>(
      `/snapshot/${encodedTicker}?period=${period}&interval=1d`,
    );
    return normalizeMarketSnapshot(payload, normalizedTicker, period);
  } catch (snapshotError) {
    const [quoteResult, historyResult, profileResult] = await Promise.allSettled([
      getQuote(normalizedTicker),
      getHistory(normalizedTicker, period),
      getProfile(normalizedTicker),
    ]);

    if (
      quoteResult.status === "rejected" &&
      historyResult.status === "rejected" &&
      profileResult.status === "rejected"
    ) {
      throw snapshotError;
    }

    const quote =
      quoteResult.status === "fulfilled"
        ? quoteResult.value
        : normalizeQuote({}, normalizedTicker);
    const history =
      historyResult.status === "fulfilled"
        ? historyResult.value
        : normalizeHistory({}, normalizedTicker, period);
    const profile =
      profileResult.status === "fulfilled"
        ? profileResult.value
        : normalizeProfile({}, normalizedTicker);

    return {
      quote,
      history,
      profile,
      metadata: normalizeSnapshotMetadata(
        {},
        normalizedTicker,
        period,
        quote,
        history,
        profile,
      ),
    };
  }
}

export async function getQuote(ticker: string): Promise<QuoteResponse> {
  const normalizedTicker = normalizeTicker(ticker);
  const encodedTicker = encodeURIComponent(normalizedTicker);
  return normalizeQuote(await fetchJson<unknown>(`/quote/${encodedTicker}`), normalizedTicker);
}

export async function getProfile(ticker: string): Promise<ProfileResponse> {
  const encodedTicker = encodeURIComponent(normalizeTicker(ticker));
  return normalizeProfile(
    await fetchJson<unknown>(`/profile/${encodedTicker}`),
    normalizeTicker(ticker),
  );
}

export async function getHistory(
  ticker: string,
  period: ChartPeriod,
): Promise<HistoryResponse> {
  const normalizedTicker = normalizeTicker(ticker);
  const encodedTicker = encodeURIComponent(normalizedTicker);
  return normalizeHistory(
    await fetchJson<unknown>(
      `/history/${encodedTicker}?period=${period}&interval=1d`,
    ),
    normalizedTicker,
    period,
  );
}
