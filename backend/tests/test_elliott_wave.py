"""
Tests for the Elliott Wave + Fibonacci Confluence strategy.

Builder philosophy:
  Monotonically ascending rallies and descending pullbacks produce ZERO
  intermediate confirmed pivots (a bar can only be a local extreme if at
  least pivot_right bars on each side are strictly on the other side of it).
  This keeps the pivot list clean: exactly W0, W1, W2 — no noise.

Real market data has many more pivots; tests use min_pivots=3 to bypass the
"enough history" guard (default=6 is appropriate for production, not synthetic data).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.modules.bot.strategies.elliott_wave import evaluate, _find_pivots


# ── Helpers ───────────────────────────────────────────────────────────────────

def _candle(close: float, hi_offset: float = 0.0, lo_offset: float = 0.0) -> dict:
    spread = close * 0.001  # tight spread; keeps pivot math simple
    return {
        "open":   close,
        "high":   close + spread + hi_offset,
        "low":    close - spread - lo_offset,
        "close":  close,
        "volume": 1000.0,
    }


def _flat(price: float, n: int) -> list[dict]:
    return [_candle(price) for _ in range(n)]


def _ramp(start: float, end: float, n: int) -> list[dict]:
    """Return n candles linearly interpolated from start to end (inclusive)."""
    if n <= 1:
        return [_candle(start)]
    step = (end - start) / (n - 1)
    return [_candle(start + step * i) for i in range(n)]


# ── Wave builders ─────────────────────────────────────────────────────────────

def _build_uptrend_wave(
    w0_price: float = 100.0,
    w1_price: float = 120.0,
    w2_price: float = 112.0,
    entry_price: float = 113.0,
    n_padding: int = 20,
    pivot_right: int = 3,
) -> list[dict]:
    """
    Build a clean W0(low)→W1(high)→W2(low)→entry uptrend sequence.

    Only three pivot-worthy bars are created.
    All transitions are monotonic ramps so no intermediate pivots form.
    The pivot_right bars after W2 are strictly ascending → W2 confirmed.
    Entry bar must be above W2.

    Requires: w2_price < w1_price - 2  (so the pullback ramp is strictly descending).
    """
    assert entry_price > w2_price, "entry_price must be above W2 for a long setup"
    assert w2_price < w1_price - 2, "w2_price must be well below w1_price (pullback must descend)"

    candles: list[dict] = []

    # Padding (no pivots)
    candles += _flat(w0_price + 5, n_padding)

    # Descend to W0 (3 bars — left confirmation)
    candles += _ramp(w0_price + 3, w0_price + 1, 3)
    # W0 — exaggerated low so it's unambiguously the lowest bar in its neighbourhood
    candles.append(_candle(w0_price, lo_offset=2.0))

    # Monotonic rally W0 → W1 (serves as right-side confirmation for W0)
    candles += _ramp(w0_price + 1, w1_price - 1, 9)

    # W1 — exaggerated high
    candles.append(_candle(w1_price, hi_offset=2.0))

    # Monotonic pullback W1 → W2 (serves as right-side confirmation for W1)
    # Must be descending — guaranteed by the assert above.
    candles += _ramp(w1_price - 1, w2_price + 1, 9)

    # W2 — exaggerated low
    candles.append(_candle(w2_price, lo_offset=2.0))

    # Monotonic rise from W2 to entry (pivot_right bars confirm W2, entry is the ceiling)
    # Must stay strictly increasing so no peak forms before entry.
    steps = pivot_right + 1
    step_up = (entry_price - w2_price) / steps
    for i in range(1, pivot_right + 1):
        candles.append(_candle(w2_price + step_up * i))
    candles.append(_candle(entry_price))

    return candles


def _build_downtrend_wave(
    w0_price: float = 120.0,
    w1_price: float = 100.0,
    w2_price: float = 108.0,
    entry_price: float = 107.0,
    n_padding: int = 20,
    pivot_right: int = 3,
) -> list[dict]:
    """Build a clean W0(high)→W1(low)→W2(high)→entry downtrend sequence."""
    assert entry_price < w2_price, "entry_price must be below W2 for a short setup"

    candles: list[dict] = []

    candles += _flat(w0_price - 5, n_padding)

    # Ascend to W0 (3 bars — left confirmation)
    candles += _ramp(w0_price - 3, w0_price - 1, 3)
    candles.append(_candle(w0_price, hi_offset=2.0))

    # Monotonic drop W0 → W1
    candles += _ramp(w0_price - 1, w1_price + 1, 9)

    candles.append(_candle(w1_price, lo_offset=2.0))

    # Monotonic bounce W1 → W2
    candles += _ramp(w1_price + 1, w2_price - 1, 9)

    candles.append(_candle(w2_price, hi_offset=2.0))

    # Monotonic fall from W2 to entry (pivot_right bars confirm W2)
    steps = pivot_right + 1
    step_dn = (w2_price - entry_price) / steps
    for i in range(1, pivot_right + 1):
        candles.append(_candle(w2_price - step_dn * i))
    candles.append(_candle(entry_price))

    return candles


# Params shared by all structural tests: bypass the min_pivots production guard
_P = {"min_pivots": 3}


# ── Pivot unit tests ──────────────────────────────────────────────────────────

def test_pivot_detection_clean_low():
    """Monotonic descent → low → monotonic ascent produces exactly one pivot low."""
    candles = _ramp(110, 100, 5) + [_candle(95, lo_offset=3)] + _ramp(100, 110, 5)
    pivots = _find_pivots(candles, left=3, right=3)
    lows = [p for p in pivots if p.kind == "low"]
    assert len(lows) == 1, f"Expected 1 pivot low, got {len(lows)}"
    assert lows[0].price < 93, f"Expected low < 93, got {lows[0].price}"


def test_pivot_detection_clean_high():
    """Monotonic ascent → high → monotonic descent produces exactly one pivot high."""
    candles = _ramp(100, 110, 5) + [_candle(115, hi_offset=3)] + _ramp(110, 100, 5)
    pivots = _find_pivots(candles, left=3, right=3)
    highs = [p for p in pivots if p.kind == "high"]
    assert len(highs) == 1, f"Expected 1 pivot high, got {len(highs)}"
    assert highs[0].price > 117, f"Expected high > 117, got {highs[0].price}"


def test_monotonic_ramp_no_pivots():
    """A strictly ascending ramp cannot contain any confirmed pivot (high or low)."""
    candles = _ramp(100, 150, 30)
    pivots = _find_pivots(candles, left=3, right=3)
    assert pivots == [], f"Expected no pivots in a ramp, got {pivots}"


# ── Strategy signal tests ─────────────────────────────────────────────────────

def test_valid_w3_long():
    """
    Uptrend: W0=100, W1=120, W2=112 (≈40% retrace after offsets).
    Entry at 113 (above W2). Expect LONG signal with TP near 161.8% extension.
    """
    candles = _build_uptrend_wave(
        w0_price=100, w1_price=120, w2_price=112, entry_price=113
    )
    sig = evaluate(candles, {**_P})
    assert sig.action == "long", f"Expected 'long', got '{sig.action}' | {sig.reason}"
    assert sig.stop_loss < sig.w2, f"Stop should be below W2 ({sig.w2:.2f}), got {sig.stop_loss}"
    assert sig.take_profit > 113, f"TP should be above entry"
    # 161.8% of ~22pt W1 from W2 ≈ 146. Give a generous lower bound.
    assert sig.take_profit > 135, f"TP too low: {sig.take_profit}"
    assert 23.6 <= sig.retracement_pct <= 78.6, f"Retrace out of range: {sig.retracement_pct}"


def test_valid_w3_short():
    """
    Downtrend: W0=120, W1=100, W2=108 (≈40% retrace).
    Entry at 107 (below W2). Expect SHORT signal.
    """
    candles = _build_downtrend_wave(
        w0_price=120, w1_price=100, w2_price=108, entry_price=107
    )
    sig = evaluate(candles, {**_P})
    assert sig.action == "short", f"Expected 'short', got '{sig.action}' | {sig.reason}"
    assert sig.stop_loss > sig.w2, f"Stop should be above W2 ({sig.w2:.2f}), got {sig.stop_loss}"
    assert sig.take_profit < 107, f"TP should be below entry"
    # 161.8% extension ≈ 74. Give generous upper bound.
    assert sig.take_profit < 85, f"TP too high: {sig.take_profit}"
    assert 23.6 <= sig.retracement_pct <= 78.6


def test_ewt_rule_a_w2_exceeds_w0():
    """
    EWT Rule A: W2 must not break below W0 in an uptrend.
    W0=100, W1=120, W2=99 → Rule A violated → 'none'.
    """
    candles = _build_uptrend_wave(
        w0_price=100, w1_price=120, w2_price=99, entry_price=100
    )
    sig = evaluate(candles, {**_P})
    assert sig.action == "none", f"Expected 'none' (W2 breaks W0), got '{sig.action}' | {sig.reason}"
    assert "EWT violated" in sig.reason, f"Reason should mention EWT: {sig.reason}"


def test_retracement_too_shallow():
    """
    W0=100, W1=200, W2=195 → 5/100 = 5% retrace, well below 23.6% minimum.
    Using a large W1 range so the pullback (200→195) is clearly descending.
    """
    candles = _build_uptrend_wave(
        w0_price=100, w1_price=200, w2_price=195, entry_price=196
    )
    sig = evaluate(candles, {**_P})
    assert sig.action == "none", f"Expected 'none' (shallow), got '{sig.action}' | {sig.reason}"
    assert "shallow" in sig.reason, f"Reason should say 'shallow': {sig.reason}"


def test_retracement_too_deep():
    """
    W2=101 gives >90% retrace → above 78.6% maximum.
    """
    candles = _build_uptrend_wave(
        w0_price=100, w1_price=120, w2_price=101, entry_price=102
    )
    sig = evaluate(candles, {**_P})
    assert sig.action == "none", f"Expected 'none' (too deep), got '{sig.action}' | {sig.reason}"
    assert "deep" in sig.reason, f"Reason should say 'deep': {sig.reason}"


def test_not_enough_candles():
    candles = [_candle(100)] * 5
    sig = evaluate(candles)
    assert sig.action == "none"
    assert "candle" in sig.reason.lower()


def test_no_wave_structure():
    """A monotonically rising series has no pivot alternation → no wave structure."""
    candles = _ramp(100, 200, 80)
    sig = evaluate(candles)
    assert sig.action == "none"


def test_golden_zone_flagged():
    """
    W2=110 → 50% retrace → squarely in golden zone (38.2%–61.8%).
    If a long signal fires, 'golden zone' must appear in the reason.
    """
    candles = _build_uptrend_wave(
        w0_price=100, w1_price=120, w2_price=110, entry_price=111
    )
    sig = evaluate(candles, {**_P})
    if sig.action == "long":
        assert "golden zone" in sig.reason, f"Expected 'golden zone': {sig.reason}"


def test_custom_retracement_range_rejects():
    """
    Custom params: allow only 60%–78.6%.
    The ~46% retrace from the standard uptrend wave falls outside → 'none'.
    """
    candles = _build_uptrend_wave(
        w0_price=100, w1_price=120, w2_price=112, entry_price=113
    )
    sig = evaluate(candles, {**_P, "retracement_lo": 60.0, "retracement_hi": 78.6})
    assert sig.action == "none", f"Expected 'none' with tight range, got '{sig.action}'"


def test_ewt_rule_a_downtrend():
    """
    Downtrend: W2 must not break above W0.
    W0=120 (high), W1=100 (low), W2=121 (exceeds W0) → Rule A violated.
    """
    candles = _build_downtrend_wave(
        w0_price=120, w1_price=100, w2_price=121, entry_price=120
    )
    sig = evaluate(candles, {**_P})
    assert sig.action == "none", f"Expected 'none' (W2 breaks W0 downtrend), got '{sig.action}'"
    assert "EWT violated" in sig.reason, f"Reason: {sig.reason}"


if __name__ == "__main__":
    tests = [
        test_pivot_detection_clean_low,
        test_pivot_detection_clean_high,
        test_monotonic_ramp_no_pivots,
        test_valid_w3_long,
        test_valid_w3_short,
        test_ewt_rule_a_w2_exceeds_w0,
        test_retracement_too_shallow,
        test_retracement_too_deep,
        test_not_enough_candles,
        test_no_wave_structure,
        test_golden_zone_flagged,
        test_custom_retracement_range_rejects,
        test_ewt_rule_a_downtrend,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
    if failed:
        raise SystemExit(1)
