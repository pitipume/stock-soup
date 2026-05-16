"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { viApi, type Scan, type ScanResult } from "@/lib/api";

// ── Verdict badge ─────────────────────────────────────────────────────────────
const VERDICT_STYLES: Record<string, string> = {
  strong_buy: "bg-emerald-900 text-emerald-300 border border-emerald-700",
  buy: "bg-blue-900 text-blue-300 border border-blue-700",
  hold: "bg-amber-900 text-amber-300 border border-amber-700",
  skip: "bg-red-900 text-red-300 border border-red-700",
};
const VERDICT_LABELS: Record<string, string> = {
  strong_buy: "Strong Buy",
  buy: "Buy",
  hold: "Hold",
  skip: "Skip",
};

function VerdictBadge({ verdict }: { verdict: string }) {
  return (
    <span
      className={`px-2 py-0.5 text-xs font-semibold rounded-full ${VERDICT_STYLES[verdict] ?? "bg-zinc-800 text-zinc-400"}`}
    >
      {VERDICT_LABELS[verdict] ?? verdict}
    </span>
  );
}

// ── Metric formatting helpers ─────────────────────────────────────────────────
function fmt(val: number | null, decimals = 2, suffix = "") {
  if (val === null || val === undefined) return "—";
  return `${val.toFixed(decimals)}${suffix}`;
}
function fmtPct(val: number | null) {
  if (val === null || val === undefined) return "—";
  return `${(val * 100).toFixed(1)}%`;
}
function fmtMarketCap(val: number | null) {
  if (!val) return "—";
  if (val >= 1e12) return `$${(val / 1e12).toFixed(1)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  return `$${(val / 1e6).toFixed(0)}M`;
}

// ── Results table ─────────────────────────────────────────────────────────────
function ResultsTable({ results }: { results: ScanResult[] }) {
  if (results.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-zinc-400 text-xs uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3 text-left">Ticker</th>
            <th className="px-4 py-3 text-left">Company</th>
            <th className="px-4 py-3 text-right">VI Score</th>
            <th className="px-4 py-3 text-right">P/E</th>
            <th className="px-4 py-3 text-right">P/B</th>
            <th className="px-4 py-3 text-right">ROE</th>
            <th className="px-4 py-3 text-right">Rev Growth</th>
            <th className="px-4 py-3 text-right">Mkt Cap</th>
            <th className="px-4 py-3 text-center">Verdict</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {results.map((r) => (
            <tr key={r.ticker} className="hover:bg-zinc-900/50 transition-colors">
              <td className="px-4 py-3 font-mono font-bold text-emerald-400">
                <Link href={`/vi/${r.ticker}`} className="hover:underline">
                  {r.ticker}
                </Link>
              </td>
              <td className="px-4 py-3 text-zinc-300 max-w-[200px] truncate">
                {r.company_name}
              </td>
              <td className="px-4 py-3 text-right font-bold">
                <span
                  className={
                    r.vi_score >= 75
                      ? "text-emerald-400"
                      : r.vi_score >= 55
                        ? "text-blue-400"
                        : "text-amber-400"
                  }
                >
                  {r.vi_score}
                </span>
              </td>
              <td className="px-4 py-3 text-right text-zinc-300">
                {fmt(r.metrics.pe_ratio, 1)}
              </td>
              <td className="px-4 py-3 text-right text-zinc-300">
                {fmt(r.metrics.pb_ratio, 2)}
              </td>
              <td className="px-4 py-3 text-right text-zinc-300">
                {fmtPct(r.metrics.roe)}
              </td>
              <td className="px-4 py-3 text-right text-zinc-300">
                {fmtPct(r.metrics.revenue_growth)}
              </td>
              <td className="px-4 py-3 text-right text-zinc-300">
                {fmtMarketCap(r.metrics.market_cap)}
              </td>
              <td className="px-4 py-3 text-center">
                <VerdictBadge verdict={r.verdict} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Scan history list ─────────────────────────────────────────────────────────
const STATUS_DOT: Record<string, string> = {
  done: "bg-emerald-400",
  running: "bg-blue-400 animate-pulse",
  pending: "bg-amber-400 animate-pulse",
  failed: "bg-red-400",
};

function ScanHistoryItem({
  scan,
  selected,
  onClick,
}: {
  scan: Scan;
  selected: boolean;
  onClick: () => void;
}) {
  const date = new Date(scan.created_at).toLocaleString();
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
        selected
          ? "border-emerald-600 bg-emerald-950/30"
          : "border-zinc-800 hover:border-zinc-600 bg-zinc-900"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[scan.status] ?? "bg-zinc-500"}`}
        />
        <span className="text-xs text-zinc-400">{date}</span>
        <span className="ml-auto text-xs text-zinc-500 capitalize">
          {scan.status}
        </span>
      </div>
      {scan.status === "done" && (
        <p className="text-xs text-zinc-500 mt-1 pl-4">
          {scan.results_count} results from {scan.total_scanned} scanned
        </p>
      )}
    </button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function VIScannerPage() {
  const queryClient = useQueryClient();
  const [selectedScanId, setSelectedScanId] = useState<number | null>(null);

  const { data: scans = [], isLoading: scansLoading } = useQuery({
    queryKey: ["vi-scans"],
    queryFn: viApi.listScans,
    refetchInterval: (query) => {
      const running = query.state.data?.some(
        (s) => s.status === "pending" || s.status === "running"
      );
      return running ? 3000 : false;
    },
  });

  const { data: activeScan, isLoading: scanLoading } = useQuery({
    queryKey: ["vi-scan", selectedScanId],
    queryFn: () => viApi.getScan(selectedScanId!),
    enabled: selectedScanId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 3000 : false;
    },
  });

  const startScan = useMutation({
    mutationFn: viApi.startScan,
    onSuccess: (newScan) => {
      queryClient.invalidateQueries({ queryKey: ["vi-scans"] });
      setSelectedScanId(newScan.id);
    },
  });

  const isScanning = scans.some(
    (s) => s.status === "pending" || s.status === "running"
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">VI Scanner</h1>
          <p className="text-sm text-zinc-500 mt-0.5">
            Value Investing screen — US markets (S&amp;P 500 + NASDAQ-100)
          </p>
        </div>
        <button
          onClick={() => startScan.mutate()}
          disabled={isScanning || startScan.isPending}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
        >
          {isScanning ? "Scanning…" : "Scan US Markets"}
        </button>
      </div>

      {/* Warning: scans take time */}
      {isScanning && (
        <div className="rounded-lg border border-blue-800 bg-blue-950/30 px-4 py-3 text-sm text-blue-300">
          Scan running in background — fetching fundamentals for 500+ stocks.
          This takes 15–30 minutes. You can close this tab and come back.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6">
        {/* Scan history sidebar */}
        <div className="space-y-2">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
            Recent Scans
          </h2>
          {scansLoading && (
            <p className="text-sm text-zinc-600">Loading…</p>
          )}
          {!scansLoading && scans.length === 0 && (
            <p className="text-sm text-zinc-600">
              No scans yet. Hit &quot;Scan US Markets&quot; to start.
            </p>
          )}
          {scans.map((scan) => (
            <ScanHistoryItem
              key={scan.id}
              scan={scan}
              selected={selectedScanId === scan.id}
              onClick={() => setSelectedScanId(scan.id)}
            />
          ))}
        </div>

        {/* Results panel */}
        <div>
          {selectedScanId === null && (
            <div className="flex items-center justify-center h-64 text-zinc-600 text-sm">
              Select a scan or start a new one
            </div>
          )}
          {selectedScanId !== null && scanLoading && (
            <div className="flex items-center justify-center h-64 text-zinc-600 text-sm">
              Loading results…
            </div>
          )}
          {activeScan && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${STATUS_DOT[activeScan.status] ?? "bg-zinc-500"}`}
                />
                <span className="text-sm text-zinc-400 capitalize">
                  {activeScan.status}
                </span>
                {activeScan.status === "done" && (
                  <span className="text-sm text-zinc-500">
                    · {activeScan.results_count} stocks passing VI criteria
                    from {activeScan.total_scanned} scanned
                  </span>
                )}
              </div>

              {activeScan.status === "done" && activeScan.results && (
                <ResultsTable results={activeScan.results} />
              )}

              {(activeScan.status === "pending" ||
                activeScan.status === "running") && (
                <div className="flex items-center justify-center h-48 text-zinc-600 text-sm">
                  Scanning stocks… results will appear here when done
                </div>
              )}

              {activeScan.status === "failed" && (
                <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-sm text-red-300">
                  Scan failed. Check worker logs. Try starting a new scan.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
