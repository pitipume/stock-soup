"""
Time-Series Momentum strategy.

Academically-grounded trend-following: unlike this codebase's other strategies,
which react to single-candle indicator crossovers on 15m/1h/4h bars, this
strategy asks a much lower-frequency question -- has this asset trended up or
down over the trailing lookback window? -- and only rebalances periodically.
That low frequency is deliberate: it's designed to filter out the candle-to-
candle noise that sank every other strategy in the 2026-08-17 5-year
validation (see docs/backtest-log.md). Grounded in peer-reviewed research on
crypto time-series momentum (see docs/execution-log.md, 2026-08-17 entry).

Requires daily ("1d") candles -- a 90-day lookback computed on 15m/1h/4h
candles would need thousands of bars and defeats the entire point.

Signal logic:
  On each rebalance boundary (every `rebalance_days` candles):
    trailing_return = (close[today] / close[today - lookback_days]) - 1
    trailing_return > 0  -> LONG
    trailing_return < 0  -> SHORT
  Between rebalance boundaries: no signal. This strategy does deliberately NOT
  re-evaluate every candle the way the others do.

Adaptation note (read before trusting results at face value): this codebase's
shared backtester/executor only closes a position on stop-loss or take-profit,
not on "the strategy's signal changed." A textbook TSMOM implementation flips
a single position on every rebalance; that isn't available here without a
larger shared change to run_backtest/executor. As a result: the stop-loss is
set wide (multi-day ATR-based) so a position typically survives to the next
rebalance, and take-profit is set very far away so it almost never triggers --
the position is meant to exit mainly via stop-loss (trend invalidation) or by
simply riding until the backtest/cycle ends, matching "let winners run." This
is an approximation of pure TSMOM within existing infrastructure, not a 1:1
academic replication. Also note: since rebalances only open NEW positions
(the harness never proactively closes an old one on a fresh opposite signal),
multiple same-direction or overlapping positions can accumulate up to the
platform's max-concurrent-positions limit before earlier ones are stopped out.

Stop loss:   entry -+ (atr_multiplier x ATR(atr_period)) on daily candles.
Take profit: entry -+ (tp_atr_multiplier x ATR(atr_period)) -- deliberately far
             (default 8x ATR vs a 3x ATR stop) so exits are dominated by trend
             invalidation, not an early profit cap.
"""
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    trailing_return_pct: float
    reason: str


def compute_atr(candles: list[dict], period: int = 14) -> float:
    """Average True Range on whatever timeframe `candles` are in (expects daily)."""
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        prev_close = candles[i - 1]["close"]
        high = candles[i]["high"]
        low = candles[i]["low"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs[-period:]) / min(len(trs), period)


def evaluate(candles: list[dict], params: Optional[dict] = None) -> Signal:
    """
    Given a list of daily OHLCV candles (newest last), return a trading signal.
    Intended timeframe: "1d". A shorter timeframe will not error, but defeats
    the low-frequency design this was validated for.

    params keys (all optional):
      lookback_days      int   = 90   (trailing return window)
      rebalance_days      int   = 7    (only emit an actionable signal every N candles)
      atr_period          int   = 14
      atr_multiplier       float = 3.0  (stop distance = atr * multiplier)
      tp_atr_multiplier    float = 8.0  (take-profit distance -- deliberately wide)
    """
    p = params or {}
    lookback_days = int(p.get("lookback_days", 90))
    rebalance_days = int(p.get("rebalance_days", 7))
    atr_period = int(p.get("atr_period", 14))
    atr_multiplier = float(p.get("atr_multiplier", 3.0))
    tp_atr_multiplier = float(p.get("tp_atr_multiplier", 8.0))

    n = len(candles)
    if n < lookback_days + 2:
        return Signal("none", 0, 0, 0, 0.0, "not enough candles for lookback window")

    # Only act on rebalance boundaries -- this is what keeps this strategy
    # low-frequency instead of firing every candle like the others.
    if (n - 1) % rebalance_days != 0:
        return Signal("none", candles[-1]["close"], 0, 0, 0.0, "not a rebalance day")

    closes = [c["close"] for c in candles]
    entry = closes[-1]
    past_price = closes[-1 - lookback_days]

    if past_price <= 0:
        return Signal("none", entry, 0, 0, 0.0, "invalid historical price")

    trailing_return = (entry / past_price) - 1.0
    atr = compute_atr(candles, atr_period)

    if atr <= 0:
        return Signal("none", entry, 0, 0, round(trailing_return * 100, 2), "ATR is zero")

    stop_distance = atr * atr_multiplier
    tp_distance = atr * tp_atr_multiplier

    if trailing_return > 0:
        stop_loss = entry - stop_distance
        take_profit = entry + tp_distance
        return Signal(
            action="long",
            entry_price=entry,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            trailing_return_pct=round(trailing_return * 100, 2),
            reason=f"{lookback_days}d trailing return {trailing_return * 100:+.1f}% > 0 -> long",
        )
    elif trailing_return < 0:
        stop_loss = entry + stop_distance
        take_profit = entry - tp_distance
        return Signal(
            action="short",
            entry_price=entry,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            trailing_return_pct=round(trailing_return * 100, 2),
            reason=f"{lookback_days}d trailing return {trailing_return * 100:+.1f}% < 0 -> short",
        )
    else:
        return Signal("none", entry, 0, 0, 0.0, "trailing return exactly zero -- no signal")
