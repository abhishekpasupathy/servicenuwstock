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
