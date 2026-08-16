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

---

## 2026-08-16 — Symbol/timeframe breadth check for supertrend and rsi

**Purpose:** The 2026-08-16 run above tested BTCUSDT/1h only — one symbol, one timeframe, one 6-month window. This round asks: (1) does `supertrend`'s positive BTCUSDT/1h result hold on ETHUSDT/SOLUSDT? (2) `rsi`'s own docstring default is `timeframe="15m"` — does it do better on its documented native timeframe than the 1h test it was run on before?

**Method:** `POST /lab/compare` with `"strategies": ["rsi", "supertrend"]`, default params (no tuning — `params: {}` in every request, so both strategies ran on their file-documented defaults). `initial_balance=10000, leverage=3, risk_pct=0.01` throughout, matching the prior round.

**Params confirmed from source (`backend/app/modules/bot/strategies/`):**
- `rsi.py`: docstring defaults `period=14, oversold=30, overbought=70, timeframe="15m"`. `evaluate()` param defaults: `rsi_period=14, oversold=30, overbought=70, atr_period=14, atr_multiplier=1.0, rr_ratio=2.0`.
- `supertrend.py`: `atr_period=10, atr_multiplier=3.0, rr_ratio=2.0`.

**Cells cited from the prior 2026-08-16 entry (not re-run):**
- BTCUSDT / 1h / supertrend — 80 trades, 37.50% win rate, +9.75% PnL, 8.00% max DD, avg RR 1.49
- BTCUSDT / 1h / rsi — 314 trades, 32.17% win rate, -15.72% PnL, 45.83% max DD, avg RR 0.43

**Cells newly run this round (5 `/lab/compare` jobs, 2 strategies each = 10 cells):**

| Symbol | TF | Strategy | Trades | Win % | PnL % | Max DD % | Avg RR | Date range | Job status |
|---|---|---|---|---|---|---|---|---|---|
| ETHUSDT | 1h | supertrend | 81 | 38.27 | +8.09 | 7.75 | 1.98 | 2026-02-27 → 2026-08-16 | done |
| ETHUSDT | 1h | rsi | 326 | 37.12 | +34.29 | 23.25 | 0.65 | 2026-02-27 → 2026-08-16 | done |
| SOLUSDT | 1h | supertrend | 81 | 37.04 | +4.88 | 8.50 | 2.16 | 2026-02-27 → 2026-08-16 | done |
| SOLUSDT | 1h | rsi | 271 | 33.21 | -6.35 | 27.38 | 0.67 | 2026-02-27 → 2026-08-16 | done |
| BTCUSDT | 15m | supertrend | 358 | 34.36 | +4.72 | 23.52 | 0.75 | 2026-02-19 → 2026-08-16 | done |
| BTCUSDT | 15m | rsi | 1171 | 30.23 | -72.66 | 77.70 | 0.24 | 2026-02-19 → 2026-08-16 | done |
| ETHUSDT | 15m | supertrend | 345 | 35.65 | +24.52 | 12.58 | 0.98 | 2026-02-19 → 2026-08-16 | done |
| ETHUSDT | 15m | rsi | 1139 | 32.92 | -30.62 | 50.96 | 0.34 | 2026-02-19 → 2026-08-16 | done |
| SOLUSDT | 15m | supertrend | 346 | 33.24 | -6.30 | 20.18 | 1.09 | 2026-02-19 → 2026-08-16 | done |
| SOLUSDT | 15m | rsi | 1122 | 32.89 | -30.69 | 47.42 | 0.36 | 2026-02-19 → 2026-08-16 | done |

**Full matrix (12 cells, all BTCUSDT/ETHUSDT/SOLUSDT x 15m/1h x supertrend/rsi):**

| Symbol | TF | supertrend PnL% / maxDD% / RR / trades | rsi PnL% / maxDD% / RR / trades |
|---|---|---|---|
| BTCUSDT | 1h | +9.75 / 8.00 / 1.49 / 80 (cited) | -15.72 / 45.83 / 0.43 / 314 (cited) |
| ETHUSDT | 1h | +8.09 / 7.75 / 1.98 / 81 | +34.29 / 23.25 / 0.65 / 326 |
| SOLUSDT | 1h | +4.88 / 8.50 / 2.16 / 81 | -6.35 / 27.38 / 0.67 / 271 |
| BTCUSDT | 15m | +4.72 / 23.52 / 0.75 / 358 | -72.66 / 77.70 / 0.24 / 1171 |
| ETHUSDT | 15m | +24.52 / 12.58 / 0.98 / 345 | -30.62 / 50.96 / 0.34 / 1139 |
| SOLUSDT | 15m | -6.30 / 20.18 / 1.09 / 346 | -30.69 / 47.42 / 0.36 / 1122 |

**15m data volume note:** all three 15m jobs completed successfully in one shot (`/lab/backtest`'s Binance klines fetch paginates internally at 1500 candles/request) — no pagination failures, timeouts, or fallback to a shorter window were needed. Actual date range returned was 2026-02-19 → 2026-08-16 (~179 days, consistent with the `months=6` request and Binance's futures listing/liquidity limits) vs 2026-02-27 → 2026-08-16 (~170 days) for the 1h requests — both are the requested ~6-month window, the few-day difference is just candle-availability rounding, not a shortfall.

**Regime caveat:** all 12 cells cover the *same* calendar window (Feb–Aug 2026) across BTC/ETH/SOL, which are highly correlated assets. Running more symbols increases confidence that a result isn't a single-asset fluke, but it does **not** substitute for testing a different market regime (different bull/bear/chop cycle) — that axis is still untested. Equity curves show peaks concentrated mid-to-late window for 1h supertrend (broadly consistent with the prior log's characterization of a choppy uptrend into a partial reversal) and, for rsi at 15m, an early peak (within the first 1-3% of trades) followed by a near-continuous bleed for the rest of the window on all three symbols — i.e. rsi's few early wins are erased by a long losing stretch, not offset by later recovery.

**supertrend read:** positive on 5 of 6 symbol/TF cells (only SOLUSDT/15m is negative), with the 1h timeframe consistently better than 15m on every metric that matters (lower max DD: 7.75-8.50% vs 12.58-23.52%; higher avg RR: 1.49-2.16 vs 0.75-1.09). Trade counts are adequate everywhere (81-358, well above the ~20-30 threshold). This is now a 3-symbol, 1h-consistent, modestly-positive result — meaningfully stronger evidence than the single BTCUSDT cell from the prior round, but still confined to one 6-month calendar window/regime.

**rsi read:** negative-to-catastrophic everywhere except one outlier (ETHUSDT/1h +34.29%, but with 23.25% max DD — a rough ride for the return). On its own documented native timeframe (15m), rsi is unambiguously worse than on 1h: -72.66% PnL / 77.70% max DD on BTCUSDT, -30.62% on ETHUSDT, -30.69% on SOLUSDT, all with 1100+ trades (statistically meaningful sample, just meaningfully bad) and avg RR well under 1 (0.24-0.36). The hypothesis that 1h was "the wrong timeframe" for rsi is not supported — 15m is worse, not better. rsi mean-reversion logic appears to overtrade on noisy short-interval data and get chopped up by stop-losses at a higher rate than TPs.

**Not tested this round:** any timeframe/symbol combination for the other 7 strategies (macd, fibonacci, bollinger, elliott_wave, combined, triple_ema_stoch_rsi, three_golden) — out of scope per this round's instructions. No different calendar window/regime was tested — all 12 cells share the same Feb-Aug 2026 period. No param tuning was attempted on any cell.

