"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { botApi, type BotStatus, type Portfolio, type Position, type Trade, type TradeStats, type PortfolioSnapshot, type StrategyStats } from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmt(n: number, decimals = 2) {
  return n.toFixed(decimals);
}
function fmtUSDT(n: number) {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function fmtPct(n: number) {
  return `${n.toFixed(2)}%`;
}
function fmtDate(s: string) {
  return new Date(s).toLocaleString();
}
function fmtTime(s: string) {
  return new Date(s).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const STRATEGIES = ["rsi", "macd", "fibonacci", "bollinger", "elliott_wave", "combined"] as const;

// ── Status banner ─────────────────────────────────────────────────────────────
function StatusBanner({ status }: { status: BotStatus }) {
  const qc = useQueryClient();
  const resume = useMutation({
    mutationFn: botApi.resume,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bot-status"] }),
  });
  const suspend = useMutation({
    mutationFn: botApi.suspend,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bot-status"] }),
  });

  if (status.is_suspended) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-red-400">Bot Suspended</p>
          {status.suspension_reason && (
            <p className="text-xs text-red-500 mt-0.5">{status.suspension_reason}</p>
          )}
        </div>
        <button
          onClick={() => resume.mutate()}
          disabled={resume.isPending}
          className="px-3 py-1.5 text-xs font-semibold bg-zinc-700 hover:bg-zinc-600 text-white rounded transition-colors disabled:opacity-50"
        >
          {resume.isPending ? "Resuming…" : "Resume Bot"}
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-emerald-800 bg-emerald-950/20 px-4 py-3 flex items-center gap-3">
      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
      <p className="text-sm text-emerald-400">
        Bot running — {status.active_strategy.toUpperCase()} strategy
        {status.is_stub && (
          <span className="ml-2 text-xs text-amber-400 bg-amber-900/30 border border-amber-800 px-1.5 py-0.5 rounded">
            STUB MODE — no Binance keys
          </span>
        )}
      </p>
      <span className="ml-auto text-xs text-zinc-500 uppercase tracking-wider mr-3">
        {status.trading_mode}
      </span>
      <button
        onClick={() => suspend.mutate()}
        disabled={suspend.isPending}
        className="px-3 py-1.5 text-xs font-semibold bg-zinc-800 hover:bg-red-900/60 border border-zinc-700 hover:border-red-800 text-zinc-400 hover:text-red-300 rounded transition-colors disabled:opacity-50"
      >
        {suspend.isPending ? "Pausing…" : "⏸ Pause"}
      </button>
    </div>
  );
}

// ── Strategy panel ────────────────────────────────────────────────────────────
function StrategyPanel({ status }: { status: BotStatus }) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState(status.active_strategy);
  const [saved, setSaved] = useState(false);

  const update = useMutation({
    mutationFn: (s: string) => botApi.updateConfig({ active_strategy: s }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bot-status"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const trigger = useMutation({
    mutationFn: botApi.trigger,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bot-positions"] }),
  });

  const isDirty = selected !== status.active_strategy;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-4 flex flex-wrap items-center gap-3">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Strategy</p>
      <select
        value={selected}
        onChange={(e) => { setSelected(e.target.value); setSaved(false); }}
        className="flex-1 min-w-[160px] bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-3 py-1.5 focus:outline-none focus:border-emerald-600"
      >
        {STRATEGIES.map((s) => (
          <option key={s} value={s}>
            {s === "elliott_wave" ? "Elliott Wave" : s.charAt(0).toUpperCase() + s.slice(1)}
          </option>
        ))}
      </select>
      <button
        onClick={() => update.mutate(selected)}
        disabled={!isDirty || update.isPending}
        className="px-3 py-1.5 text-xs font-semibold bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-colors disabled:opacity-40"
      >
        {saved ? "Saved ✓" : update.isPending ? "Saving…" : "Save"}
      </button>
      <div className="ml-auto">
        <button
          onClick={() => trigger.mutate()}
          disabled={trigger.isPending}
          className="px-3 py-1.5 text-xs font-semibold bg-zinc-700 hover:bg-zinc-600 text-zinc-100 rounded transition-colors disabled:opacity-50"
        >
          {trigger.isPending ? "Running…" : "▶ Run Now"}
        </button>
      </div>
    </div>
  );
}

// ── Equity curve (SVG) ────────────────────────────────────────────────────────
function EquityCurve({ snapshots }: { snapshots: PortfolioSnapshot[] }) {
  if (snapshots.length < 2) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-6 text-center text-sm text-zinc-600">
        Equity curve builds as the bot runs — check back after a few cycles
      </div>
    );
  }

  const W = 800;
  const H = 160;
  const PAD = { top: 10, right: 16, bottom: 28, left: 68 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;

  const equities = snapshots.map((s) => s.equity_usdt);
  const rawMin = Math.min(...equities);
  const rawMax = Math.max(...equities);
  const pad = (rawMax - rawMin) * 0.12 || rawMax * 0.02;
  const minEq = rawMin - pad;
  const maxEq = rawMax + pad;
  const eqRange = maxEq - minEq;

  const times = snapshots.map((s) => new Date(s.recorded_at).getTime());
  const minT = times[0];
  const maxT = times[times.length - 1];
  const tRange = maxT - minT || 1;

  const cx = (i: number) => PAD.left + ((times[i] - minT) / tRange) * plotW;
  const cy = (eq: number) => PAD.top + (1 - (eq - minEq) / eqRange) * plotH;

  const linePath = snapshots
    .map((s, i) => `${i === 0 ? "M" : "L"}${cx(i).toFixed(1)},${cy(s.equity_usdt).toFixed(1)}`)
    .join(" ");

  const fillPath =
    linePath +
    ` L${cx(snapshots.length - 1).toFixed(1)},${(PAD.top + plotH).toFixed(1)}` +
    ` L${PAD.left},${(PAD.top + plotH).toFixed(1)} Z`;

  const hwm = Math.max(...snapshots.map((s) => s.high_water_mark));
  const hwmY = cy(hwm);
  const killLevel = hwm * 0.9;
  const killY = cy(Math.max(killLevel, minEq));

  // Y axis ticks (3)
  const yTicks = [0, 0.5, 1].map((t) => ({
    y: PAD.top + (1 - t) * plotH,
    label: fmtUSDT(minEq + t * eqRange),
  }));

  // X axis ticks (up to 4)
  const xTickCount = Math.min(4, snapshots.length);
  const xTicks = Array.from({ length: xTickCount }, (_, i) => {
    const idx = Math.round((i / (xTickCount - 1)) * (snapshots.length - 1));
    return { x: cx(idx), label: fmtTime(snapshots[idx].recorded_at) };
  });

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-4">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
        Equity Curve ({snapshots.length} snapshots)
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        {/* Kill zone fill */}
        {killY < PAD.top + plotH && (
          <rect
            x={PAD.left}
            y={killY}
            width={plotW}
            height={PAD.top + plotH - killY}
            fill="rgba(220,38,38,0.08)"
          />
        )}

        {/* HWM dashed line */}
        {hwmY >= PAD.top && hwmY <= PAD.top + plotH && (
          <>
            <line
              x1={PAD.left}
              y1={hwmY}
              x2={PAD.left + plotW}
              y2={hwmY}
              stroke="#52525b"
              strokeDasharray="4 3"
              strokeWidth="1"
            />
            <text x={PAD.left + plotW - 2} y={hwmY - 3} textAnchor="end" fill="#71717a" fontSize="9">
              HWM
            </text>
          </>
        )}

        {/* Kill zone label */}
        {killY < PAD.top + plotH && killY >= PAD.top && (
          <text x={PAD.left + plotW - 2} y={killY - 3} textAnchor="end" fill="#f87171" fontSize="9">
            -10% kill
          </text>
        )}

        {/* Equity fill */}
        <path d={fillPath} fill="rgba(52,211,153,0.07)" />
        {/* Equity line */}
        <path d={linePath} fill="none" stroke="#34d399" strokeWidth="1.5" strokeLinejoin="round" />

        {/* Y axis ticks */}
        {yTicks.map((t) => (
          <g key={t.label}>
            <line x1={PAD.left - 4} y1={t.y} x2={PAD.left} y2={t.y} stroke="#3f3f46" strokeWidth="1" />
            <text x={PAD.left - 6} y={t.y + 3.5} textAnchor="end" fill="#71717a" fontSize="9">
              {t.label}
            </text>
          </g>
        ))}

        {/* X axis ticks */}
        {xTicks.map((t) => (
          <g key={t.x}>
            <line x1={t.x} y1={PAD.top + plotH} x2={t.x} y2={PAD.top + plotH + 4} stroke="#3f3f46" strokeWidth="1" />
            <text x={t.x} y={H - 4} textAnchor="middle" fill="#71717a" fontSize="9">
              {t.label}
            </text>
          </g>
        ))}

        {/* Axes */}
        <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + plotH} stroke="#3f3f46" strokeWidth="1" />
        <line x1={PAD.left} y1={PAD.top + plotH} x2={PAD.left + plotW} y2={PAD.top + plotH} stroke="#3f3f46" strokeWidth="1" />
      </svg>
    </div>
  );
}

// ── Portfolio card ────────────────────────────────────────────────────────────
function PortfolioCard({ portfolio }: { portfolio: Portfolio }) {
  const drawdownColor =
    portfolio.drawdown_pct > 8
      ? "text-red-400"
      : portfolio.drawdown_pct > 5
        ? "text-amber-400"
        : "text-emerald-400";

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-4 space-y-3">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Portfolio</p>
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Balance" value={fmtUSDT(portfolio.balance_usdt)} />
        <Stat label="Equity" value={fmtUSDT(portfolio.equity_usdt)} />
        <Stat label="High-Water Mark" value={fmtUSDT(portfolio.high_water_mark)} />
        <Stat label="Drawdown" value={fmtPct(portfolio.drawdown_pct)} valueClass={drawdownColor} />
      </div>
      <div>
        <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              portfolio.drawdown_pct > 8
                ? "bg-red-500"
                : portfolio.drawdown_pct > 5
                  ? "bg-amber-500"
                  : "bg-emerald-500"
            }`}
            style={{ width: `${Math.min(portfolio.drawdown_pct / 10, 1) * 100}%` }}
          />
        </div>
        <p className="text-xs text-zinc-600 mt-1">Kill switch triggers at 10% drawdown</p>
      </div>
    </div>
  );
}

// ── Stats card ────────────────────────────────────────────────────────────────
function StatsCard({ stats }: { stats: TradeStats }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-4 space-y-3">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Performance</p>
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Total Trades" value={stats.total_trades.toString()} />
        <Stat
          label="Win Rate"
          value={fmtPct(stats.win_rate_pct)}
          valueClass={stats.win_rate_pct >= 55 ? "text-emerald-400" : "text-zinc-300"}
        />
        <Stat
          label="Total P&L"
          value={fmtUSDT(stats.total_pnl_usdt)}
          valueClass={stats.total_pnl_usdt >= 0 ? "text-emerald-400" : "text-red-400"}
        />
        <Stat label="Avg R:R" value={fmt(stats.avg_rr) + "×"} />
      </div>
      {stats.total_trades > 0 && stats.total_trades < 100 && (
        <p className="text-xs text-amber-500">
          {100 - stats.total_trades} more trades needed before go-live check
        </p>
      )}
    </div>
  );
}

// ── Open positions ────────────────────────────────────────────────────────────
function PositionsTable({ positions }: { positions: Position[] }) {
  if (positions.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-6 text-center text-sm text-zinc-600">
        No open positions
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs text-zinc-500 uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3 text-left">Symbol</th>
            <th className="px-4 py-3 text-left">Side</th>
            <th className="px-4 py-3 text-right">Size</th>
            <th className="px-4 py-3 text-right">Entry</th>
            <th className="px-4 py-3 text-right">Now</th>
            <th className="px-4 py-3 text-right">Unreal. P&amp;L</th>
            <th className="px-4 py-3 text-right">Stop</th>
            <th className="px-4 py-3 text-right">Target</th>
            <th className="px-4 py-3 text-right">Lev</th>
            <th className="px-4 py-3 text-left">Strategy</th>
            <th className="px-4 py-3 text-left">Opened</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {positions.map((p) => (
            <tr key={p.id} className="hover:bg-zinc-900/50">
              <td className="px-4 py-3 font-mono font-bold text-emerald-400">{p.symbol}</td>
              <td className="px-4 py-3">
                <span
                  className={`px-2 py-0.5 rounded text-xs font-semibold ${
                    p.side === "long"
                      ? "bg-emerald-900 text-emerald-300"
                      : "bg-red-900 text-red-300"
                  }`}
                >
                  {p.side.toUpperCase()}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-mono">{p.size}</td>
              <td className="px-4 py-3 text-right font-mono text-zinc-300">{fmt(p.entry_price)}</td>
              <td className="px-4 py-3 text-right font-mono text-zinc-400">
                {p.current_price != null ? fmt(p.current_price) : "—"}
              </td>
              <td className={`px-4 py-3 text-right font-mono font-semibold ${
                p.unrealized_pnl == null
                  ? "text-zinc-600"
                  : p.unrealized_pnl >= 0
                    ? "text-emerald-400"
                    : "text-red-400"
              }`}>
                {p.unrealized_pnl == null
                  ? "—"
                  : `${p.unrealized_pnl >= 0 ? "+" : ""}${fmtUSDT(p.unrealized_pnl)}`}
              </td>
              <td className="px-4 py-3 text-right font-mono text-red-400">{fmt(p.stop_loss)}</td>
              <td className="px-4 py-3 text-right font-mono text-emerald-400">{fmt(p.take_profit)}</td>
              <td className="px-4 py-3 text-right text-zinc-400">{p.leverage}×</td>
              <td className="px-4 py-3 text-zinc-400 uppercase text-xs">{p.strategy}</td>
              <td className="px-4 py-3 text-zinc-500 text-xs">{fmtDate(p.opened_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Strategy breakdown ────────────────────────────────────────────────────────
function StrategyBreakdown({ rows }: { rows: StrategyStats[] }) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-6 text-center text-sm text-zinc-600">
        No trades yet — breakdown appears after first closed trade
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs text-zinc-500 uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3 text-left">Strategy</th>
            <th className="px-4 py-3 text-right">Trades</th>
            <th className="px-4 py-3 text-right">W / L</th>
            <th className="px-4 py-3 text-right">Win Rate</th>
            <th className="px-4 py-3 text-right">Total P&amp;L</th>
            <th className="px-4 py-3 text-right">Avg P&amp;L</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {rows.map((r) => (
            <tr key={r.strategy} className="hover:bg-zinc-900/50">
              <td className="px-4 py-3 font-semibold text-zinc-200 uppercase text-xs tracking-wide">
                {r.strategy.replace("_", " ")}
              </td>
              <td className="px-4 py-3 text-right text-zinc-400">{r.total_trades}</td>
              <td className="px-4 py-3 text-right font-mono text-xs">
                <span className="text-emerald-400">{r.wins}</span>
                <span className="text-zinc-600"> / </span>
                <span className="text-red-400">{r.losses}</span>
              </td>
              <td className={`px-4 py-3 text-right font-semibold ${
                r.win_rate_pct >= 55 ? "text-emerald-400" : r.win_rate_pct >= 45 ? "text-amber-400" : "text-red-400"
              }`}>
                {fmtPct(r.win_rate_pct)}
              </td>
              <td className={`px-4 py-3 text-right font-mono font-semibold ${
                r.total_pnl_usdt >= 0 ? "text-emerald-400" : "text-red-400"
              }`}>
                {r.total_pnl_usdt >= 0 ? "+" : ""}{fmtUSDT(r.total_pnl_usdt)}
              </td>
              <td className={`px-4 py-3 text-right font-mono ${
                r.avg_pnl_usdt >= 0 ? "text-emerald-400" : "text-red-400"
              }`}>
                {r.avg_pnl_usdt >= 0 ? "+" : ""}{fmtUSDT(r.avg_pnl_usdt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Trade history ─────────────────────────────────────────────────────────────
function TradeHistory({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-6 text-center text-sm text-zinc-600">
        No completed trades yet
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900 text-xs text-zinc-500 uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3 text-left">Symbol</th>
            <th className="px-4 py-3 text-left">Side</th>
            <th className="px-4 py-3 text-right">P&amp;L</th>
            <th className="px-4 py-3 text-right">P&amp;L %</th>
            <th className="px-4 py-3 text-center">Outcome</th>
            <th className="px-4 py-3 text-left">Close Reason</th>
            <th className="px-4 py-3 text-left">Closed</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {trades.map((t) => (
            <tr key={t.id} className="hover:bg-zinc-900/50">
              <td className="px-4 py-3 font-mono font-bold text-zinc-200">{t.symbol}</td>
              <td className="px-4 py-3">
                <span
                  className={`text-xs font-semibold ${
                    t.side === "long" ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {t.side.toUpperCase()}
                </span>
              </td>
              <td
                className={`px-4 py-3 text-right font-mono font-semibold ${
                  t.pnl_usdt >= 0 ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {t.pnl_usdt >= 0 ? "+" : ""}
                {fmtUSDT(t.pnl_usdt)}
              </td>
              <td
                className={`px-4 py-3 text-right font-mono ${
                  t.pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {t.pnl_pct >= 0 ? "+" : ""}
                {fmtPct(t.pnl_pct)}
              </td>
              <td className="px-4 py-3 text-center">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                    t.outcome === "win"
                      ? "bg-emerald-900 text-emerald-300"
                      : t.outcome === "loss"
                        ? "bg-red-900 text-red-300"
                        : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  {t.outcome}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-zinc-500">{t.close_reason.replace("_", " ")}</td>
              <td className="px-4 py-3 text-xs text-zinc-500">{fmtDate(t.closed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Stat component ────────────────────────────────────────────────────────────
function Stat({
  label,
  value,
  valueClass = "text-zinc-100",
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div>
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`text-lg font-bold tabular-nums ${valueClass}`}>{value}</p>
    </div>
  );
}

// ── Go-live checklist ─────────────────────────────────────────────────────────
function GoLiveChecklist({ stats, portfolio }: { stats: TradeStats; portfolio: Portfolio }) {
  const checks = [
    {
      label: "Win rate > 55% (100+ trades)",
      done: stats.total_trades >= 100 && stats.win_rate_pct > 55,
      note: `${stats.total_trades} trades, ${fmtPct(stats.win_rate_pct)} win rate`,
    },
    {
      label: "Max drawdown stayed < 8%",
      done: portfolio.drawdown_pct < 8,
      note: `Current: ${fmtPct(portfolio.drawdown_pct)}`,
    },
    {
      label: "Positive total P&L",
      done: stats.total_pnl_usdt > 0,
      note: fmtUSDT(stats.total_pnl_usdt),
    },
    {
      label: "Avg R:R ≥ 2×",
      done: stats.avg_rr >= 2,
      note: `Current: ${fmt(stats.avg_rr)}×`,
    },
  ];

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/20 p-4 space-y-2">
      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Go-Live Checklist</p>
      {checks.map((c) => (
        <div key={c.label} className="flex items-start gap-2 text-sm">
          <span className={c.done ? "text-emerald-400" : "text-zinc-600"}>{c.done ? "✓" : "○"}</span>
          <span className={c.done ? "text-zinc-300" : "text-zinc-500"}>{c.label}</span>
          <span className="ml-auto text-xs text-zinc-600">{c.note}</span>
        </div>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function BotPage() {
  const { data: status } = useQuery({
    queryKey: ["bot-status"],
    queryFn: botApi.getStatus,
    refetchInterval: 10_000,
  });

  const { data: portfolio } = useQuery({
    queryKey: ["bot-portfolio"],
    queryFn: botApi.getPortfolio,
    refetchInterval: 30_000,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["bot-portfolio-history"],
    queryFn: () => botApi.getPortfolioHistory(288),
    refetchInterval: 60_000,
  });

  const { data: positions = [] } = useQuery({
    queryKey: ["bot-positions"],
    queryFn: botApi.getPositions,
    refetchInterval: 15_000,
  });

  const { data: trades = [] } = useQuery({
    queryKey: ["bot-trades"],
    queryFn: () => botApi.getTrades(50),
    refetchInterval: 30_000,
  });

  const { data: stats } = useQuery({
    queryKey: ["bot-stats"],
    queryFn: botApi.getStats,
    refetchInterval: 30_000,
  });

  const { data: strategyStats = [] } = useQuery({
    queryKey: ["bot-stats-by-strategy"],
    queryFn: botApi.getStatsByStrategy,
    refetchInterval: 60_000,
  });

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Trading Bot</h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Binance Futures · {status?.trading_mode ?? "testnet"} · {status?.active_strategy?.toUpperCase() ?? "—"} strategy
        </p>
      </div>

      {status && <StatusBanner status={status} />}
      {status && <StrategyPanel status={status} />}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {portfolio && <PortfolioCard portfolio={portfolio} />}
        {stats && <StatsCard stats={stats} />}
      </div>

      <EquityCurve snapshots={history} />

      <div>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
          Open Positions ({positions.length} / 3)
        </h2>
        <PositionsTable positions={positions} />
      </div>

      <div>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
          Strategy Breakdown
        </h2>
        <StrategyBreakdown rows={strategyStats} />
      </div>

      <div>
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-2">
          Trade History
        </h2>
        <TradeHistory trades={trades} />
      </div>

      {portfolio && stats && <GoLiveChecklist stats={stats} portfolio={portfolio} />}
    </div>
  );
}
