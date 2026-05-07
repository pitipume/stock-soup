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
};
