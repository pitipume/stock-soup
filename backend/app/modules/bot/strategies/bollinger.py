"""
Bollinger Band Squeeze strategy.

Signal logic (three conditions must ALL be true):
  1. SQUEEZE — band width was at a recent low, indicating coiled energy.
     Band width = (upper - lower) / middle. A squeeze is when the current
     width falls in the bottom `squeeze_pct`% of widths over `squeeze_lookback` candles.
     The squeeze must have fired within the last `breakout_lookback` candles — we want
     to enter on the first breakout, not chase a move that already ran.

  2. BREAKOUT — price closes outside the band on the current candle:
       Close > upper band → LONG (bullish breakout)
       Close < lower band → SHORT (bearish breakout)

  3. VOLUME CONFIRMATION — current volume exceeds `volume_mult` × average volume
     over `bb_period` candles. Thin-volume breakouts are fakeouts; high volume = conviction.

Stop loss:  middle band (SMA) at time of entry — if price falls back to the mean,
            the breakout has failed. Capped at ATR × `atr_cap` from entry so the
            risk is never unbounded on a wide band.
Take profit: entry ± risk × `rr_ratio` (minimum 1:2 R:R per spec).

Why middle-band stop instead of ATR?
  Bollinger Bands are self-adapting to volatility. The middle band is a natural
  support/resistance after a breakout. If price can't hold above it, the setup is dead.
  The ATR cap prevents the stop being unreasonably wide on an already-wide band.

Default params:
  bb_period         int   = 20    — SMA period for Bollinger Bands
  bb_std            float = 2.0   — standard deviation multiplier
  squeeze_lookback  int   = 50    — candles used to rank band widths
  squeeze_pct       float = 20.0  — bottom X% of widths counts as squeeze
  breakout_lookback int   = 5     — squeeze must have occurred within last N candles
  volume_mult       float = 1.0   — volume must be > X × avg volume
  atr_period        int   = 14
  atr_cap           float = 2.0   — max stop distance in ATR units
  rr_ratio          float = 2.0
"""
import math
from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    band_width: float       # current band width (narrower = tighter squeeze)
    squeeze_active: bool    # was a squeeze present recently?
    upper_band: float
    lower_band: float
    middle_band: float
    reason: str


# ── Band computation ──────────────────────────────────────────────────────────

def _bollinger_bands(
    closes: list[float],
    period: int,
    num_std: float,
) -> list[tuple[float, float, float]]:
    """
    Return list of (upper, middle, lower) for each candle that has enough history.
    Output length = len(closes) - period + 1.
    """
    result = []
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(variance)
        result.append((mean + num_std * std, mean, mean - num_std * std))
    return result


def _band_width(upper: float, middle: float, lower: float) -> float:
    """Normalised band width — independent of price level."""
    return (upper - lower) / middle if middle > 0 else 0.0


def _volume_avg(candles: list[dict], period: int) -> float:
    vols = [c["volume"] for c in candles[-period:]]
    return sum(vols) / len(vols) if vols else 0.0


def _atr(candles: list[dict], period: int) -> float:
    if len(candles) < 2:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        prev = candles[i - 1]["close"]
        h, l = candles[i]["high"], candles[i]["low"]
        trs.append(max(h - l, abs(h - prev), abs(l - prev)))
    return sum(trs[-period:]) / min(len(trs), period)


# ── Squeeze detector ──────────────────────────────────────────────────────────

def _squeeze_history(
    bands: list[tuple[float, float, float]],
    squeeze_pct: float,
) -> list[bool]:
    """
    For each band entry, True if its width is in the bottom `squeeze_pct`%
    of all widths in the series.
    """
    widths = [_band_width(*b) for b in bands]
    sorted_w = sorted(widths)
    threshold_idx = max(0, int(len(sorted_w) * squeeze_pct / 100) - 1)
    threshold = sorted_w[threshold_idx]
    return [w <= threshold for w in widths]


# ── Public evaluate ───────────────────────────────────────────────────────────

def evaluate(candles: list[dict], params: Optional[dict] = None) -> Signal:
    """
    Given OHLCV candles (newest last), return a Bollinger Band Squeeze signal.

    params keys (all optional, see module docstring for defaults):
      bb_period, bb_std, squeeze_lookback, squeeze_pct,
      breakout_lookback, volume_mult, atr_period, atr_cap, rr_ratio
    """
    p = params or {}
    bb_period         = int(p.get("bb_period", 20))
    bb_std            = float(p.get("bb_std", 2.0))
    squeeze_lookback  = int(p.get("squeeze_lookback", 50))
    squeeze_pct       = float(p.get("squeeze_pct", 20.0))
    breakout_lookback = int(p.get("breakout_lookback", 5))
    volume_mult       = float(p.get("volume_mult", 1.0))
    atr_period        = int(p.get("atr_period", 14))
    atr_cap           = float(p.get("atr_cap", 2.0))
    rr_ratio          = float(p.get("rr_ratio", 2.0))

    min_candles = squeeze_lookback + bb_period + atr_period
    if len(candles) < min_candles:
        return Signal("none", 0, 0, 0, 0, False, 0, 0, 0, "not enough candles")

    closes = [c["close"] for c in candles]

    # Compute bands over the whole series so we have a squeeze history
    all_bands = _bollinger_bands(closes, bb_period, bb_std)
    # all_bands[i] corresponds to candle index (bb_period - 1 + i)

    # We want the last `squeeze_lookback` band values for ranking
    history = all_bands[-squeeze_lookback:]
    squeezes = _squeeze_history(history, squeeze_pct)

    # Current band = last element
    upper, middle, lower = history[-1]
    width = _band_width(upper, middle, lower)
    current_close = closes[-1]
    current_volume = candles[-1]["volume"]
    avg_volume = _volume_avg(candles, bb_period)

    # Was there a squeeze in the last `breakout_lookback` candles (excluding current)?
    recent = squeezes[-(breakout_lookback + 1) : -1]
    squeeze_fired = any(recent)

    # Breakout direction
    broke_up = current_close > upper
    broke_down = current_close < lower

    if not (broke_up or broke_down):
        return Signal(
            "none", current_close, 0, 0, round(width, 6), squeeze_fired,
            round(upper, 2), round(lower, 2), round(middle, 2),
            f"No breakout (close {current_close:.0f} inside bands "
            f"{lower:.0f}–{upper:.0f}); squeeze_fired={squeeze_fired}"
        )

    if not squeeze_fired:
        direction = "above upper" if broke_up else "below lower"
        return Signal(
            "none", current_close, 0, 0, round(width, 6), False,
            round(upper, 2), round(lower, 2), round(middle, 2),
            f"Price broke {direction} but no prior squeeze — chasing the move"
        )

    # Volume confirmation
    volume_ok = avg_volume > 0 and current_volume >= volume_mult * avg_volume
    if not volume_ok:
        return Signal(
            "none", current_close, 0, 0, round(width, 6), True,
            round(upper, 2), round(lower, 2), round(middle, 2),
            f"Breakout without volume: {current_volume:.0f} < "
            f"{volume_mult} × avg {avg_volume:.0f}"
        )

    # Stop loss: middle band, capped at ATR × atr_cap
    current_atr = _atr(candles, atr_period)
    max_stop_dist = current_atr * atr_cap

    if broke_up:
        raw_stop = middle
        stop_dist = min(current_close - raw_stop, max_stop_dist)
        if stop_dist <= 0:
            return Signal("none", current_close, 0, 0, round(width, 6), True,
                          round(upper, 2), round(lower, 2), round(middle, 2),
                          "Stop distance is zero or negative")
        stop_loss = round(current_close - stop_dist, 2)
        take_profit = round(current_close + stop_dist * rr_ratio, 2)
        return Signal(
            action="long",
            entry_price=current_close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            band_width=round(width, 6),
            squeeze_active=True,
            upper_band=round(upper, 2),
            lower_band=round(lower, 2),
            middle_band=round(middle, 2),
            reason=(
                f"BB squeeze breakout LONG — close {current_close:.0f} > upper {upper:.0f} "
                f"with vol {current_volume:.0f} > {avg_volume:.0f}"
            ),
        )

    else:  # broke_down
        raw_stop = middle
        stop_dist = min(raw_stop - current_close, max_stop_dist)
        if stop_dist <= 0:
            return Signal("none", current_close, 0, 0, round(width, 6), True,
                          round(upper, 2), round(lower, 2), round(middle, 2),
                          "Stop distance is zero or negative")
        stop_loss = round(current_close + stop_dist, 2)
        take_profit = round(current_close - stop_dist * rr_ratio, 2)
        return Signal(
            action="short",
            entry_price=current_close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            band_width=round(width, 6),
            squeeze_active=True,
            upper_band=round(upper, 2),
            lower_band=round(lower, 2),
            middle_band=round(middle, 2),
            reason=(
                f"BB squeeze breakout SHORT — close {current_close:.0f} < lower {lower:.0f} "
                f"with vol {current_volume:.0f} > {avg_volume:.0f}"
            ),
        )
