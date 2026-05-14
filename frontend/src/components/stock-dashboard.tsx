"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  LineChart,
  Loader2,
  Search,
} from "lucide-react";

import {
  ChartPeriod,
  getMarketSnapshot,
  MarketSnapshot,
  normalizeTicker,
  validateTicker,
} from "@/lib/market-api";

const DEFAULT_TICKER = process.env.NEXT_PUBLIC_DEFAULT_TICKER ?? "NOW";
const PERIOD_OPTIONS: { label: string; value: ChartPeriod }[] = [
  { label: "1M", value: "1mo" },
  { label: "3M", value: "3mo" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
  { label: "MAX", value: "max" },
];

type ChartDatum = {
  date: string;
  close: number;
  volume: number;
};

function formatCurrency(value: number | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined) {
    return "N/A";
  }

  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 2,
    }).format(value);
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    notation: value >= 1_000_000 ? "compact" : "standard",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function calculateDailyChange(snapshot: MarketSnapshot | null): number | null {
  const price = snapshot?.quote.price;
  const previousClose = snapshot?.quote.previous_close;

  if (price === null || price === undefined || !previousClose) {
    return null;
  }

  return ((price - previousClose) / previousClose) * 100;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "just now";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function getDisplayError(message: string): string {
  if (/not found/i.test(message)) {
    return "I couldn't find market data for that ticker. Check the symbol and try again.";
  }

  if (/api url|next_public_api_base_url/i.test(message)) {
    return "The frontend is missing its backend API URL. Set NEXT_PUBLIC_API_BASE_URL in Vercel.";
  }

  if (/rate limit|too many requests/i.test(message)) {
    return "The market data provider is rate limiting requests. Try again in a few minutes.";
  }

  return message;
}

function MetricCard({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="mt-3 text-2xl font-semibold text-foreground">{value}</div>
      {helper ? <p className="mt-1 text-sm text-muted-foreground">{helper}</p> : null}
    </div>
  );
}

function LoadingPanel() {
  return (
    <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-border bg-card/80">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        Loading market data
      </div>
    </div>
  );
}

export function StockDashboard() {
  const [searchValue, setSearchValue] = useState(DEFAULT_TICKER);
  const [activeTicker, setActiveTicker] = useState(DEFAULT_TICKER);
  const [selectedPeriod, setSelectedPeriod] = useState<ChartPeriod>("1y");
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inputError, setInputError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCurrent = true;

    setIsLoading(true);
    setError(null);

    getMarketSnapshot(activeTicker, selectedPeriod)
      .then((data) => {
        if (isCurrent) {
          setSnapshot(data);
        }
      })
      .catch((requestError: unknown) => {
        if (isCurrent) {
          setSnapshot(null);
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load market data.",
          );
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [activeTicker, selectedPeriod]);

  const chartData = useMemo<ChartDatum[]>(() => {
    return (
      snapshot?.history.points.flatMap((point) =>
        point.close === null
          ? []
          : [
              {
                date: point.date,
                close: point.close,
                volume: point.volume ?? 0,
              },
            ],
      ) ?? []
    );
  }, [snapshot]);

  const dailyChange = calculateDailyChange(snapshot);
  const isPositiveChange = dailyChange !== null && dailyChange >= 0;
  const currency = snapshot?.quote.currency || "USD";
  const displayTicker = snapshot?.quote.ticker || snapshot?.metadata.ticker || activeTicker;
  const companyName = snapshot?.quote.name ?? snapshot?.profile.name;
  const isDegraded =
    snapshot?.metadata.is_degraded ??
    snapshot?.quote.is_degraded ??
    snapshot?.history.is_degraded ??
    snapshot?.profile.is_degraded ??
    false;
  const providerMessage =
    snapshot?.metadata.provider_message ??
    snapshot?.quote.provider_message ??
    snapshot?.history.provider_message ??
    snapshot?.profile.provider_message;
  const activePeriodLabel =
    PERIOD_OPTIONS.find((option) => option.value === selectedPeriod)?.label ?? "1Y";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationMessage = validateTicker(searchValue);

    if (validationMessage) {
      setInputError(validationMessage);
      return;
    }

    setInputError(null);
    setActiveTicker(normalizeTicker(searchValue));
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="border-b border-border bg-card/70">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-7 sm:px-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-primary">
              <LineChart className="h-4 w-4" />
              DadStock
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              Stock dashboard
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              A compact market view for tracking quotes, company context, price
              history, and volume from a FastAPI data service.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="w-full max-w-md">
            <label
              htmlFor="ticker-search"
              className="text-sm font-medium text-muted-foreground"
            >
              Ticker
            </label>
            <div className="mt-2 flex gap-2">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="ticker-search"
                  value={searchValue}
                  onChange={(event) => {
                    setSearchValue(event.target.value.toUpperCase());
                    setInputError(null);
                  }}
                  className="h-11 w-full rounded-md border border-border bg-background pl-10 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                  maxLength={12}
                  placeholder="Try NOW, AAPL, MSFT..."
                />
              </div>
              <button
                type="submit"
                className="inline-flex h-11 min-w-11 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isLoading}
                aria-label="Search ticker"
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                <span className="hidden sm:inline">Search</span>
              </button>
            </div>
            {inputError ? (
              <p className="mt-2 text-sm text-destructive">{inputError}</p>
            ) : null}
          </form>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-5 py-6 sm:px-8">
        {isLoading && snapshot ? (
          <div className="mb-5 flex items-center gap-3 rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            Refreshing {activeTicker} market data
          </div>
        ) : null}

        {error ? (
          <div className="mb-5 flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive-foreground">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <p className="font-semibold text-foreground">Market data unavailable</p>
              <p className="mt-1 text-muted-foreground">{getDisplayError(error)}</p>
            </div>
          </div>
        ) : null}

        {isDegraded && snapshot ? (
          <div className="mb-5 flex items-start gap-3 rounded-lg border border-amber-400/35 bg-amber-400/10 p-4 text-sm">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" />
            <div>
              <p className="font-semibold text-foreground">Showing fallback market data</p>
              <p className="mt-1 text-muted-foreground">
                {providerMessage ??
                  "The upstream provider is temporarily unavailable. Sample data is displayed so the dashboard remains usable."}
              </p>
            </div>
          </div>
        ) : null}

        {isLoading && !snapshot ? (
          <LoadingPanel />
        ) : snapshot ? (
          <div className={`space-y-5 ${isLoading ? "opacity-75" : ""}`}>
            <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5 shadow-sm shadow-black/20 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm text-muted-foreground">
                  {snapshot.quote.exchange ?? "Exchange unavailable"} ·{" "}
                  {snapshot.quote.currency ?? "Currency unavailable"}
                </p>
                <h2 className="mt-2 flex flex-col gap-1 text-3xl font-semibold sm:flex-row sm:items-baseline">
                  {displayTicker}
                  {companyName ? (
                    <span className="text-xl font-medium text-muted-foreground sm:ml-3">
                      {companyName}
                    </span>
                  ) : null}
                </h2>
                <p className="mt-3 text-xs text-muted-foreground">
                  Updated {formatTimestamp(snapshot.metadata.fetched_at)}
                </p>
              </div>
              <div className="text-left sm:text-right">
                <div className="text-4xl font-semibold">
                  {formatCurrency(snapshot.quote.price, currency)}
                </div>
                <div
                  className={`mt-2 inline-flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium ${
                    isPositiveChange
                      ? "bg-emerald-500/10 text-emerald-300"
                      : "bg-red-500/10 text-red-300"
                  }`}
                >
                  {isPositiveChange ? (
                    <ArrowUpRight className="h-4 w-4" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4" />
                  )}
                  {dailyChange === null ? "N/A" : `${dailyChange.toFixed(2)}% today`}
                </div>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="Volume"
                value={formatNumber(snapshot.quote.volume)}
                helper="Latest reported trading volume"
              />
              <MetricCard
                label="Previous close"
                value={formatCurrency(snapshot.quote.previous_close, currency)}
                helper="Reference for daily movement"
              />
              <MetricCard
                label="Day range"
                value={`${formatCurrency(snapshot.quote.day_low, currency)} - ${formatCurrency(
                  snapshot.quote.day_high,
                  currency,
                )}`}
                helper="Intraday low to high"
              />
              <MetricCard
                label="Market cap"
                value={formatNumber(snapshot.quote.market_cap)}
                helper="Company equity value"
              />
            </div>

            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(340px,0.75fr)]">
              <div className="rounded-lg border border-border bg-card p-5 shadow-sm shadow-black/20">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">Historical close</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {activePeriodLabel} · Daily interval · {snapshot.metadata.source}
                    </p>
                  </div>
                  <div className="flex w-full rounded-md border border-border bg-background p-1 sm:w-auto">
                    {PERIOD_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => setSelectedPeriod(option.value)}
                        className={`h-8 flex-1 rounded px-3 text-xs font-semibold transition sm:flex-none ${
                          selectedPeriod === option.value
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                        disabled={isLoading}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mt-5 h-[360px]">
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                        <defs>
                          <linearGradient id="closeGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
                        <XAxis
                          dataKey="date"
                          tickFormatter={formatDate}
                          minTickGap={32}
                          stroke="hsl(var(--muted-foreground))"
                          tickLine={false}
                          axisLine={false}
                          fontSize={12}
                        />
                        <YAxis
                          domain={["dataMin", "dataMax"]}
                          tickFormatter={(value) => `$${Number(value).toFixed(0)}`}
                          stroke="hsl(var(--muted-foreground))"
                          tickLine={false}
                          axisLine={false}
                          fontSize={12}
                          width={52}
                        />
                        <Tooltip
                          contentStyle={{
                            background: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "8px",
                            color: "hsl(var(--foreground))",
                          }}
                          formatter={(value) => [
                            formatCurrency(Number(value), currency),
                            "Close",
                          ]}
                          labelFormatter={(label) =>
                            Number.isNaN(new Date(`${label}T00:00:00`).getTime())
                              ? String(label)
                              : new Intl.DateTimeFormat("en-US", {
                                  month: "short",
                                  day: "numeric",
                                  year: "numeric",
                                }).format(new Date(`${label}T00:00:00`))
                          }
                        />
                        <Area
                          type="monotone"
                          dataKey="close"
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                          fill="url(#closeGradient)"
                          dot={false}
                          activeDot={{ r: 4 }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full items-center justify-center rounded-md border border-border bg-background text-sm text-muted-foreground">
                      No historical prices returned for this period.
                    </div>
                  )}
                </div>
              </div>

              <aside className="rounded-lg border border-border bg-card p-5 shadow-sm shadow-black/20">
                <div className="flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold">Company profile</h3>
                </div>
                <dl className="mt-5 space-y-4 text-sm">
                  <div>
                    <dt className="text-muted-foreground">Sector</dt>
                    <dd className="mt-1 font-medium">{snapshot.profile.sector ?? "N/A"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Industry</dt>
                    <dd className="mt-1 font-medium">{snapshot.profile.industry ?? "N/A"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Country</dt>
                    <dd className="mt-1 font-medium">{snapshot.profile.country ?? "N/A"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Employees</dt>
                    <dd className="mt-1 font-medium">{formatNumber(snapshot.profile.employees)}</dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Website</dt>
                    <dd className="mt-1 font-medium">
                      {snapshot.profile.website ? (
                        <a
                          className="text-primary underline-offset-4 hover:underline"
                          href={snapshot.profile.website}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {snapshot.profile.website.replace(/^https?:\/\//, "")}
                        </a>
                      ) : (
                        "N/A"
                      )}
                    </dd>
                  </div>
                </dl>
                {snapshot.profile.business_summary ? (
                  <p className="mt-5 border-t border-border pt-5 text-sm leading-6 text-muted-foreground">
                    {snapshot.profile.business_summary}
                  </p>
                ) : null}
              </aside>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
