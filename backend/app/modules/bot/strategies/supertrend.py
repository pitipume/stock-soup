"""
Supertrend strategy — ATR-based dynamic trailing stop that flips direction
on a price crossover. Acts as both a trend filter and a signal trigger.

Entry logic:
  Long:  Supertrend flips from bearish to bullish (price crosses above the band)
  Short: Supertrend flips from bullish to bearish (price crosses below the band)

Stop loss:  opposite Supertrend band at entry
Take profit: 2× risk (1:2 R:R by default)

Parameters:
  atr_period   — ATR lookback (default 10)
  atr_mult     — band width multiplier (default 3.0)
  rr_ratio     — risk:reward ratio (default 2.0)
"""
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    rsi: float
    macd: float
    reason: str


def _compute_atr(candles: list[dict], period: int) -> list[float]:
    if len(candles) < 2:
        return [0.0]
    trs = []
    for i in range(1, len(candles)):
        prev = candles[i - 1]["close"]
        h, l = candles[i]["high"], candles[i]["low"]
        trs.append(max(h - l, abs(h - prev), abs(l - prev)))
    # Wilder's smoothed ATR
    atrs = [sum(trs[:period]) / period] if len(trs) >= period else [trs[-1] if trs else 0.0]
    for i in range(period, len(trs)):
        atrs.append((atrs[-1] * (period - 1) + trs[i]) / period)
    return atrs


def _compute_supertrend(candles: list[dict], period: int, mult: float) -> list[dict]:
    """Return list of {direction, upper, lower} for each candle (same length as candles)."""
    atrs = _compute_atr(candles, period)
    # Align ATR to candles: first `period` candles have no ATR
    atr_aligned = [0.0] * period + atrs

    results = []
    prev_upper = prev_lower = prev_dir = None

    for i, c in enumerate(candles):
        hl2 = (c["high"] + c["low"]) / 2
        atr = atr_aligned[i] if i < len(atr_aligned) else atrs[-1]

        raw_upper = hl2 + mult * atr
        raw_lower = hl2 - mult * atr

        if prev_upper is None:
            upper, lower = raw_upper, raw_lower
            direction = 1  # start bullish
        else:
            upper = raw_upper if raw_upper < prev_upper or candles[i - 1]["close"] > prev_upper else prev_upper
            lower = raw_lower if raw_lower > prev_lower or candles[i - 1]["close"] < prev_lower else prev_lower

            if prev_dir == 1 and c["close"] < lower:
                direction = -1
            elif prev_dir == -1 and c["close"] > upper:
                direction = 1
            else:
                direction = prev_dir

        results.append({"direction": direction, "upper": upper, "lower": lower})
        prev_upper, prev_lower, prev_dir = upper, lower, direction

    return results


def evaluate(candles: list[dict], params: Optional[dict] = None) -> Signal:
    p = params or {}
    atr_period = int(p.get("atr_period", 10))
    atr_mult = float(p.get("atr_multiplier", 3.0))
    rr_ratio = float(p.get("rr_ratio", 2.0))

    min_needed = atr_period + 5
    if len(candles) < min_needed + 1:
        return Signal("none", 0, 0, 0, 0, 0, "not enough candles")

    st = _compute_supertrend(candles, atr_period, atr_mult)
    if len(st) < 2:
        return Signal("none", 0, 0, 0, 0, 0, "not enough supertrend data")

    curr = st[-1]
    prev = st[-2]
    entry = candles[-1]["close"]

    # Signal fires only on the flip candle
    long_signal = curr["direction"] == 1 and prev["direction"] == -1
    short_signal = curr["direction"] == -1 and prev["direction"] == 1

    if long_signal:
        sl = curr["lower"]
        risk = entry - sl
        if risk <= 0:
            return Signal("none", entry, 0, 0, 0, 0, "zero risk")
        tp = entry + risk * rr_ratio
        return Signal("long", entry, round(sl, 4), round(tp, 4), 0.0, 0.0,
                      "Supertrend flipped bullish")

    if short_signal:
        sl = curr["upper"]
        risk = sl - entry
        if risk <= 0:
            return Signal("none", entry, 0, 0, 0, 0, "zero risk")
        tp = entry - risk * rr_ratio
        return Signal("short", entry, round(sl, 4), round(tp, 4), 0.0, 0.0,
                      "Supertrend flipped bearish")

    return Signal("none", entry, 0, 0, 0.0, 0.0, "No Supertrend flip")
