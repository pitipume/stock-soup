"""
Walk-forward backtesting engine.

Fetches historical OHLCV from Binance public API, then simulates each strategy
candle-by-candle. SL/TP are checked using each candle's high/low so exits are
realistic — we don't assume we close at the exact close price.

Why public API for historical data: the testnet does not have years of history.
Binance public klines require no authentication.
"""
import httpx
from datetime import datetime, timezone, timedelta
from typing import Any

from app.modules.lab.schemas import BacktestResult, BacktestMetrics, BacktestTrade

_BINANCE_BASE = "https://fapi.binance.com"
_MIN_CANDLES = 250  # enough for EMA-200 used by MACD / Elliott Wave
_MAX_CONCURRENT = 3
_STRATEGIES = ["rsi", "macd", "fibonacci", "bollinger", "elliott_wave", "combined", "triple_ema_stoch_rsi", "three_golden", "supertrend", "time_series_momentum"]


async def fetch_candles(symbol: str, interval: str, months: int) -> list[dict]:
    """Fetch historical candles from Binance public futures API."""
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)

    candles: list[dict] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        current = start_ms
        while current < end_ms:
            resp = await client.get(
                f"{_BINANCE_BASE}/fapi/v1/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current,
                    "endTime": end_ms,
                    "limit": 1500,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            for r in data:
                candles.append({
                    "open_time": int(r[0]),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": float(r[5]),
                })
            if len(data) < 1500:
                break
            current = int(data[-1][0]) + 1

    return candles


def _get_signal(candles: list[dict], strategy: str, params: dict):
    if strategy == "rsi":
        from app.modules.bot.strategies.rsi import evaluate
        return evaluate(candles, params)
    elif strategy == "macd":
        from app.modules.bot.strategies.macd import evaluate
        return evaluate(candles, params)
    elif strategy == "fibonacci":
        from app.modules.bot.strategies.fibonacci import evaluate
        return evaluate(candles, params)
    elif strategy == "bollinger":
        from app.modules.bot.strategies.bollinger import evaluate
        return evaluate(candles, params)
    elif strategy == "elliott_wave":
        from app.modules.bot.strategies.elliott_wave import evaluate
        return evaluate(candles, params)
    elif strategy == "combined":
        from app.modules.bot.strategies.combined import evaluate
        # Use equal weights in backtest — no live trade history available
        merged = {
            "rsi_weight": 0.5,
            "macd_weight": 0.5,
            "fibonacci_weight": 0.5,
            "bollinger_weight": 0.5,
            "elliott_wave_weight": 0.5,
            **params,
        }
        return evaluate(candles, merged)
    elif strategy == "triple_ema_stoch_rsi":
        from app.modules.bot.strategies.triple_ema_stoch_rsi import evaluate
        return evaluate(candles, params)
    elif strategy == "three_golden":
        from app.modules.bot.strategies.three_golden import evaluate
        return evaluate(candles, params)
    elif strategy == "supertrend":
        from app.modules.bot.strategies.supertrend import evaluate
        return evaluate(candles, params)
    elif strategy == "time_series_momentum":
        from app.modules.bot.strategies.time_series_momentum import evaluate
        return evaluate(candles, params)
    return None


def _unrealized(pos: dict, price: float, leverage: int) -> float:
    if pos["side"] == "long":
        return (price - pos["entry_price"]) * pos["size"] * leverage
    return (pos["entry_price"] - price) * pos["size"] * leverage


def _close_position(pos: dict, exit_price: float, exit_time: int, leverage: int, close_reason: str) -> tuple[float, BacktestTrade]:
    """Shared close accounting so SL/TP, signal-reversal, and end-of-backtest exits compute pnl identically."""
    if pos["side"] == "long":
        pnl = (exit_price - pos["entry_price"]) * pos["size"] * leverage
    else:
        pnl = (pos["entry_price"] - exit_price) * pos["size"] * leverage
    pnl_pct = pnl / (pos["entry_price"] * pos["size"]) * 100
    trade = BacktestTrade(
        side=pos["side"],
        entry_price=round(pos["entry_price"], 4),
        exit_price=round(exit_price, 4),
        stop_loss=round(pos["stop_loss"], 4),
        pnl_usdt=round(pnl, 4),
        pnl_pct=round(pnl_pct, 4),
        outcome="win" if pnl > 0 else ("loss" if pnl < 0 else "breakeven"),
        close_reason=close_reason,
        entry_time=pos["entry_time"],
        exit_time=exit_time,
    )
    return pnl, trade


def run_backtest(
    candles: list[dict],
    symbol: str,
    strategy: str,
    params: dict,
    initial_balance: float,
    leverage: int,
    risk_pct: float,
    timeframe: str,
    months: int,
    close_on_reversal: bool = False,
) -> BacktestResult:
    """
    close_on_reversal (default False, OPT-IN ONLY): when True, an open position
    is closed at the current candle's close price the moment the strategy emits
    a signal in the opposite direction, instead of only ever exiting via SL/TP/
    end-of-backtest. This resolves the "positions stack up because the harness
    never proactively closes on a fresh opposite signal" limitation documented
    in time_series_momentum.py and docs/backtest-log.md (2026-08-17 overnight
    entries).

    Deliberately NOT the default: every one of the other 9 strategies' results
    logged in docs/backtest-log.md was produced without this behavior, and
    changing the default would silently invalidate that entire evidence trail.
    Both existing callers (run_lab_backtest, run_lab_compare in
    backend/app/tasks/lab_tasks.py) call this positionally/by-keyword without
    this argument, so they are unaffected and continue to reproduce prior
    results byte-for-byte. This flag is for ad hoc validation runs only, until/
    unless Poom decides it should become a real per-strategy option in the API.
    """
    balance = initial_balance
    open_positions: list[dict] = []
    trades: list[BacktestTrade] = []
    equity_curve: list[float] = [initial_balance]
    equity_times: list[int] = [candles[_MIN_CANDLES]["open_time"]]
    peak = initial_balance
    max_dd = 0.0

    for i in range(_MIN_CANDLES, len(candles)):
        candle = candles[i]
        high = candle["high"]
        low = candle["low"]
        close = candle["close"]
        ts = candle["open_time"]

        # ── Check SL / TP on open positions ───────────────────────────────────
        still_open = []
        closed_this_candle = False
        for pos in open_positions:
            if pos["side"] == "long":
                sl_hit = low <= pos["stop_loss"]
                tp_hit = high >= pos["take_profit"]
            else:
                sl_hit = high >= pos["stop_loss"]
                tp_hit = low <= pos["take_profit"]

            if sl_hit or tp_hit:
                # If both hit same candle, take the worse outcome (SL)
                exit_price = pos["stop_loss"] if sl_hit else pos["take_profit"]
                close_reason = "stop_loss" if sl_hit else "take_profit"
                pnl, trade = _close_position(pos, exit_price, ts, leverage, close_reason)
                balance += pnl
                trades.append(trade)
                closed_this_candle = True
            else:
                still_open.append(pos)

        open_positions = still_open

        # ── Optional: close on signal reversal (opt-in only, see docstring) ───
        cached_signal = None
        if close_on_reversal and open_positions and balance > 0:
            cached_signal = _get_signal(candles[: i + 1], strategy, params)
            if cached_signal and cached_signal.action != "none":
                still_open2 = []
                for pos in open_positions:
                    if pos["side"] != cached_signal.action:
                        pnl, trade = _close_position(pos, close, ts, leverage, "signal_reversal")
                        balance += pnl
                        trades.append(trade)
                        closed_this_candle = True
                    else:
                        still_open2.append(pos)
                open_positions = still_open2

        # ── Equity snapshot after any close ───────────────────────────────────
        if closed_this_candle or i % 24 == 0:
            unreal = sum(_unrealized(p, close, leverage) for p in open_positions)
            equity = balance + unreal
            equity_curve.append(round(equity, 2))
            equity_times.append(ts)
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        # ── Get strategy signal ───────────────────────────────────────────────
        if len(open_positions) < _MAX_CONCURRENT and balance > 0:
            if close_on_reversal:
                # Reuse the signal already computed above for the reversal check
                # (when positions were open) to avoid a second, potentially
                # inconsistent evaluate() call on the same candle.
                signal = cached_signal if cached_signal is not None else _get_signal(candles[: i + 1], strategy, params)
            else:
                signal = _get_signal(candles[: i + 1], strategy, params)
            if signal and signal.action != "none":
                stop_dist = abs(signal.entry_price - signal.stop_loss)
                if stop_dist > 0:
                    risk_amt = balance * risk_pct
                    size = risk_amt / (stop_dist * leverage)
                    if size > 0:
                        open_positions.append({
                            "side": signal.action,
                            "entry_price": close,
                            "stop_loss": signal.stop_loss,
                            "take_profit": signal.take_profit,
                            "size": size,
                            "entry_time": ts,
                        })

    # ── Close remaining positions at last candle ──────────────────────────────
    last_close = candles[-1]["close"]
    last_ts = candles[-1]["open_time"]
    for pos in open_positions:
        pnl, trade = _close_position(pos, last_close, last_ts, leverage, "end_of_backtest")
        balance += pnl
        trades.append(trade)

    equity_curve.append(round(balance, 2))
    equity_times.append(last_ts)

    # ── Metrics ───────────────────────────────────────────────────────────────
    wins = [t for t in trades if t.outcome == "win"]
    losses = [t for t in trades if t.outcome == "loss"]
    n = len(trades)
    win_rate = round(len(wins) / n * 100, 2) if n else 0.0
    total_pnl = round(balance - initial_balance, 2)
    total_pnl_pct = round(total_pnl / initial_balance * 100, 2)

    rr_vals = []
    for t in trades:
        # Use the position's actual stop-loss distance (real risk taken), not a flat 2% guess.
        # A hardcoded 2% here was inconsistent with position sizing above, which already uses
        # the real stop_dist = abs(signal.entry_price - signal.stop_loss) per trade.
        risk = abs(t.entry_price - t.stop_loss)
        reward = abs(t.exit_price - t.entry_price)
        if risk > 0:
            rr_vals.append(reward / risk)
    avg_rr = round(sum(rr_vals) / len(rr_vals), 2) if rr_vals else 0.0

    metrics = BacktestMetrics(
        total_trades=n,
        wins=len(wins),
        losses=len(losses),
        win_rate_pct=win_rate,
        total_pnl_usdt=total_pnl,
        total_pnl_pct=total_pnl_pct,
        max_drawdown_pct=round(max_dd, 2),
        avg_rr=avg_rr,
    )

    return BacktestResult(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        months=months,
        initial_balance=initial_balance,
        final_balance=round(balance, 2),
        metrics=metrics,
        trades=trades,
        equity_curve=equity_curve,
        equity_times=equity_times,
    )
