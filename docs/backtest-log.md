# Backtest Log

Running record of Formula Lab backtests (`/lab/backtest`, `/lab/compare`) against real Binance historical data. Append-only — do not overwrite prior entries. Job results themselves expire from Redis after 7 days; this file is the permanent record.

---

## 2026-08-16 — First real backtest validation run

**Method:** `POST /lab/compare` (single job, default params for every strategy — no tuning applied).

**Request:**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "months": 6,
  "initial_balance": 10000,
  "leverage": 3,
  "risk_pct": 0.01,
  "strategies": ["rsi", "combined", "macd", "supertrend"]
}
```
- job_id: `1e08ad27-95a6-4f3b-b5ab-7e69e7df2c52`
- Actual trade/equity date range covered by the job (per equity_times/trade timestamps): **2026-02-27 → 2026-08-16** (~6 months, UTC)

**Results (default params, no tuning):**

| Strategy | Trades | Wins | Losses | Win rate | Total PnL % | Final balance | Max drawdown % | Avg RR |
|---|---|---|---|---|---|---|---|---|
| supertrend | 80 | 30 | 50 | 37.50% | +9.75% | $10,974.90 | 8.00% | 1.49 |
| macd | 147 | 51 | 96 | 34.69% | +5.33% | $10,532.98 | 12.67% | 0.41 |
| rsi | 314 | 101 | 213 | 32.17% | -15.72% | $8,427.93 | 45.83% | 0.43 |
| combined | 1232 | 374 | 858 | 30.36% | -59.09% | $4,091.30 | 75.97% | 0.36 |

**Equity curve shape (downsampled, for regime context — not an interpretation of tradability):**
- `supertrend`: choppy grind, mostly sideways-to-up drift, no severe drawdown episode (10,000 → ~11,700 peak in July → 10,975 by Aug 16).
- `macd`: sideways/range-bound the whole window, ends roughly flat (~+5%).
- `rsi`: sharp drop Mar–Apr (10,000 → ~6,200 by late April), partial recovery, ends down -15.72%.
- `combined`: strong run-up Feb–Apr (10,000 → ~14,000 peak), then a sustained multi-month bleed Apr–Jul (14,000 → ~4,100), i.e. it caught an uptrend then gave everything back plus more in what looks like a trend reversal/chop period afterward.
- All four strategies were run over the *same* BTCUSDT 1h window, so the divergence in outcome (supertrend/macd flat-to-positive vs. rsi/combined deeply negative) reflects each strategy's rule differences reacting to the same underlying price action, not different market conditions.

**Data/testing notes:**
- 6-month window only — this is one BTCUSDT regime (net range/uptrend-then-reversal per the equity curves above); none of these results are validated across bull/bear/sideways cycles independently.
- Default strategy params only, per the run instructions — no tuning was attempted.
- Not evaluated: strategy suitability for testnet or live use — that determination belongs to `lucy-trading-lead` / `lucy-trading-execution`, not this log entry.

**Not tested this run:** fibonacci, bollinger, elliott_wave, triple_ema_stoch_rsi, three_golden — out of scope per this run's instructions (only rsi, combined, macd, supertrend requested).
