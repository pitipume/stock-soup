"""
Three Golden strategy — inspired by "Three Golden by Moonalert" (TradingView).
Original indicator: https://www.tradingview.com/script/bqbaMOSM/
Credit: Moonalert (TradingView)

Entry logic — ALL THREE must agree:
  Long:  price > BB midline  AND  RSI > 50  AND  MACD line > 0
  Short: price < BB midline  AND  RSI < 50  AND  MACD line < 0
  Wait:  any disagreement → no trade

Signal fires on the first candle where all three flip into agreement
(previous candle did not have full consensus in that direction).

Stop loss:  1 ATR from entry
Take profit: 2× risk (1:2 R:R)
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


def _ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(values[:period]) / period]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def _sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0.0
    return sum(values[-period:]) / period


def _compute_rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    rs = avg_gain / avg_loss if avg_loss else 100
    return 100 - 100 / (1 + rs)


def _compute_macd_line(closes: list[float], fast: int = 12, slow: int = 26) -> float:
    ema_f = _ema(closes, fast)
    ema_s = _ema(closes, slow)
    if not ema_f or not ema_s:
        return 0.0
    return ema_f[-1] - ema_s[-1]


def _compute_atr(candles: list[dict], period: int = 14) -> float:
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        prev = candles[i - 1]["close"]
        h, l = candles[i]["high"], candles[i]["low"]
        trs.append(max(h - l, abs(h - prev), abs(l - prev)))
    return sum(trs[-period:]) / min(len(trs), period)


def _consensus(closes: list[float], candles: list[dict], rsi_period: int, bb_period: int,
               macd_fast: int, macd_slow: int) -> tuple[bool, bool]:
    """Return (bullish_consensus, bearish_consensus) for the last candle."""
    price = closes[-1]
    bb_mid = _sma(closes, bb_period)
    rsi = _compute_rsi(closes, rsi_period)
    macd = _compute_macd_line(closes, macd_fast, macd_slow)
    bull = price > bb_mid and rsi > 50 and macd > 0
    bear = price < bb_mid and rsi < 50 and macd < 0
    return bull, bear


def evaluate(candles: list[dict], params: Optional[dict] = None) -> Signal:
    p = params or {}
    rsi_period = int(p.get("rsi_period", 14))
    bb_period = int(p.get("bb_period", 20))
    macd_fast = int(p.get("macd_fast", 12))
    macd_slow = int(p.get("macd_slow", 26))
    atr_period = int(p.get("atr_period", 14))
    atr_mult = float(p.get("atr_multiplier", 1.0))
    rr_ratio = float(p.get("rr_ratio", 2.0))

    min_needed = max(macd_slow, bb_period, rsi_period) + 5
    if len(candles) < min_needed + 1:
        return Signal("none", 0, 0, 0, 0, 0, "not enough candles")

    closes = [c["close"] for c in candles]
    entry = closes[-1]

    # Current and previous consensus
    bull_now, bear_now = _consensus(closes, candles, rsi_period, bb_period, macd_fast, macd_slow)
    bull_prev, bear_prev = _consensus(closes[:-1], candles[:-1], rsi_period, bb_period, macd_fast, macd_slow)

    # Signal only on the first bar where consensus forms
    long_signal = bull_now and not bull_prev
    short_signal = bear_now and not bear_prev

    rsi_val = _compute_rsi(closes, rsi_period)
    macd_val = _compute_macd_line(closes, macd_fast, macd_slow)
    atr = _compute_atr(candles, atr_period)

    if atr == 0:
        return Signal("none", entry, 0, 0, rsi_val, macd_val, "ATR is zero")

    if long_signal:
        sl = entry - atr * atr_mult
        tp = entry + atr * atr_mult * rr_ratio
        return Signal("long", entry, round(sl, 4), round(tp, 4),
                      round(rsi_val, 2), round(macd_val, 6),
                      "All three bullish: price>BB_mid, RSI>50, MACD>0")

    if short_signal:
        sl = entry + atr * atr_mult
        tp = entry - atr * atr_mult * rr_ratio
        return Signal("short", entry, round(sl, 4), round(tp, 4),
                      round(rsi_val, 2), round(macd_val, 6),
                      "All three bearish: price<BB_mid, RSI<50, MACD<0")

    return Signal("none", entry, 0, 0, round(rsi_val, 2), round(macd_val, 6), "No consensus")
