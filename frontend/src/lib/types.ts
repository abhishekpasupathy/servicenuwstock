export type Quote = {
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  avg_volume: number;
  market_cap: number;
  pe_ratio: number;
  week_52_high: number;
  week_52_low: number;
  day_high: number;
  day_low: number;
  prev_close: number;
  open: number;
  source: string;
  timestamp: string;
  stale?: boolean;
};

export type Bar = { date: string; open: number; high: number; low: number; close: number; volume: number };
export type RealtimeQuote = {
  type: "quote";
  ticker: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  bid?: number | null;
  ask?: number | null;
  timestamp: string;
  provider?: string;
  source?: string;
  delayed?: boolean;
  stale?: boolean;
  signal?: string | null;
  composite_score?: number | null;
};

export type MarketStatus = {
  is_open: boolean;
  status: "OPEN" | "PRE_MARKET" | "AFTER_HOURS" | "CLOSED";
  next_open?: string | null;
  next_close?: string | null;
  message: string;
  timestamp: string;
};

export type Signals = {
  composite_score: number;
  buy_prob: number;
  hold_prob: number;
  sell_prob: number;
  action: string;
  confidence: number;
  agreement?: string;
  signal_strength: number;
  indicator_breakdown: Record<string, { score: number; weight: number; contribution: number; signal: string }>;
};

export type Prediction = {
  ticker: string;
  current_price: number;
  day_prediction: {
    predicted_high: number;
    predicted_low: number;
    predicted_mid: number;
    atr_value: number;
    atr_pct: number;
  };
  year_prediction: {
    median_target: number;
    base_target: number;
    ci_95_low: number;
    ci_95_high: number;
    prob_above_current: number;
    prob_10pct_gain: number;
    prob_20pct_gain: number;
    prob_10pct_loss: number;
    expected_return_pct: number;
  };
  direction_bias: number;
  direction_label: string;
  regime: string;
  composite_score: number;
  action: string;
  confidence: number;
  support_levels: number[];
  resistance_levels: number[];
  algorithms: Record<string, { weight: number; value: string | number; description: string }>;
  source: string;
  stale?: boolean;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type TradingSystem = Record<string, any>;
