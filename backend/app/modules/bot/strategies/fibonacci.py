"""
Fibonacci Retracement strategy.

Signal logic:
  1. Find the most recent significant swing high and swing low within a lookback window.
  2. Determine trend direction:
       swing_high came AFTER swing_low  → uptrend  (price rallied, now pulling back)
       swing_low  came AFTER swing_high → downtrend (price fell, now bouncing)
  3. Uptrend retracement → LONG:
       Price pulls back to a key Fib level (38.2%, 50%, 61.8% from swing_low to swing_high).
       Stop: just below the level (level - stop_buffer).  Breaking below invalidates the setup.
       Target: 2× risk above entry (toward the swing high).
  4. Downtrend retracement → SHORT:
       Price bounces up to a key Fib level (38.2%, 50%, 61.8% from swing_high to swing_low).
       Stop: just above the level (level + stop_buffer).
       Target: 2× risk below entry (toward the swing low).

Why these levels?
  38.2% = 1 - 0.618.  Shallow retracement — strong trend.
  50.0% = midpoint.   Widely watched, psychologically significant.
  61.8% = golden ratio. Deepest common retracement before trend is considered broken.

Default params:
  swing_lookback    int   = 50    — candles to scan for swing high/low
  entry_tolerance   float = 0.5   — % distance from level; price must be within this
  atr_period        int   = 14
  atr_multiplier    float = 0.5   — stop buffer as multiple of ATR beyond the level
  rr_ratio          float = 2.0
  min_move_pct      float = 1.0   — ignore swings smaller than this % (avoids noise)
"""
from dataclasses import dataclass, field
from typing import Literal, Optional


_FIB_RATIOS = [0.382, 0.500, 0.618]


@dataclass
class FibLevel:
    ratio: float
    price: float
    label: str  # e.g. "61.8%"


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    fib_level: float        # the Fib price that triggered entry
    fib_ratio: float        # e.g. 0.618
    swing_high: float
    swing_low: float
    reason: str


def _find_swing_points(candles: list[dict], lookback: int) -> tuple[float, int, float, int]:
    """
    Scan the last `lookback` candles for the highest high and lowest low.
    Returns (swing_high, high_idx, swing_low, low_idx) where indices are
    positions within the lookback slice (0 = oldest, lookback-1 = newest).
    """
    window = candles[-lookback:]
    highs = [c["high"] for c in window]
    lows = [c["low"] for c in window]

    high_idx = highs.index(max(highs))
    low_idx = lows.index(min(lows))

    return max(highs), high_idx, min(lows), low_idx


def _compute_atr(candles: list[dict], period: int = 14) -> float:
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


def _fib_levels(swing_high: float, swing_low: float, uptrend: bool) -> list[FibLevel]:
    """
    Compute key Fib retracement levels.
    Uptrend:   levels are measured downward from swing_high.
    Downtrend: levels are measured upward from swing_low.
    """
    move = swing_high - swing_low
    levels = []
    for ratio in _FIB_RATIOS:
        if uptrend:
            price = swing_high - ratio * move
        else:
            price = swing_low + ratio * move
        levels.append(FibLevel(ratio=ratio, price=price, label=f"{ratio*100:.1f}%"))
    return levels


def evaluate(candles: list[dict], params: Optional[dict] = None) -> Signal:
    """
    Given OHLCV candles (newest last), return a Fibonacci retracement signal.

    params keys (all optional):
      swing_lookback    int   = 50
      entry_tolerance   float = 0.5   (%)
      atr_period        int   = 14
      atr_multiplier    float = 0.5
      rr_ratio          float = 2.0
      min_move_pct      float = 1.0   (%)
    """
    p = params or {}
    swing_lookback = int(p.get("swing_lookback", 50))
    entry_tolerance = float(p.get("entry_tolerance", 0.5))
    atr_period = int(p.get("atr_period", 14))
    atr_multiplier = float(p.get("atr_multiplier", 0.5))
    rr_ratio = float(p.get("rr_ratio", 2.0))
    min_move_pct = float(p.get("min_move_pct", 1.0))

    min_candles = swing_lookback + atr_period + 2
    if len(candles) < min_candles:
        return Signal("none", 0, 0, 0, 0, 0, 0, 0, "not enough candles")

    swing_high, high_idx, swing_low, low_idx = _find_swing_points(candles, swing_lookback)

    # Reject tiny swings — just noise
    move_pct = (swing_high - swing_low) / swing_low * 100
    if move_pct < min_move_pct:
        return Signal(
            "none", 0, 0, 0, 0, 0, swing_high, swing_low,
            f"Swing too small: {move_pct:.2f}% < {min_move_pct}%"
        )

    uptrend = high_idx > low_idx   # high came after low → price trended up

    entry = candles[-1]["close"]
    atr = _compute_atr(candles, atr_period)
    if atr == 0:
        return Signal("none", entry, 0, 0, 0, 0, swing_high, swing_low, "ATR is zero")

    stop_buffer = atr * atr_multiplier
    levels = _fib_levels(swing_high, swing_low, uptrend)

    # Find the closest Fib level to current price
    closest: Optional[FibLevel] = None
    closest_dist = float("inf")
    for lvl in levels:
        dist_pct = abs(entry - lvl.price) / entry * 100
        if dist_pct < closest_dist:
            closest_dist = dist_pct
            closest = lvl

    if closest is None or closest_dist > entry_tolerance:
        return Signal(
            "none", entry, 0, 0, 0, 0, swing_high, swing_low,
            f"Not near any Fib level (closest {closest.label if closest else '?'} "
            f"at {closest_dist:.2f}%)"
        )

    if uptrend:
        # Long: price retraced to a support level
        # Guard: entry must be below swing_high (still in the retracement, not at new high)
        if entry >= swing_high:
            return Signal(
                "none", entry, 0, 0, 0, 0, swing_high, swing_low,
                "Price at/above swing high — retracement already over"
            )
        stop_loss = round(closest.price - stop_buffer, 2)
        risk = entry - stop_loss
        if risk <= 0:
            return Signal("none", entry, 0, 0, 0, 0, swing_high, swing_low, "Invalid risk (stop >= entry)")
        take_profit = round(entry + risk * rr_ratio, 2)
        return Signal(
            action="long",
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fib_level=round(closest.price, 2),
            fib_ratio=closest.ratio,
            swing_high=round(swing_high, 2),
            swing_low=round(swing_low, 2),
            reason=(
                f"Uptrend retracement to {closest.label} Fib "
                f"({closest.price:.0f}) — {closest_dist:.2f}% away"
            ),
        )

    else:
        # Short: price bounced up to a resistance level
        # Guard: entry must be above swing_low (still in the bounce, not at new low)
        if entry <= swing_low:
            return Signal(
                "none", entry, 0, 0, 0, 0, swing_high, swing_low,
                "Price at/below swing low — bounce already over"
            )
        stop_loss = round(closest.price + stop_buffer, 2)
        risk = stop_loss - entry
        if risk <= 0:
            return Signal("none", entry, 0, 0, 0, 0, swing_high, swing_low, "Invalid risk (stop <= entry)")
        take_profit = round(entry - risk * rr_ratio, 2)
        return Signal(
            action="short",
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fib_level=round(closest.price, 2),
            fib_ratio=closest.ratio,
            swing_high=round(swing_high, 2),
            swing_low=round(swing_low, 2),
            reason=(
                f"Downtrend bounce to {closest.label} Fib "
                f"({closest.price:.0f}) — {closest_dist:.2f}% away"
            ),
        )
