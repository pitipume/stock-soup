"""
MACD + EMA Trend-Following strategy.

Signal logic:
  A trade is entered only when TWO conditions align:
    1. EMA trend filter — price is above the slow EMA (bullish) or below it (bearish)
    2. MACD crossover — MACD line crosses above signal line (long) or below (short)

This prevents entering counter-trend trades, which is the main weakness of RSI alone.

Default params:
  ema_period=200  — long-term trend direction (price above = bullish regime)
  macd_fast=12    — standard MACD fast EMA
  macd_slow=26    — standard MACD slow EMA
  macd_signal=9   — signal line smoothing

Stop loss:  1 ATR below entry (long) / above entry (short)
Take profit: 2× risk distance (1:2 R:R, matching spec minimum)
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    macd: float
    macd_signal: float
    ema: float
    reason: str


def _ema(values: list[float], period: int) -> list[float]:
    """Exponential moving average over a list of values."""
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def compute_macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """
    Returns (macd_line, signal_line, histogram) aligned to the same indices.
    All three lists have the same length (may be shorter than closes).
    """
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    # Align: ema_slow is shorter by (slow - fast) elements
    offset = slow - fast
    if offset > len(ema_fast):
        return [], [], []

    ema_fast_aligned = ema_fast[offset:]
    macd_line = [f - s for f, s in zip(ema_fast_aligned, ema_slow)]

    signal_line = _ema(macd_line, signal_period)
    macd_aligned = macd_line[len(macd_line) - len(signal_line):]

    histogram = [m - s for m, s in zip(macd_aligned, signal_line)]
    return macd_aligned, signal_line, histogram


def compute_atr(candles: list[dict], period: int = 14) -> float:
    """Average True Range."""
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


def evaluate(candles: list[dict], params: dict | None = None) -> Signal:
    """
    Given OHLCV candles (newest last), return a trading signal.

    params keys (all optional):
      ema_period    int   = 200
      macd_fast     int   = 12
      macd_slow     int   = 26
      macd_signal   int   = 9
      atr_period    int   = 14
      atr_multiplier float = 1.0
      rr_ratio      float = 2.0
    """
    p = params or {}
    ema_period = int(p.get("ema_period", 200))
    macd_fast = int(p.get("macd_fast", 12))
    macd_slow = int(p.get("macd_slow", 26))
    macd_sig = int(p.get("macd_signal", 9))
    atr_period = int(p.get("atr_period", 14))
    atr_multiplier = float(p.get("atr_multiplier", 1.0))
    rr_ratio = float(p.get("rr_ratio", 2.0))

    min_candles = max(ema_period, macd_slow + macd_sig) + 5
    if len(candles) < min_candles:
        return Signal("none", 0, 0, 0, 0, 0, 0, "not enough candles")

    closes = [c["close"] for c in candles]
    entry = closes[-1]

    # EMA trend filter
    ema_values = _ema(closes, ema_period)
    if not ema_values:
        return Signal("none", entry, 0, 0, 0, 0, 0, "EMA failed")
    current_ema = ema_values[-1]
    bullish_regime = entry > current_ema
    bearish_regime = entry < current_ema

    # MACD crossover — compare last two bars
    macd_line, signal_line, _ = compute_macd(closes, macd_fast, macd_slow, macd_sig)
    if len(macd_line) < 2 or len(signal_line) < 2:
        return Signal("none", entry, 0, 0, 0, 0, current_ema, "MACD failed")

    macd_prev, macd_curr = macd_line[-2], macd_line[-1]
    sig_prev, sig_curr = signal_line[-2], signal_line[-1]

    bullish_cross = macd_prev < sig_prev and macd_curr > sig_curr  # MACD crossed above signal
    bearish_cross = macd_prev > sig_prev and macd_curr < sig_curr  # MACD crossed below signal

    atr = compute_atr(candles, atr_period)
    if atr == 0:
        return Signal("none", entry, 0, 0, macd_curr, sig_curr, current_ema, "ATR is zero")

    stop_distance = atr * atr_multiplier

    if bullish_regime and bullish_cross:
        stop_loss = entry - stop_distance
        take_profit = entry + stop_distance * rr_ratio
        return Signal(
            action="long",
            entry_price=entry,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            macd=round(macd_curr, 6),
            macd_signal=round(sig_curr, 6),
            ema=round(current_ema, 2),
            reason=f"MACD bullish cross above signal | price {entry:.0f} > EMA {current_ema:.0f}",
        )

    if bearish_regime and bearish_cross:
        stop_loss = entry + stop_distance
        take_profit = entry - stop_distance * rr_ratio
        return Signal(
            action="short",
            entry_price=entry,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            macd=round(macd_curr, 6),
            macd_signal=round(sig_curr, 6),
            ema=round(current_ema, 2),
            reason=f"MACD bearish cross below signal | price {entry:.0f} < EMA {current_ema:.0f}",
        )

    return Signal(
        action="none",
        entry_price=entry,
        stop_loss=0,
        take_profit=0,
        macd=round(macd_curr, 6),
        macd_signal=round(sig_curr, 6),
        ema=round(current_ema, 2),
        reason="No crossover in current regime",
    )
