"""
VI scoring logic. Takes raw yfinance metrics dict, returns (score 0-100, verdict).

Scoring weights (total = 100 pts):
  PE ratio < 15          → 15 pts  (cheap relative to earnings)
  PB ratio < 1.5         → 15 pts  (asset-backed value)
  Debt/Equity < 50       → 15 pts  (yfinance returns D/E as %; 50 = 0.5 ratio)
  ROE > 15%              → 15 pts  (management quality, Peter Lynch threshold)
  Revenue growth > 10%   → 15 pts  (growth, not a value trap)
  Free cash flow > 0     → 15 pts  (real earnings, not accounting illusion)
  Insider ownership > 5% → 10 pts  (skin in the game)

Hidden gem bonus (+5, capped at 100):
  Market cap < $2B AND analyst coverage < 5 firms
"""
from typing import Optional


def score_stock(metrics: dict) -> tuple[float, str]:
    score = 0.0
    max_score = 0.0

    def check(key: str, condition_fn, points: float):
        nonlocal score, max_score
        val = metrics.get(key)
        if val is None:
            return
        max_score += points
        if condition_fn(val):
            score += points

    check("pe_ratio", lambda v: 0 < v < 15, 15)
    check("pb_ratio", lambda v: v < 1.5, 15)
    check("debt_to_equity", lambda v: v < 50, 15)   # yfinance: % form (50 = 0.5 ratio)
    check("roe", lambda v: v > 0.15, 15)             # yfinance: decimal (0.15 = 15%)
    check("revenue_growth", lambda v: v > 0.10, 15)  # yfinance: decimal (0.10 = 10%)
    check("free_cash_flow", lambda v: v > 0, 15)
    check("insider_ownership", lambda v: v > 0.05, 10)  # yfinance: decimal (0.05 = 5%)

    normalized = (score / max_score * 100) if max_score > 0 else 0

    # Hidden gem bonus: small-cap + underfollowed
    market_cap = metrics.get("market_cap")
    analyst_count = metrics.get("analyst_count")
    is_hidden_gem = (
        market_cap is not None
        and market_cap < 2_000_000_000
        and (analyst_count is None or analyst_count < 5)
    )
    if is_hidden_gem:
        normalized = min(100, normalized + 5)

    return round(normalized, 1), _verdict(normalized)


def _verdict(score: float) -> str:
    if score >= 75:
        return "strong_buy"
    elif score >= 55:
        return "buy"
    elif score >= 35:
        return "hold"
    return "skip"
