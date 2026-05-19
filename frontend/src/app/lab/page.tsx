"use client";

import { useState } from "react";
import { labApi, type BacktestResult, type BacktestMetrics } from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtUSDT(n: number) {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function fmtPct(n: number) {
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}
function fmtDate(ms: number) {
  return new Date(ms).toLocaleDateString();
}

const STRATEGIES = ["rsi", "macd", "fibonacci", "bollinger", "elliott_wave", "combined"];
const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];
const TIMEFRAMES = ["15m", "1h", "4h", "1d"];
const MONTHS = [1, 3, 6, 12];

function stratLabel(s: string) {
  return s === "elliott_wave" ? "Elliott Wave" : s.charAt(0).toUpperCase() + s.slice(1);
}

// ── Equity curve SVG ──────────────────────────────────────────────────────────
function EquityCurve({ curve, times, initial }: { curve: number[]; times: number[]; initial: number }) {
  if (curve.length < 2) return null;
  const W = 800, H = 140;
  const PAD = { top: 8, right: 16, bottom: 24, left: 72 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const minV = Math.min(...curve);
  const maxV = Math.max(...curve);
  const pad = (maxV - minV) * 0.1 || maxV * 0.02;
  const minEq = minV - pad, maxEq = maxV + pad;
  const eqRange = maxEq - minEq;

  const cx = (i: number) => PAD.left + (i / (curve.length - 1)) * plotW;
  const cy = (v: number) => PAD.top + (1 - (v - minEq) / eqRange) * plotH;

  const line = curve.map((v, i) => `${i === 0 ? "M" : "L"}${cx(i).toFixed(1)},${cy(v).toFixed(1)}`).join(" ");
  const fill = line + ` L${cx(curve.length - 1).toFixed(1)},${(PAD.top + plotH).toFixed(1)} L${PAD.left},${(PAD.top + plotH).toFixed(1)} Z`;

  const profit = curve[curve.length - 1] >= initial;
  const color = profit ? "#34d399" : "#f87171";
  const fillColor = profit ? "rgba(52,211,153,0.07)" : "rgba(248,113,113,0.07)";

  const yTicks = [0, 0.5, 1].map((t) => ({
    y: PAD.top + (1 - t) * plotH,
    label: fmtUSDT(minEq + t * eqRange),
  }));

  const xTicks = [0, Math.floor(curve.length / 2), curve.length - 1].map((idx) => ({
    x: cx(idx),
    label: times[idx] ? fmtDate(times[idx]) : "",
  }));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      <path d={fill} fill={fillColor} />
      <path d={line} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      {yTicks.map((t) => (
        <g key={t.label}>
          <line x1={PAD.left - 4} y1={t.y} x2={PAD.left} y2={t.y} stroke="#3f3f46" strokeWidth="1" />
          <text x={PAD.left - 6} y={t.y + 3.5} textAnchor="end" fill="#71717a" fontSize="9">{t.label}</text>
        </g>
      ))}
      {xTicks.map((t) => (
        <g key={t.x}>
          <line x1={t.x} y1={PAD.top + plotH} x2={t.x} y2={PAD.top + plotH + 4} stroke="#3f3f46" strokeWidth="1" />
          <text x={t.x} y={H - 4} textAnchor="middle" fill="#71717a" fontSize="9">{t.label}</text>
        </g>
      ))}
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + plotH} stroke="#3f3f46" strokeWidth="1" />
      <line x1={PAD.left} y1={PAD.top + plotH} x2={PAD.left + plotW} y2={PAD.top + plotH} stroke="#3f3f46" strokeWidth="1" />
    </svg>
  );
}

// ── Metrics grid ──────────────────────────────────────────────────────────────
function MetricsGrid({ m, initial, final: finalBal }: { m: BacktestMetrics; initial: number; final: number }) {
  const pnlColor = m.total_pnl_usdt >= 0 ? "text-emerald-400" : "text-red-400";
  const wrColor = m.win_rate_pct >= 55 ? "text-emerald-400" : m.win_rate_pct >= 40 ? "text-amber-400" : "text-red-400";

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[
        { label: "Total Trades", value: m.total_trades.toString() },
        { label: "Win Rate", value: `${m.win_rate_pct.toFixed(1)}%`, cls: wrColor },
        { label: "Total P&L", value: fmtUSDT(m.total_pnl_usdt), cls: pnlColor },
        { label: "Return", value: fmtPct(m.total_pnl_pct), cls: pnlColor },
        { label: "Wins / Losses", value: `${m.wins} / ${m.losses}` },
        { label: "Max Drawdown", value: `${m.max_drawdown_pct.toFixed(2)}%`, cls: m.max_drawdown_pct > 20 ? "text-red-400" : "text-zinc-100" },
        { label: "Avg R:R", value: `${m.avg_rr.toFixed(2)}×` },
        { label: "Final Balance", value: fmtUSDT(finalBal) },
      ].map((item) => (
        <div key={item.label} className="rounded-lg border border-zinc-800 bg-zinc-900/30 px-3 py-3">
          <p className="text-xs text-zinc-500">{item.label}</p>
          <p className={`text-lg font-bold tabular-nums ${item.cls ?? "text-zinc-100"}`}>{item.value}</p>
        </div>
      ))}
    </div>
  );
}

// ── Trade table ───────────────────────────────────────────────────────────────
function TradeTable({ result }: { result: BacktestResult }) {
  const [show, setShow] = useState(false);
  if (result.trades.length === 0) return <p className="text-xs text-zinc-600">No trades generated.</p>;

  return (
    <div>
      <button
        onClick={() => setShow((v) => !v)}
        className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors mb-2"
      >
        {show ? "Hide" : "Show"} {result.trades.length} trades ▾
      </button>
      {show && (
        <div className="overflow-x-auto rounded-lg border border-zinc-800">
          <table className="w-full text-xs">
            <thead className="bg-zinc-900 text-zinc-500 uppercase tracking-wider">
              <tr>
                <th className="px-3 py-2 text-left">Side</th>
                <th className="px-3 py-2 text-right">Entry</th>
                <th className="px-3 py-2 text-right">Exit</th>
                <th className="px-3 py-2 text-right">P&L</th>
                <th className="px-3 py-2 text-center">Result</th>
                <th className="px-3 py-2 text-left">Reason</th>
                <th className="px-3 py-2 text-left">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {result.trades.map((t, i) => (
                <tr key={i} className="hover:bg-zinc-900/50">
                  <td className="px-3 py-2">
                    <span className={`font-semibold ${t.side === "long" ? "text-emerald-400" : "text-red-400"}`}>
                      {t.side.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-zinc-300">{t.entry_price.toFixed(2)}</td>
                  <td className="px-3 py-2 text-right font-mono text-zinc-300">{t.exit_price.toFixed(2)}</td>
                  <td className={`px-3 py-2 text-right font-mono font-semibold ${t.pnl_usdt >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {t.pnl_usdt >= 0 ? "+" : ""}{t.pnl_usdt.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${
                      t.outcome === "win" ? "bg-emerald-900 text-emerald-300" : "bg-red-900 text-red-300"
                    }`}>
                      {t.outcome}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-zinc-500">{t.close_reason.replace("_", " ")}</td>
                  <td className="px-3 py-2 text-zinc-600">{fmtDate(t.entry_time)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Settings panel ────────────────────────────────────────────────────────────
function Settings({
  symbol, setSymbol,
  timeframe, setTimeframe,
  months, setMonths,
  leverage, setLeverage,
  riskPct, setRiskPct,
}: {
  symbol: string; setSymbol: (v: string) => void;
  timeframe: string; setTimeframe: (v: string) => void;
  months: number; setMonths: (v: number) => void;
  leverage: number; setLeverage: (v: number) => void;
  riskPct: number; setRiskPct: (v: number) => void;
}) {
  const sel = "bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-emerald-600";
  return (
    <div className="flex flex-wrap gap-3 items-center">
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">Symbol</label>
        <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className={sel}>
          {SYMBOLS.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">Timeframe</label>
        <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className={sel}>
          {TIMEFRAMES.map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">History</label>
        <select value={months} onChange={(e) => setMonths(Number(e.target.value))} className={sel}>
          {MONTHS.map((m) => <option key={m} value={m}>{m} month{m > 1 ? "s" : ""}</option>)}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">Leverage</label>
        <select value={leverage} onChange={(e) => setLeverage(Number(e.target.value))} className={sel}>
          {[1, 2, 3, 5, 10].map((l) => <option key={l} value={l}>{l}×</option>)}
        </select>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-zinc-500">Risk / trade</label>
        <select value={riskPct} onChange={(e) => setRiskPct(Number(e.target.value))} className={sel}>
          {[0.005, 0.01, 0.02].map((r) => <option key={r} value={r}>{(r * 100).toFixed(1)}%</option>)}
        </select>
      </div>
    </div>
  );
}

// ── Tab: Backtest ─────────────────────────────────────────────────────────────
function BacktestTab() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [months, setMonths] = useState(3);
  const [strategy, setStrategy] = useState("combined");
  const [leverage, setLeverage] = useState(3);
  const [riskPct, setRiskPct] = useState(0.01);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await labApi.backtest({ symbol, timeframe, strategy, params: {}, months, initial_balance: 10_000, leverage, risk_pct: riskPct });
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const sel = "bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-emerald-600";

  return (
    <div className="space-y-5">
      <Settings symbol={symbol} setSymbol={setSymbol} timeframe={timeframe} setTimeframe={setTimeframe}
        months={months} setMonths={setMonths} leverage={leverage} setLeverage={setLeverage}
        riskPct={riskPct} setRiskPct={setRiskPct} />

      <div className="flex items-end gap-3 flex-wrap">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-500">Strategy</label>
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className={sel}>
            {STRATEGIES.map((s) => <option key={s} value={s}>{stratLabel(s)}</option>)}
          </select>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="px-4 py-1.5 text-sm font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-colors disabled:opacity-50"
        >
          {loading ? "Running…" : "▶ Run Backtest"}
        </button>
        {loading && (
          <p className="text-xs text-zinc-500">Fetching {months} months of {timeframe} candles…</p>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <p className="text-sm font-semibold text-zinc-300">
              {stratLabel(result.strategy)} · {result.symbol} · {result.timeframe} · {result.months}m
            </p>
            <p className={`text-sm font-bold ${result.metrics.total_pnl_usdt >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {fmtUSDT(result.metrics.total_pnl_usdt)} ({fmtPct(result.metrics.total_pnl_pct)})
            </p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-3">
            <EquityCurve curve={result.equity_curve} times={result.equity_times} initial={result.initial_balance} />
          </div>
          <MetricsGrid m={result.metrics} initial={result.initial_balance} final={result.final_balance} />
          <TradeTable result={result} />
        </div>
      )}
    </div>
  );
}

// ── Tab: Compare ──────────────────────────────────────────────────────────────
function CompareTab() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [months, setMonths] = useState(3);
  const [leverage, setLeverage] = useState(3);
  const [riskPct, setRiskPct] = useState(0.01);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const r = await labApi.compare({ symbol, timeframe, months, initial_balance: 10_000, leverage, risk_pct: riskPct });
      setResults(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <Settings symbol={symbol} setSymbol={setSymbol} timeframe={timeframe} setTimeframe={setTimeframe}
        months={months} setMonths={setMonths} leverage={leverage} setLeverage={setLeverage}
        riskPct={riskPct} setRiskPct={setRiskPct} />

      <button
        onClick={run}
        disabled={loading}
        className="px-4 py-1.5 text-sm font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-colors disabled:opacity-50"
      >
        {loading ? "Comparing all strategies…" : "▶ Compare All Strategies"}
      </button>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-950/30 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-xs text-zinc-500">{results[0].symbol} · {results[0].timeframe} · {results[0].months} months · sorted by P&L</p>
          <div className="overflow-x-auto rounded-lg border border-zinc-800">
            <table className="w-full text-sm">
              <thead className="bg-zinc-900 text-xs text-zinc-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 text-left">Strategy</th>
                  <th className="px-4 py-3 text-right">Trades</th>
                  <th className="px-4 py-3 text-right">Win Rate</th>
                  <th className="px-4 py-3 text-right">Total P&L</th>
                  <th className="px-4 py-3 text-right">Return</th>
                  <th className="px-4 py-3 text-right">Max DD</th>
                  <th className="px-4 py-3 text-right">Avg R:R</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {results.map((r, i) => {
                  const win = r.metrics.win_rate_pct;
                  const pnl = r.metrics.total_pnl_usdt;
                  return (
                    <tr key={r.strategy} className="hover:bg-zinc-900/50">
                      <td className="px-4 py-3 font-semibold text-zinc-200 flex items-center gap-2">
                        {i === 0 && <span className="text-amber-400 text-xs">🏆</span>}
                        {stratLabel(r.strategy)}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-400">{r.metrics.total_trades}</td>
                      <td className={`px-4 py-3 text-right font-semibold ${win >= 55 ? "text-emerald-400" : win >= 40 ? "text-amber-400" : "text-red-400"}`}>
                        {win.toFixed(1)}%
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-semibold ${pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {pnl >= 0 ? "+" : ""}{fmtUSDT(pnl)}
                      </td>
                      <td className={`px-4 py-3 text-right font-mono ${pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {fmtPct(r.metrics.total_pnl_pct)}
                      </td>
                      <td className={`px-4 py-3 text-right ${r.metrics.max_drawdown_pct > 20 ? "text-red-400" : "text-zinc-400"}`}>
                        {r.metrics.max_drawdown_pct.toFixed(1)}%
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-400">{r.metrics.avg_rr.toFixed(2)}×</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {results.map((r) => (
              <div key={r.strategy} className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-3">
                <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">{stratLabel(r.strategy)}</p>
                <EquityCurve curve={r.equity_curve} times={r.equity_times} initial={r.initial_balance} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tab: Pine Script ──────────────────────────────────────────────────────────
function PineScriptTab() {
  const [strategy, setStrategy] = useState("rsi");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function generate() {
    setLoading(true);
    try {
      const r = await labApi.pinescript(strategy, {});
      setCode(r.code);
    } finally {
      setLoading(false);
    }
  }

  function copy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const sel = "bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-emerald-600";

  return (
    <div className="space-y-4">
      <p className="text-sm text-zinc-500">
        Export any strategy to TradingView Pine Script v5. Paste the code directly into the Pine Script editor on TradingView.
      </p>

      <div className="flex items-end gap-3 flex-wrap">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-zinc-500">Strategy</label>
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className={sel}>
            {STRATEGIES.map((s) => <option key={s} value={s}>{stratLabel(s)}</option>)}
          </select>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="px-4 py-1.5 text-sm font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-colors disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate Pine Script"}
        </button>
      </div>

      {code && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-zinc-500">{stratLabel(strategy)} — Pine Script v5</p>
            <button
              onClick={copy}
              className="px-3 py-1 text-xs font-semibold bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded transition-colors"
            >
              {copied ? "Copied ✓" : "Copy"}
            </button>
          </div>
          <pre className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 text-xs text-zinc-300 overflow-x-auto font-mono leading-relaxed whitespace-pre">
            {code}
          </pre>
          <p className="text-xs text-zinc-600">
            Open TradingView → Pine Script Editor → New → paste this code → Add to chart
          </p>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function LabPage() {
  const [tab, setTab] = useState<"backtest" | "compare" | "pinescript">("backtest");

  const tabs = [
    { id: "backtest", label: "Backtest" },
    { id: "compare", label: "Compare Strategies" },
    { id: "pinescript", label: "Pine Script Export" },
  ] as const;

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Formula Lab</h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Backtest strategies on historical Binance data before trading live
        </p>
      </div>

      <div className="flex gap-1 border-b border-zinc-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.id
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div>
        {tab === "backtest" && <BacktestTab />}
        {tab === "compare" && <CompareTab />}
        {tab === "pinescript" && <PineScriptTab />}
      </div>
    </div>
  );
}
