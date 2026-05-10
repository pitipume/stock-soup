const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface VIMetrics {
  pe_ratio: number | null;
  pb_ratio: number | null;
  debt_to_equity: number | null;
  roe: number | null;
  revenue_growth: number | null;
  free_cash_flow: number | null;
  insider_ownership: number | null;
  market_cap: number | null;
  analyst_count: number | null;
}

export interface ScanResult {
  ticker: string;
  company_name: string;
  vi_score: number;
  verdict: "strong_buy" | "buy" | "hold" | "skip";
  metrics: VIMetrics;
}

export interface Scan {
  id: number;
  status: "pending" | "running" | "done" | "failed";
  total_scanned: number;
  results_count: number;
  created_at: string;
  completed_at: string | null;
  results?: ScanResult[];
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const viApi = {
  startScan: () => api<Scan>("/vi/scan", { method: "POST" }),
  listScans: () => api<Scan[]>("/vi/scans"),
  getScan: (id: number) => api<Scan>(`/vi/scans/${id}`),
  getStock: (ticker: string) => api<ScanResult>(`/vi/stocks/${ticker}`),
};

// ── Bot types ──────────────────────────────────────────────────────────────

export interface BotStatus {
  is_suspended: boolean;
  suspension_reason: string | null;
  active_strategy: string;
  strategy_params: Record<string, unknown>;
  trading_mode: string;
  is_stub: boolean;
}

export interface Portfolio {
  balance_usdt: number;
  equity_usdt: number;
  high_water_mark: number;
  drawdown_pct: number;
  trading_mode: string;
  is_stub: boolean;
}

export interface Position {
  id: number;
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  leverage: number;
  strategy: string;
  opened_at: string;
}

export interface Trade {
  id: number;
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  exit_price: number;
  pnl_usdt: number;
  pnl_pct: number;
  outcome: string;
  strategy: string;
  close_reason: string;
  opened_at: string;
  closed_at: string;
}

export interface TradeStats {
  total_trades: number;
  win_rate_pct: number;
  avg_pnl_usdt: number;
  total_pnl_usdt: number;
  avg_rr: number;
}

export const botApi = {
  getStatus: () => api<BotStatus>("/bot/status"),
  getPortfolio: () => api<Portfolio>("/bot/portfolio"),
  getPositions: () => api<Position[]>("/bot/positions"),
  getTrades: (limit = 50) => api<Trade[]>(`/bot/trades?limit=${limit}`),
  getStats: () => api<TradeStats>("/bot/stats"),
  resume: () => api<BotStatus>("/bot/resume", { method: "POST" }),
  updateConfig: (body: { active_strategy?: string; strategy_params?: Record<string, unknown> }) =>
    api<BotStatus>("/bot/config", { method: "PATCH", body: JSON.stringify(body) }),
};
