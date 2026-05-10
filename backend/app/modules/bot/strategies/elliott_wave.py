"""
Elliott Wave + Fibonacci Confluence strategy.

Theory:
  Impulse waves move in 5 sub-waves; the strongest move is Wave 3.
  This strategy identifies the start of Wave 3 — the moment AFTER Wave 2
  has completed its retracement and price resumes the Wave 1 direction.

Signal logic:
  1. PIVOT DETECTION — find confirmed swing highs and lows.
     A pivot high is confirmed when N bars to the LEFT and N bars to the RIGHT
     are all lower than the pivot bar. Same logic inverted for pivot lows.
     Using confirmed pivots (not just running extremes) prevents false early entries.

  2. WAVE STRUCTURE — build the most recent W0→W1→W2 sequence from the pivot list.
     W0: starting pivot (low for uptrend, high for downtrend)
     W1: first counter-pivot (high for uptrend, low for downtrend)
     W2: retracement pivot (low for uptrend, high for downtrend)
     The sequence must be alternating: low→high→low (uptrend) or high→low→high (downtrend).

  3. EWT RULE VALIDATION:
     Rule A — W2 must not exceed W0.
       Uptrend:   W2_low  must be  > W0_low   (if W2 falls below W0, count is invalid)
       Downtrend: W2_high must be  < W0_high
     Rule B — W2 retracement must be within 23.6%–78.6% of W1.
       Outside this range → too shallow or too deep → not a Wave 2.
       Optimal zone (38.2%–61.8%) is flagged but not required for signal.

  4. ENTRY — price just broke beyond the W2 extreme in the W1 direction.
     This is the first sign that Wave 3 is starting.
     Uptrend:   current close > W2_low + ATR  (started moving away from W2)
     Downtrend: current close < W2_high - ATR

  5. STOP LOSS — just beyond W2 extreme (ATR buffer).
     EWT hard rule: if price breaks the W0 start, the wave count is wrong.
     A stop just beyond W2 gives a tight risk while respecting the count.

  6. TAKE PROFIT — 161.8% Fibonacci extension of W1 from W2.
     Wave 3 most commonly reaches 161.8% of Wave 1 length.
     tp = W2 + (W1_length × 1.618)  [uptrend]
     tp = W2 - (W1_length × 1.618)  [downtrend]

  7. MINIMUM R:R — checked against rr_ratio param (default 2.0). Skipped if below.

Default params:
  pivot_left      int   = 3      — bars to the left of a pivot (confirmation)
  pivot_right     int   = 3      — bars to the right (must close before confirming)
  min_pivots      int   = 6      — minimum pivots to build a reliable wave count
  retracement_lo  float = 23.6   — minimum W2 retracement % of W1
  retracement_hi  float = 78.6   — maximum W2 retracement % of W1
  atr_period      int   = 14
  atr_buffer      float = 0.5    — stop buffer beyond W2 in ATR units
  extension       float = 1.618  — Fibonacci extension for take-profit
  rr_ratio        float = 2.0    — minimum risk-to-reward
"""
import math
from dataclasses import dataclass
from typing import Literal, Optional, Tuple


@dataclass
class Pivot:
    index: int         # position in the original candle list
    price: float
    kind: Literal["high", "low"]


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    w0: float
    w1: float
    w2: float
    retracement_pct: float    # how deep W2 retraced W1 (%)
    extension_target: float   # 161.8% projection
    reason: str


# ── Pivot detection ───────────────────────────────────────────────────────────

def _find_pivots(candles: list[dict], left: int, right: int) -> list[Pivot]:
    """
    Scan candles and return confirmed pivot highs and lows.

    A pivot high at index i requires:
      candles[i-left : i]  all have  high < candles[i]['high']
      candles[i+1 : i+right+1]  all have  high < candles[i]['high']

    The last `right` candles cannot be confirmed pivots (not enough bars to the right).
    This is intentional — an unconfirmed bar is not a validated swing.
    """
    pivots: list[Pivot] = []
    n = len(candles)

    for i in range(left, n - right):
        h = candles[i]["high"]
        l = candles[i]["low"]

        # Check pivot high
        left_highs  = all(candles[j]["high"] < h for j in range(i - left, i))
        right_highs = all(candles[j]["high"] < h for j in range(i + 1, i + right + 1))
        if left_highs and right_highs:
            pivots.append(Pivot(index=i, price=h, kind="high"))
            continue  # a bar cannot be both high and low pivot

        # Check pivot low
        left_lows  = all(candles[j]["low"] > l for j in range(i - left, i))
        right_lows = all(candles[j]["low"] > l for j in range(i + 1, i + right + 1))
        if left_lows and right_lows:
            pivots.append(Pivot(index=i, price=l, kind="low"))

    return pivots


# ── ATR ───────────────────────────────────────────────────────────────────────

def _atr(candles: list[dict], period: int) -> float:
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        prev = candles[i - 1]["close"]
        h, l = candles[i]["high"], candles[i]["low"]
        trs.append(max(h - l, abs(h - prev), abs(l - prev)))
    return sum(trs[-period:]) / min(len(trs), period)


# ── Wave structure builder ────────────────────────────────────────────────────

def _find_wave_sequence(
    pivots: list[Pivot],
) -> Optional[Tuple[Pivot, Pivot, Pivot, bool]]:
    """
    Walk the pivot list backwards looking for the most recent valid W0→W1→W2.

    Returns (w0, w1, w2, is_uptrend) or None if no valid sequence found.

    An uptrend sequence is: low → high → low  (W0=low, W1=high, W2=low)
    A downtrend sequence is: high → low → high (W0=high, W1=low, W2=high)

    We scan from the newest pivot backwards to find the latest W2,
    then trace back for a matching W1 and W0.
    """
    # Need at least 3 pivots
    if len(pivots) < 3:
        return None

    # Try starting from the most recent pivot as W2 and work backwards
    for w2_idx in range(len(pivots) - 1, 1, -1):
        w2 = pivots[w2_idx]
        w1 = pivots[w2_idx - 1]
        w0 = pivots[w2_idx - 2]

        # Uptrend: low → high → low
        if w0.kind == "low" and w1.kind == "high" and w2.kind == "low":
            return w0, w1, w2, True

        # Downtrend: high → low → high
        if w0.kind == "high" and w1.kind == "low" and w2.kind == "high":
            return w0, w1, w2, False

    return None


# ── Public evaluate ───────────────────────────────────────────────────────────

def evaluate(candles: list[dict], params: Optional[dict] = None) -> Signal:
    """
    Given OHLCV candles (newest last), return an Elliott Wave W3 signal.

    params keys (all optional, see module docstring for defaults):
      pivot_left, pivot_right, min_pivots,
      retracement_lo, retracement_hi,
      atr_period, atr_buffer, extension, rr_ratio
    """
    p = params or {}
    pivot_left     = int(p.get("pivot_left", 3))
    pivot_right    = int(p.get("pivot_right", 3))
    min_pivots     = int(p.get("min_pivots", 6))
    retracement_lo = float(p.get("retracement_lo", 23.6))
    retracement_hi = float(p.get("retracement_hi", 78.6))
    atr_period     = int(p.get("atr_period", 14))
    atr_buffer     = float(p.get("atr_buffer", 0.5))
    extension      = float(p.get("extension", 1.618))
    rr_ratio       = float(p.get("rr_ratio", 2.0))

    min_candles = pivot_left + pivot_right + atr_period + 10
    if len(candles) < min_candles:
        return Signal("none", 0, 0, 0, 0, 0, 0, 0, 0, "not enough candles")

    pivots = _find_pivots(candles, pivot_left, pivot_right)

    if len(pivots) < min_pivots:
        return Signal(
            "none", 0, 0, 0, 0, 0, 0, 0, 0,
            f"Too few confirmed pivots ({len(pivots)} < {min_pivots})"
        )

    wave = _find_wave_sequence(pivots)
    if wave is None:
        return Signal("none", 0, 0, 0, 0, 0, 0, 0, 0, "No W0→W1→W2 structure found")

    w0, w1, w2, uptrend = wave
    current_close = candles[-1]["close"]
    current_atr = _atr(candles, atr_period)

    if current_atr == 0:
        return Signal("none", current_close, 0, 0, 0, 0, 0, 0, 0, "ATR is zero")

    # ── EWT Rule A: W2 must not exceed W0 ────────────────────────────────────
    if uptrend:
        if w2.price <= w0.price:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price, 0, 0,
                f"EWT violated: W2 low ({w2.price:.2f}) ≤ W0 low ({w0.price:.2f}) — count invalid"
            )
    else:
        if w2.price >= w0.price:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price, 0, 0,
                f"EWT violated: W2 high ({w2.price:.2f}) ≥ W0 high ({w0.price:.2f}) — count invalid"
            )

    # ── EWT Rule B: W2 retracement depth ─────────────────────────────────────
    w1_length = abs(w1.price - w0.price)
    if w1_length == 0:
        return Signal("none", current_close, 0, 0, 0, 0, 0, 0, 0, "W1 length is zero")

    if uptrend:
        retracement = (w1.price - w2.price) / w1_length * 100
    else:
        retracement = (w2.price - w1.price) / w1_length * 100

    if retracement < retracement_lo:
        return Signal(
            "none", current_close, 0, 0, w0.price, w1.price, w2.price,
            round(retracement, 1), 0,
            f"W2 retracement too shallow: {retracement:.1f}% < {retracement_lo}%"
        )
    if retracement > retracement_hi:
        return Signal(
            "none", current_close, 0, 0, w0.price, w1.price, w2.price,
            round(retracement, 1), 0,
            f"W2 retracement too deep: {retracement:.1f}% > {retracement_hi}%"
        )

    # ── Entry confirmation: price moving away from W2 in W1 direction ────────
    stop_buffer = current_atr * atr_buffer

    if uptrend:
        # Wave 3 long: price climbing away from W2 (the retracement low)
        if current_close <= w2.price:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price,
                round(retracement, 1), 0,
                f"Waiting: price {current_close:.2f} still at/below W2 low {w2.price:.2f}"
            )
        stop_loss = round(w2.price - stop_buffer, 2)
        risk = current_close - stop_loss
        if risk <= 0:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price,
                round(retracement, 1), 0, "Stop distance is zero or negative"
            )
        # 161.8% extension: W2 + W1_length × extension
        ext_target = w2.price + w1_length * extension
        take_profit = round(ext_target, 2)

        actual_rr = (take_profit - current_close) / risk
        if actual_rr < rr_ratio:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price,
                round(retracement, 1), round(ext_target, 2),
                f"R:R too low: {actual_rr:.2f} < {rr_ratio} (entry too far from W2)"
            )

        golden = 38.2 <= retracement <= 61.8
        return Signal(
            action="long",
            entry_price=current_close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            w0=round(w0.price, 2),
            w1=round(w1.price, 2),
            w2=round(w2.price, 2),
            retracement_pct=round(retracement, 1),
            extension_target=round(ext_target, 2),
            reason=(
                f"EWT W3 LONG — W2 retraced {retracement:.1f}% of W1"
                f"{' (golden zone)' if golden else ''} | "
                f"target 161.8%={ext_target:.0f} | R:R {actual_rr:.2f}"
            ),
        )

    else:
        # Wave 3 short: price dropping away from W2 (the retracement high)
        if current_close >= w2.price:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price,
                round(retracement, 1), 0,
                f"Waiting: price {current_close:.2f} still at/above W2 high {w2.price:.2f}"
            )
        stop_loss = round(w2.price + stop_buffer, 2)
        risk = stop_loss - current_close
        if risk <= 0:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price,
                round(retracement, 1), 0, "Stop distance is zero or negative"
            )
        # 161.8% extension: W2 - W1_length × extension
        ext_target = w2.price - w1_length * extension
        take_profit = round(ext_target, 2)

        actual_rr = (current_close - take_profit) / risk
        if actual_rr < rr_ratio:
            return Signal(
                "none", current_close, 0, 0, w0.price, w1.price, w2.price,
                round(retracement, 1), round(ext_target, 2),
                f"R:R too low: {actual_rr:.2f} < {rr_ratio} (entry too far from W2)"
            )

        golden = 38.2 <= retracement <= 61.8
        return Signal(
            action="short",
            entry_price=current_close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            w0=round(w0.price, 2),
            w1=round(w1.price, 2),
            w2=round(w2.price, 2),
            retracement_pct=round(retracement, 1),
            extension_target=round(ext_target, 2),
            reason=(
                f"EWT W3 SHORT — W2 retraced {retracement:.1f}% of W1"
                f"{' (golden zone)' if golden else ''} | "
                f"target 161.8%={ext_target:.0f} | R:R {actual_rr:.2f}"
            ),
        )
