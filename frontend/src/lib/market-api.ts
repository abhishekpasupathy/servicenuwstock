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
  open: number;
  high: number;
  low: number;
  close: number;
  adj_close: number | null;
  volume: number;
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

function getApiBaseUrl(): string {
  if (!API_BASE_URL) {
    throw new Error(
      "The API URL is not configured. Set NEXT_PUBLIC_API_BASE_URL to your backend /api URL.",
    );
  }

  return API_BASE_URL.replace(/\/$/, "");
}

async function fetchJson<T>(path: string): Promise<T> {
  const url = `${getApiBaseUrl()}${path}`;
  const response = await fetch(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let message = `Market data request failed (${response.status}).`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      message = response.statusText || message;
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
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

export async function getMarketSnapshot(
  ticker: string,
  period: ChartPeriod,
): Promise<MarketSnapshot> {
  const normalizedTicker = normalizeTicker(ticker);
  const encodedTicker = encodeURIComponent(normalizedTicker);

  return fetchJson<MarketSnapshot>(
    `/snapshot/${encodedTicker}?period=${period}&interval=1d`,
  );
}

export async function getQuote(ticker: string): Promise<QuoteResponse> {
  const encodedTicker = encodeURIComponent(normalizeTicker(ticker));
  return fetchJson<QuoteResponse>(`/quote/${encodedTicker}`);
}

export async function getProfile(ticker: string): Promise<ProfileResponse> {
  const encodedTicker = encodeURIComponent(normalizeTicker(ticker));
  return fetchJson<ProfileResponse>(`/profile/${encodedTicker}`);
}

export async function getHistory(
  ticker: string,
  period: ChartPeriod,
): Promise<HistoryResponse> {
  const encodedTicker = encodeURIComponent(normalizeTicker(ticker));
  return fetchJson<HistoryResponse>(
    `/history/${encodedTicker}?period=${period}&interval=1d`,
  );
}
