"use client";

import { use } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { viApi, type ScanResult, type VIMetrics } from "@/lib/api";

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

// ── Criterion config ─────────────────────────────────────────────────────────
interface Criterion {
  label: string;
  key: keyof VIMetrics;
  points: number;
  threshold: string;
  pass: (v: number) => boolean;
  format: (v: number) => string;
}

const CRITERIA: Criterion[] = [
  {
    label: "P/E Ratio",
    key: "pe_ratio",
    points: 15,
    threshold: "0 < P/E < 15",
    pass: (v) => v > 0 && v < 15,
    format: (v) => v.toFixed(1) + "×",
  },
  {
    label: "P/B Ratio",
    key: "pb_ratio",
    points: 15,
    threshold: "< 1.5",
    pass: (v) => v < 1.5,
    format: (v) => v.toFixed(2) + "×",
  },
  {
    label: "Debt / Equity",
    key: "debt_to_equity",
    points: 15,
    threshold: "< 50 (i.e. < 0.5 ratio)",
    pass: (v) => v < 50,
    format: (v) => (v / 100).toFixed(2),
  },
  {
    label: "Return on Equity",
    key: "roe",
    points: 15,
    threshold: "> 15%",
    pass: (v) => v > 0.15,
    format: (v) => (v * 100).toFixed(1) + "%",
  },
  {
    label: "Revenue Growth",
    key: "revenue_growth",
    points: 15,
    threshold: "> 10% YoY",
    pass: (v) => v > 0.1,
    format: (v) => (v * 100).toFixed(1) + "%",
  },
  {
    label: "Free Cash Flow",
    key: "free_cash_flow",
    points: 15,
    threshold: "Positive",
    pass: (v) => v > 0,
    format: (v) => {
      if (v >= 1e9) return "$" + (v / 1e9).toFixed(1) + "B";
      return "$" + (v / 1e6).toFixed(0) + "M";
    },
  },
  {
    label: "Insider Ownership",
    key: "insider_ownership",
    points: 10,
    threshold: "> 5%",
    pass: (v) => v > 0.05,
    format: (v) => (v * 100).toFixed(2) + "%",
  },
];

// ── Score ring ────────────────────────────────────────────────────────────────
function ScoreRing({ score, verdict }: { score: number; verdict: string }) {
  const color =
    verdict === "strong_buy"
      ? "text-emerald-400"
      : verdict === "buy"
        ? "text-blue-400"
        : verdict === "hold"
          ? "text-amber-400"
          : "text-red-400";

  return (
    <div className="flex flex-col items-center gap-1">
      <span className={`text-6xl font-bold tabular-nums ${color}`}>{score}</span>
      <span className="text-sm text-zinc-500">out of 100</span>
      <span
        className={`mt-1 px-3 py-0.5 text-sm font-semibold rounded-full ${VERDICT_STYLES[verdict] ?? "bg-zinc-800 text-zinc-400"}`}
      >
        {VERDICT_LABELS[verdict] ?? verdict}
      </span>
    </div>
  );
}

// ── Criterion row ─────────────────────────────────────────────────────────────
function CriterionRow({ c, metrics }: { c: Criterion; metrics: VIMetrics }) {
  const raw = metrics[c.key] as number | null;
  const hasData = raw !== null && raw !== undefined;
  const passed = hasData ? c.pass(raw!) : null;

  return (
    <tr className="border-t border-zinc-800">
      <td className="px-4 py-3 text-sm text-zinc-300 font-medium">{c.label}</td>
      <td className="px-4 py-3 text-sm text-center">
        {passed === null ? (
          <span className="text-zinc-600">—</span>
        ) : passed ? (
          <span className="text-emerald-400 font-bold">✓</span>
        ) : (
          <span className="text-red-400 font-bold">✗</span>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-right font-mono text-zinc-300">
        {hasData ? c.format(raw!) : <span className="text-zinc-600">N/A</span>}
      </td>
      <td className="px-4 py-3 text-sm text-right text-zinc-500">{c.threshold}</td>
      <td className="px-4 py-3 text-sm text-right text-zinc-600">{c.points} pts</td>
    </tr>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function StockDetailPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = use(params);
  const upperTicker = ticker.toUpperCase();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["vi-stock", upperTicker],
    queryFn: () => viApi.getStock(upperTicker),
  });

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link
          href="/vi"
          className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          ← VI Scanner
        </Link>
      </div>

      {isLoading && (
        <p className="text-zinc-600 text-sm">Loading {upperTicker}…</p>
      )}

      {isError && (
        <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-sm text-red-300">
          No scan data for {upperTicker}. Run a scan first.
        </div>
      )}

      {data && (
        <>
          {/* Header */}
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">{data.company_name}</h1>
              <p className="text-zinc-500 font-mono mt-0.5">{data.ticker}</p>
            </div>
            <ScoreRing score={data.vi_score} verdict={data.verdict} />
          </div>

          {/* Criterion breakdown */}
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <div className="px-4 py-3 bg-zinc-900 border-b border-zinc-800">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                Criterion Breakdown
              </h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-zinc-900/50">
                <tr className="text-xs text-zinc-600 uppercase tracking-wider">
                  <th className="px-4 py-2 text-left">Metric</th>
                  <th className="px-4 py-2 text-center">Pass</th>
                  <th className="px-4 py-2 text-right">Value</th>
                  <th className="px-4 py-2 text-right">Threshold</th>
                  <th className="px-4 py-2 text-right">Weight</th>
                </tr>
              </thead>
              <tbody>
                {CRITERIA.map((c) => (
                  <CriterionRow key={c.key} c={c} metrics={data.metrics} />
                ))}
              </tbody>
            </table>

            {/* Hidden gem check */}
            <div className="px-4 py-3 border-t border-zinc-800 bg-zinc-900/30">
              {data.metrics.market_cap !== null &&
              data.metrics.market_cap < 2_000_000_000 &&
              (data.metrics.analyst_count === null ||
                data.metrics.analyst_count < 5) ? (
                <p className="text-sm text-emerald-400">
                  ✦ Hidden gem bonus applied (+5 pts) — small-cap, underfollowed
                </p>
              ) : (
                <p className="text-sm text-zinc-600">
                  No hidden gem bonus — market cap ≥ $2B or analyst coverage ≥ 5 firms
                </p>
              )}
            </div>
          </div>

          {/* Additional info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 px-4 py-4 space-y-2">
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">
                Market Data
              </p>
              <Row
                label="Market Cap"
                value={
                  data.metrics.market_cap
                    ? formatMarketCap(data.metrics.market_cap)
                    : "N/A"
                }
              />
              <Row
                label="Analyst Coverage"
                value={
                  data.metrics.analyst_count !== null
                    ? `${data.metrics.analyst_count} firms`
                    : "N/A"
                }
              />
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 px-4 py-4 space-y-2">
              <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">
                VI Score Meaning
              </p>
              <Row label="≥ 75" value="Strong Buy" />
              <Row label="≥ 55" value="Buy" />
              <Row label="≥ 35" value="Hold" />
              <Row label="< 35" value="Skip" />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="text-zinc-300">{value}</span>
    </div>
  );
}

function formatMarketCap(v: number): string {
  if (v >= 1e12) return `$${(v / 1e12).toFixed(1)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  return `$${(v / 1e6).toFixed(0)}M`;
}
