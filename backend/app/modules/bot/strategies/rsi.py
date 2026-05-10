"""
RSI Mean-Reversion strategy.

Signal logic:
  RSI < oversold_threshold  → LONG  (buy the dip)
  RSI > overbought_threshold → SHORT (sell the spike)
  Otherwise                 → no signal

Default params (overridable via BotConfig.strategy_params):
  period=14, oversold=30, overbought=70, timeframe="15m"

Stop loss:  placed 1 ATR below entry (long) or above entry (short)
Take profit: entry ± 2× risk (enforces 1:2 R:R minimum from spec)
"""
from dataclasses import dataclass
from typing import Literal, Optional

import statistics


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    rsi: float
    reason: str


def compute_rsi(closes: list[float], period: int = 14) -> float:
    """Classic Wilder RSI."""
    if len(closes) < period + 1:
        return 50.0  # neutral — not enough data

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_atr(candles: list[dict], period: int = 14) -> float:
    """Average True Range — used to set stop distance."""
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
    Given a list of OHLCV candles (newest last), return a trading signal.

    params keys (all optional):
      rsi_period     int   = 14
      oversold       float = 30
      overbought     float = 70
      atr_period     int   = 14
      atr_multiplier float = 1.0   (stop distance = atr * multiplier)
      rr_ratio       float = 2.0   (take profit = entry ± risk * rr_ratio)
    """
    p = params or {}
    rsi_period = int(p.get("rsi_period", 14))
    oversold = float(p.get("oversold", 30))
    overbought = float(p.get("overbought", 70))
    atr_period = int(p.get("atr_period", 14))
    atr_multiplier = float(p.get("atr_multiplier", 1.0))
    rr_ratio = float(p.get("rr_ratio", 2.0))

    if len(candles) < rsi_period + 2:
        return Signal("none", 0, 0, 0, 0, "not enough candles")

    closes = [c["close"] for c in candles]
    rsi = compute_rsi(closes, rsi_period)
    atr = compute_atr(candles, atr_period)
    entry = closes[-1]
    stop_distance = atr * atr_multiplier

    if stop_distance == 0:
        return Signal("none", entry, 0, 0, rsi, "ATR is zero")

    if rsi < oversold:
        stop_loss = entry - stop_distance
        take_profit = entry + stop_distance * rr_ratio
        return Signal(
            action="long",
            entry_price=entry,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            rsi=round(rsi, 2),
            reason=f"RSI {rsi:.1f} < oversold {oversold}",
        )

    if rsi > overbought:
        stop_loss = entry + stop_distance
        take_profit = entry - stop_distance * rr_ratio
        return Signal(
            action="short",
            entry_price=entry,
            stop_loss=round(stop_loss, 2),
            take_profit=round(take_profit, 2),
            rsi=round(rsi, 2),
            reason=f"RSI {rsi:.1f} > overbought {overbought}",
        )

    return Signal("none", entry, 0, 0, round(rsi, 2), f"RSI {rsi:.1f} — no signal")
