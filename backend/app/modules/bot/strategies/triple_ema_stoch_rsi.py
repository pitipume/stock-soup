"""
Triple EMA + Stochastic RSI strategy (TTMW-style).

Entry logic:
  Long:  EMA12 > EMA26 > EMA200 (all EMAs aligned bullish)
         AND StochRSI K crosses above D while both are in oversold zone (< 20)
  Short: EMA12 < EMA26 < EMA200 (all EMAs aligned bearish)
         AND StochRSI K crosses below D while both are in overbought zone (> 80)

Stop loss:  lowest low (long) / highest high (short) of the last 3 candles
Take profit: 2× risk distance from entry to SL

Default params:
  ema_fast=12, ema_slow=26, ema_filter=200
  rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3
  oversold=20, overbought=80, rr_ratio=2.0
"""
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    k: float
    d: float
    reason: str


def _ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def _sma(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    return [sum(values[i:i + period]) / period for i in range(len(values) - period + 1)]


def _compute_rsi(closes: list[float], period: int = 14) -> list[float]:
    if len(closes) < period + 1:
        return []
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_vals = []
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi_vals.append(100 - 100 / (1 + rs))
    return rsi_vals


def _compute_stoch_rsi(
    closes: list[float],
    rsi_period: int = 14,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> tuple[list[float], list[float]]:
    rsi_vals = _compute_rsi(closes, rsi_period)
    if len(rsi_vals) < stoch_period:
        return [], []

    raw_k = []
    for i in range(stoch_period - 1, len(rsi_vals)):
        window = rsi_vals[i - stoch_period + 1:i + 1]
        lo, hi = min(window), max(window)
        raw_k.append((rsi_vals[i] - lo) / (hi - lo) * 100 if hi != lo else 50.0)

    k = _sma(raw_k, k_smooth)
    d = _sma(k, d_smooth)
    return k, d


def evaluate(candles: list[dict], params: Optional[dict] = None) -> Signal:
    p = params or {}
    ema_fast = int(p.get("ema_fast", 12))
    ema_slow = int(p.get("ema_slow", 26))
    ema_filter = int(p.get("ema_filter", 200))
    rsi_period = int(p.get("rsi_period", 14))
    stoch_period = int(p.get("stoch_period", 14))
    k_smooth = int(p.get("k_smooth", 3))
    d_smooth = int(p.get("d_smooth", 3))
    oversold = float(p.get("oversold", 20))
    overbought = float(p.get("overbought", 80))
    rr_ratio = float(p.get("rr_ratio", 2.0))

    min_needed = ema_filter + rsi_period + stoch_period + k_smooth + d_smooth + 10
    if len(candles) < min_needed:
        return Signal("none", 0, 0, 0, 0, 0, "not enough candles")

    closes = [c["close"] for c in candles]
    entry = closes[-1]

    ema_f = _ema(closes, ema_fast)
    ema_s = _ema(closes, ema_slow)
    ema_fil = _ema(closes, ema_filter)
    if not ema_f or not ema_s or not ema_fil:
        return Signal("none", entry, 0, 0, 0, 0, "EMA failed")

    curr_fast, curr_slow, curr_filter = ema_f[-1], ema_s[-1], ema_fil[-1]
    bullish_ema = curr_fast > curr_slow > curr_filter
    bearish_ema = curr_fast < curr_slow < curr_filter

    k, d = _compute_stoch_rsi(closes, rsi_period, stoch_period, k_smooth, d_smooth)
    if len(k) < 2 or len(d) < 2:
        return Signal("none", entry, 0, 0, 0, 0, "StochRSI failed")

    k_prev, k_curr = k[-2], k[-1]
    d_prev, d_curr = d[-2], d[-1]

    # K crossed above D while in oversold
    bullish_cross = k_prev < d_prev and k_curr > d_curr and k_prev < oversold
    # K crossed below D while in overbought
    bearish_cross = k_prev > d_prev and k_curr < d_curr and k_prev > overbought

    lows = [c["low"] for c in candles[-3:]]
    highs = [c["high"] for c in candles[-3:]]

    if bullish_ema and bullish_cross:
        stop_loss = min(lows)
        risk = entry - stop_loss
        if risk <= 0:
            return Signal("none", entry, 0, 0, round(k_curr, 2), round(d_curr, 2), "zero risk distance")
        take_profit = entry + risk * rr_ratio
        return Signal(
            action="long",
            entry_price=entry,
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            k=round(k_curr, 2),
            d=round(d_curr, 2),
            reason=f"EMA aligned bullish | StochRSI K crossed above D from oversold ({k_prev:.1f})",
        )

    if bearish_ema and bearish_cross:
        stop_loss = max(highs)
        risk = stop_loss - entry
        if risk <= 0:
            return Signal("none", entry, 0, 0, round(k_curr, 2), round(d_curr, 2), "zero risk distance")
        take_profit = entry - risk * rr_ratio
        return Signal(
            action="short",
            entry_price=entry,
            stop_loss=round(stop_loss, 4),
            take_profit=round(take_profit, 4),
            k=round(k_curr, 2),
            d=round(d_curr, 2),
            reason=f"EMA aligned bearish | StochRSI K crossed below D from overbought ({k_prev:.1f})",
        )

    return Signal(
        action="none",
        entry_price=entry,
        stop_loss=0,
        take_profit=0,
        k=round(k_curr, 2),
        d=round(d_curr, 2),
        reason="No signal",
    )
