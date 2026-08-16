"""
Combined Score strategy — the real edge.

Runs all 5 sub-strategies simultaneously and aggregates their signals into
a single weighted vote. Fires a trade only when the weighted score in one
direction clears a threshold AND there is no significant opposing vote.

Why this matters:
  Each strategy has a regime where it works and a regime where it fails.
  RSI is great in ranging markets but whipsaws in trends. MACD is great in
  trends but gives late entries in ranges. Elliott Wave fires rarely but with
  high confidence. By weighting each strategy by its recent win rate, the
  combined score automatically shifts authority toward whichever approach is
  working right now — without manual tuning or regime detection code.

Score calculation:
  long_score  = Σ weight_i  for each strategy_i that fires LONG
  short_score = Σ weight_i  for each strategy_i that fires SHORT

  win rate weight: passed in via params as {strategy}_weight (0.0–1.0)
  Default 0.5 (neutral) when no trade history exists for that strategy.

Entry decision:
  LONG  if long_score  >= threshold AND short_score <= conflict_max
  SHORT if short_score >= threshold AND long_score  <= conflict_max
  NONE  otherwise (not strong enough, or directional conflict)

  conflict_max is the maximum allowed OPPOSING score.
  If the opposing side scores above this, strategies disagree and we skip —
  e.g. RSI says oversold (long) but MACD says bearish trend (short). Better
  to skip than pick a side in a confused market.

SL/TP anchor:
  Uses the signal from the highest-weighted strategy that voted for the
  winning direction (the "anchor"). This ensures risk parameters come from
  the most currently reliable strategy.

Default params:
  threshold           float = 0.6   — minimum weighted score to fire
  conflict_max        float = 0.15  — max opposing score (above this = skip)
  rsi_weight          float = 0.5   — overridden by bot_tasks from DB
  macd_weight         float = 0.5
  fibonacci_weight    float = 0.5
  bollinger_weight    float = 0.5
  elliott_wave_weight float = 0.5

BUGFIX (2026-08-16, backtest round 3): threshold was 0.3, which is BELOW a
single sub-strategy's default neutral weight (0.5). That meant any ONE
sub-strategy firing alone, with zero opposition, already cleared the
threshold — the "weighted vote requiring confluence" this module's docstring
describes never actually applied. In practice this made `combined` behave
as an OR of all 5 sub-strategies' raw signals (worse than any single one,
since it inherited every strategy's whipsaws). Confirmed via
BTCUSDT/1h/6mo backtest: 1232 trades, -59% PnL, 76% drawdown — while the
best individual sub-strategy (supertrend, not even wrapped by combined)
produced 80 trades and RSI alone produced 314.
Raised threshold to 0.6 so that either (a) two neutral (0.5-weight)
strategies must agree, since 2*0.5=1.0 > 0.6 but 1*0.5=0.5 < 0.6, or
(b) a single strategy with a genuinely proven win-rate weight >= 0.6 can
act alone once it has track record. See docs/backtest-log.md Round 3 for
the validation backtest after this change.
"""
from dataclasses import dataclass, field
from typing import Literal, Optional, List

from app.modules.bot.strategies import rsi as _rsi
from app.modules.bot.strategies import macd as _macd
from app.modules.bot.strategies import fibonacci as _fib
from app.modules.bot.strategies import bollinger as _bb
from app.modules.bot.strategies import elliott_wave as _ewt


_STRATEGY_MODULES = {
    "rsi":          _rsi,
    "macd":         _macd,
    "fibonacci":    _fib,
    "bollinger":    _bb,
    "elliott_wave": _ewt,
}


@dataclass
class SubResult:
    strategy: str
    action: str       # "long" | "short" | "none"
    weight: float
    signal: object    # the raw sub-strategy Signal (any of the five dataclasses)


@dataclass
class Signal:
    action: Literal["long", "short", "none"]
    entry_price: float
    stop_loss: float
    take_profit: float
    long_score: float
    short_score: float
    contributing: List[str]   # names of strategies that voted for the winning direction
    anchor: str               # strategy whose SL/TP values are used
    sub_results: List[SubResult]
    reason: str


def evaluate(candles: list, params: Optional[dict] = None) -> Signal:
    """
    Given OHLCV candles (newest last), run all five sub-strategies and return
    a combined weighted signal.

    params keys (all optional):
      threshold, conflict_max,
      rsi_weight, macd_weight, fibonacci_weight, bollinger_weight, elliott_wave_weight
    """
    p = params or {}
    threshold    = float(p.get("threshold", 0.6))
    conflict_max = float(p.get("conflict_max", 0.15))

    weights = {
        "rsi":          float(p.get("rsi_weight", 0.5)),
        "macd":         float(p.get("macd_weight", 0.5)),
        "fibonacci":    float(p.get("fibonacci_weight", 0.5)),
        "bollinger":    float(p.get("bollinger_weight", 0.5)),
        "elliott_wave": float(p.get("elliott_wave_weight", 0.5)),
    }

    # ── Run each sub-strategy ─────────────────────────────────────────────────
    sub_results: list[SubResult] = []
    for name, module in _STRATEGY_MODULES.items():
        sig = module.evaluate(candles, p)
        sub_results.append(SubResult(
            strategy=name,
            action=sig.action,
            weight=weights[name],
            signal=sig,
        ))

    # ── Aggregate scores ──────────────────────────────────────────────────────
    long_score  = sum(r.weight for r in sub_results if r.action == "long")
    short_score = sum(r.weight for r in sub_results if r.action == "short")

    none_signal = Signal(
        action="none",
        entry_price=candles[-1]["close"] if candles else 0,
        stop_loss=0, take_profit=0,
        long_score=round(long_score, 3),
        short_score=round(short_score, 3),
        contributing=[], anchor="",
        sub_results=sub_results,
        reason="",
    )

    # ── Direction decision ────────────────────────────────────────────────────
    # conflict_max: the MAXIMUM allowed opposing score.
    # If the opposing side has a score above this, two strategies disagree strongly
    # enough that we skip the trade rather than pick a side.
    winning_direction: Optional[str] = None

    if long_score >= threshold and short_score <= conflict_max:
        winning_direction = "long"
    elif short_score >= threshold and long_score <= conflict_max:
        winning_direction = "short"
    else:
        if long_score < threshold and short_score < threshold:
            reason = (
                f"Score too low — long={long_score:.2f}, short={short_score:.2f} "
                f"(threshold={threshold})"
            )
        else:
            reason = (
                f"Directional conflict — long={long_score:.2f}, short={short_score:.2f} "
                f"(opposing score exceeds conflict_max={conflict_max})"
            )
        none_signal.reason = reason
        return none_signal

    # ── Select anchor (highest weight among voters in winning direction) ───────
    voters = [r for r in sub_results if r.action == winning_direction]
    if not voters:
        none_signal.reason = f"Score cleared threshold but no strategy voted {winning_direction}"
        return none_signal
    anchor = max(voters, key=lambda r: r.weight)

    anchor_sig = anchor.signal
    entry  = anchor_sig.entry_price
    sl     = anchor_sig.stop_loss
    tp     = anchor_sig.take_profit

    if sl == 0 or tp == 0 or entry == 0:
        none_signal.reason = f"Anchor strategy '{anchor.strategy}' returned invalid SL/TP"
        return none_signal

    contributing = [r.strategy for r in voters]
    score = long_score if winning_direction == "long" else short_score

    reason = (
        f"Combined {winning_direction.upper()} — score={score:.2f} "
        f"(long={long_score:.2f}, short={short_score:.2f}) | "
        f"voters=[{', '.join(contributing)}] | anchor={anchor.strategy}"
    )

    return Signal(
        action=winning_direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        long_score=round(long_score, 3),
        short_score=round(short_score, 3),
        contributing=contributing,
        anchor=anchor.strategy,
        sub_results=sub_results,
        reason=reason,
    )
