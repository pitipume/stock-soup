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

## 2026-08-16 — Combined strategy bugfix validation (threshold 0.3 -> 0.6)

**Purpose:** Lucy (lead) diagnosed the `combined` strategy's catastrophic Round 1 result (1232 trades, -59.09% PnL, 75.97% max DD) as caused by a default `threshold=0.3` that was below a single sub-strategy's flat 0.5 backtester weight — meaning any one of the 5 sub-strategies firing alone, with zero confluence, already cleared the "confluence" threshold. Fix applied to `backend/app/modules/bot/strategies/combined.py`: default `threshold` raised 0.3 -> 0.6 (docstring and `evaluate()` `p.get("threshold", 0.6)` both updated). `conflict_max` (0.15) unchanged. This round validates the fix using the exact same request as Round 1 (BTCUSDT/1h/6mo, `params: {}` so the new 0.6 default is what actually runs), no other params changed.

**Important operational note — first run was stale, had to rebuild containers:**
The first attempt at this validation (`job_id: 22db42e0-1cd7-404e-ab66-2f418641f595`) returned metrics byte-identical to the old broken Round 1 numbers (1232 trades, -59.09%, 75.97% DD) even though the fix was already present in `combined.py` on disk. Investigation: `docker-compose.yml` (the file `docker-compose up -d` uses by default) has no source volume mount for `backend`/`worker` — code is baked into the image at build time (`build: ./backend`), consistent with the known "code is baked into the image" caveat already documented in the repo's root `CLAUDE.md`. The running containers (up 27 min at time of test) predated the code fix and were serving stale strategy logic. Ran `docker-compose up -d --build backend worker` to rebuild both images, confirmed via `docker exec ... grep threshold` that the rebuilt container's `combined.py` shows `threshold = float(p.get("threshold", 0.6))`, then re-ran the identical request. **Anyone re-testing after a code change to a strategy file must rebuild (`--build`), not just resubmit a job — a plain restart or a fresh job on stale containers will silently return pre-fix numbers.**

**Request (both runs, identical):**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "strategy": "combined",
  "params": {},
  "months": 6,
  "initial_balance": 10000,
  "leverage": 3,
  "risk_pct": 0.01
}
```
- Pre-rebuild (stale code) job_id: `22db42e0-1cd7-404e-ab66-2f418641f595` — discarded, not valid evidence of the fix, included here only for the operational lesson above.
- **Post-rebuild (actual fix) job_id: `e78fd0a1-423f-4075-a2ff-280863ed415b`**
- Trade/equity date range: **2026-02-27 -> 2026-08-16** (equity curve start) / trades themselves ran **2026-03-02 -> 2026-08-16** (~6 months, UTC) — same window as Round 1, so this is an apples-to-apples comparison.

**Results — old (broken, threshold=0.3) vs new (fixed, threshold=0.6):**

| Metric | Old (Round 1, threshold=0.3) | New (this round, threshold=0.6) | Change |
|---|---|---|---|
| Total trades | 1232 | 189 | -84.7% (massively fewer) |
| Wins | 374 | 63 | |
| Losses | 858 | 126 | |
| Win rate | 30.36% | 33.33% | +2.97 pp |
| Total PnL % | -59.09% | -2.27% | +56.82 pp improvement |
| Final balance | $4,091.30 | $9,772.84 | |
| Max drawdown % | 75.97% | 17.80% | -58.17 pp (much shallower) |
| Avg RR | 0.36 | 0.33 | -0.03 (slightly worse) |

**Equity curve shape (post-fix, 310 points sampled):** Starts $10,000 (2026-02-27), dips to a trough of $8,802 (2026-04-26), recovers and grinds up to a peak of $10,943 (2026-06-16), then chops back down through July/August, ending at $9,772.84 (2026-08-16, -2.27%). This is a choppy, range-bound, no-clear-trend curve — the strategy oscillates roughly +/-10% around the starting balance the whole window rather than either riding a clean trend or bleeding out continuously. This reads as consistent with a sideways/choppy BTC regime over Feb-Aug 2026, not a strong trend in either direction (contrast with Round 1's broken curve, which had a sharp Feb-Apr runup to $14k then a continuous Apr-Jul bleed to $4.1k — that shape is gone now).

**Assessment — honest, not spun:**
- **The fix worked as diagnosed.** Trade count dropped 84.7% (1232 -> 189), confirming the threshold bug was in fact causing the strategy to fire on any single sub-strategy signal rather than requiring confluence. This is the single most important result of this validation.
- **Max drawdown improved dramatically** (75.97% -> 17.80%) — the strategy is no longer catastrophically over-leveraged into losing streaks.
- **The strategy is still net-negative, not net-positive.** -2.27% over 6 months is a real loss, not a rounding error. It is "net-negative-but-sane" rather than "still broken" — the fix eliminated the overtrading blowup, but did not turn `combined` into a working alpha-generating strategy. Avg RR (0.33) is still well under 1, meaning average losses are larger than average wins even with a 33.33% win rate — the math does not currently produce positive expectancy.
- **Trade count (189) is now statistically meaningful** (well above the ~20-30 minimum), a genuine improvement over Round 1's noisy 1232-trade churn, so this -2.27% result is more trustworthy as a signal of the strategy's real edge (or lack thereof) than Round 1's number ever was.
- **Regime caveat unchanged:** still a single 6-month BTCUSDT/1h calendar window (Feb-Aug 2026), now characterized as choppy/range-bound per the equity curve above. Not tested in a trending or high-volatility regime.

**Recommendation:** The threshold fix is confirmed working and should stay in place — it fixed a genuine confluence-logic bug, not just a symptom. However, `combined` at its current fixed default is not yet credible for testnet or a live alert: it is flat-to-slightly-negative over the one regime tested, with sub-1 avg RR. This is evidence to bring to `lucy-trading-lead`/`lucy-trading-execution` as "bug confirmed fixed, but strategy itself unproven as profitable" — not as "ready to deploy." Testing across a trending regime (not just this one choppy window) would be needed before drawing further conclusions either way.

---
## 2026-08-16 — Six untested strategies: BTCUSDT, 15m and 1h, 6 months, default params

**Purpose:** Baseline-test the 6 strategies not yet covered by any prior log round — `macd`, `bollinger`, `fibonacci`, `three_golden`, `triple_ema_stoch_rsi`, `elliott_wave` — on BTCUSDT across both 15m and 1h timeframes, default params, no tuning. Combined with the existing `rsi`/`supertrend`/`combined` rounds, this completes first-pass coverage of all 9 strategies the lab supports.

**Method:** `POST /lab/compare`, one job per timeframe, all 6 strategies batched together. `initial_balance=10000, leverage=3, risk_pct=0.01`, `params: {}` (file-documented defaults only) for every strategy in both jobs.

**Requests:**
```json
{"symbol":"BTCUSDT","timeframe":"1h","months":6,"initial_balance":10000,"leverage":3,"risk_pct":0.01,
 "strategies":["macd","bollinger","fibonacci","three_golden","triple_ema_stoch_rsi","elliott_wave"]}
```
```json
{"symbol":"BTCUSDT","timeframe":"15m","months":6,"initial_balance":10000,"leverage":3,"risk_pct":0.01,
 "strategies":["macd","bollinger","fibonacci","three_golden","triple_ema_stoch_rsi","elliott_wave"]}
```
- 1h job_id: `e00b812d-43d3-4e7c-b8e0-017a812fcd8c` (date range 2026-02-28 → 2026-08-16)
- 15m job_id: `f49a157d-f19b-4ea1-bbcf-a7cca08ce2a7` (date range 2026-02-20 → 2026-08-16; took ~15-16 min to complete — 15m over 6 months is a much larger candle set than 1h, `fibonacci` and `elliott_wave` in particular were slow)
- Both jobs ran on the freshly rebuilt backend/worker images (see combined-fix validation entry above) — `macd`'s 1h result below (147 trades, +5.33% PnL) is byte-identical to its Round 1 number, confirming the rebuild did not silently change unrelated strategy behavior.

**Results — BTCUSDT / 1h / 6mo:**

| Strategy | Trades | Wins | Losses | Win rate | Total PnL % | Final balance | Max DD % | Avg RR | Date range |
|---|---|---|---|---|---|---|---|---|---|
| elliott_wave | 207 | 43 | 164 | 20.77% | +26.73% | $12,672.55 | 44.89% | 0.72 | 2026-03-01 → 2026-08-16 |
| macd | 147 | 51 | 96 | 34.69% | +5.33% | $10,532.98 | 12.87% | 0.41 | 2026-02-28 → 2026-08-16 |
| bollinger | 211 | 72 | 139 | 34.12% | +1.99% | $10,199.27 | 26.22% | 0.67 | 2026-02-28 → 2026-08-16 |
| three_golden | 313 | 103 | 209 | 32.91% | -6.39% | $9,360.55 | 22.44% | 0.40 | 2026-02-28 → 2026-08-16 |
| triple_ema_stoch_rsi | 157 | 49 | 108 | 31.21% | -9.89% | $9,011.14 | 19.91% | 0.38 | 2026-02-28 → 2026-08-16 |
| fibonacci | 1187 | 368 | 819 | 31.00% | -64.16% | $3,583.62 | 68.79% | 0.27 | 2026-02-28 → 2026-08-16 |

**Results — BTCUSDT / 15m / 6mo:**

| Strategy | Trades | Wins | Losses | Win rate | Total PnL % | Final balance | Max DD % | Avg RR | Date range |
|---|---|---|---|---|---|---|---|---|---|
| macd | 672 | 262 | 410 | 38.99% | +186.20% | $28,619.71 | 16.21% | 0.19 | 2026-02-20 → 2026-08-16 |
| triple_ema_stoch_rsi | 590 | 208 | 382 | 35.25% | +30.66% | $13,065.64 | 26.70% | 0.21 | 2026-02-20 → 2026-08-15 |
| three_golden | 1420 | 472 | 948 | 33.24% | -19.34% | $8,065.57 | 36.58% | 0.18 | 2026-02-20 → 2026-08-16 |
| bollinger | 892 | 285 | 607 | 31.95% | -41.71% | $5,829.39 | 59.08% | 0.31 | 2026-02-20 → 2026-08-16 |
| elliott_wave | 815 | 144 | 671 | 17.67% | -80.53% | $1,946.87 | 86.94% | 0.35 | 2026-02-20 → 2026-08-16 |
| fibonacci | 4423 | 1410 | 3013 | 31.88% | -93.90% | $609.70 | 97.05% | 0.19 | 2026-02-20 → 2026-08-16 |

**Equity curve / regime notes (1h):**
- `elliott_wave`: peak $14,954.5 on 2026-04-06, trough $8,241.5 on 2026-07-01, ends +26.73% — front-loaded gains (Feb-Apr) followed by a multi-month pullback that only partially reversed by August. Only 20.77% win rate carrying a positive total return means the wins are large relative to losses (avg RR 0.72, best of the six) — a trend-catching, low-hit-rate profile.
- `macd`: shallow range $9,308.6-$11,288.3, ends +5.33%, max DD 12.87% — mildly positive, low volatility, closest to Round 1's characterization of "sideways/range-bound the whole window."
- `bollinger`: wide swing (peak $12,770.3 on 2026-04-19, trough $9,316.8 on 2026-03-03) but ends barely positive (+1.99%) — big round trip with little net progress.
- `three_golden`, `triple_ema_stoch_rsi`: both chop in a ~$8,600-$11,150 band all window and end mildly negative.
- `fibonacci`: peak $10,649.2 on 2026-04-11 then a near-continuous bleed to a trough of $3,323.7 on 2026-08-03 — shape matches the pre-fix `combined` blowup curve (strong early run-up, then sustained multi-month bleed), and with 1187 trades at 1h this strategy shows the same overtrading signature Round 1's `combined` had before its threshold fix. **Not diagnosed or touched here** (out of scope for this backtesting round — code changes are Lucy's call), but flagged as a strong candidate for the same class of bug (signal fires too easily / no real confluence requirement) given the trade-count and drawdown pattern match.

**Equity curve / regime notes (15m):**
- `fibonacci` and `elliott_wave` are both catastrophic on 15m (-93.90% / 97.05% DD and -80.53% / 86.94% DD respectively), each with a clear early peak (Feb-Mar) followed by a near-total, multi-month bleed to a trough right near the end of the window (mid-August) — same "false early edge, then sustained overtrading bleed" shape as `fibonacci`'s 1h result and pre-fix `combined`. Trade counts (4423 and 815) are large — this is not noise, it is a consistent, repeatable failure mode across timeframes for `fibonacci` specifically.
- `bollinger` 15m is also markedly worse than its 1h result (-41.71% vs +1.99%, DD 59.08% vs 26.22%) with 4x the trade count — same direction of regression as `fibonacci`/`elliott_wave`, weaker in magnitude.
- `three_golden` is negative on both timeframes (-6.39% 1h, -19.34% 15m) — consistent, not a fluke of one timeframe, though not as severe as fibonacci/elliott_wave/bollinger's 15m blowups.
- `macd` and `triple_ema_stoch_rsi` are the only two strategies where 15m outperforms 1h, and by a very large margin (macd: +5.33% → +186.20%; triple_ema_stoch_rsi: -9.89% → +30.66%). **This divergence needs scrutiny, not blind acceptance.** Both 15m results carry avg RR well under 1 (0.19 and 0.21 respectively) combined with sub-40% win rates — in isolation that combination should produce negative expectancy per trade, yet the realized total return is strongly positive. The most likely explanation is compounding: `risk_pct=1%` sizes each trade off the *current* balance, and with 590-672 trades over 6 months, even a marginal per-trade edge compounds multiplicatively — small, frequent gains on a growing base can produce outsized cumulative % returns even while avg_rr looks unimpressive trade-by-trade. This is not necessarily wrong, but it is not verified either — it has not been checked against e.g. a fixed (non-compounding) position-sizing run, and a >2.5x-in-6-months result (macd) is the kind of thing that deserves independent confirmation (different window, different symbol) before anyone treats it as real edge rather than a compounding/backtest-mechanics artifact.

**Trade-count adequacy:** every cell in both tables clears the ~20-30 trade minimum by a wide margin (147-4423 trades) — none of these are too-few-signals results. The concern for several of these strategies is not sample size, it's magnitude of loss (fibonacci, elliott_wave, bollinger at 15m) or an unverified compounding effect (macd, triple_ema_stoch_rsi at 15m), not statistical insignificance.

**Regime caveat:** all 12 cells (this round) plus the earlier `rsi`/`supertrend`/`combined` cells all share the same Feb-Aug 2026 BTCUSDT calendar window. No strategy in this log has been tested across more than one market regime. The 1h equity curves this round read as choppy/range-bound-to-mild-uptrend for most strategies (consistent with the `combined`-fix entry's regime read), with `elliott_wave` catching enough of the early uptrend to post a positive 1h result despite a low win rate.

**Read — which of these 6 show promise vs which are clearly weak:**
- **Clearly weak / do not advance:** `fibonacci` (catastrophic on both timeframes, overtrading signature resembling the pre-fix combined bug — needs a code-level look before it's retested, not just parameter changes), `elliott_wave` on 15m (-80.53%, though its 1h result is a genuinely different, less bad picture — see below), `bollinger` on 15m (-41.71%, though its 1h result is closer to flat).
- **Mixed / timeframe-dependent, needs more evidence before either direction:** `elliott_wave` (1h positive +26.73% at only 20.77% win rate — a low-hit-rate/high-RR trend-catching profile that is plausible but rests on very few wins (43) relative to the total sample; 15m catastrophic). `bollinger` (1h roughly flat +1.99%, 15m badly negative -41.71%) `three_golden` (mildly negative on both timeframes — consistent but consistently bad, not "promising," listed here rather than "weak" only because the magnitude is smaller than fibonacci/elliott_wave/bollinger-15m).
- **Best of the six on raw numbers, but flagged for the compounding-artifact question above, not yet credible without follow-up:** `macd` (1h mildly positive +5.33%/12.87% DD — the more believable of its two results; 15m's +186.20% needs independent verification before anyone treats it as real), `triple_ema_stoch_rsi` (1h mildly negative -9.89%; 15m +30.66% — same compounding-verification caveat as macd).
- **None of the 6 clear the bar for testnet or a live alert on this evidence.** The two with positive headline numbers on 15m (macd, triple_ema_stoch_rsi) have an unresolved question about whether the return is a real edge or a backtest-mechanics artifact of compounding position sizing on a large trade count; the two with the worst numbers (fibonacci, elliott_wave-15m) look structurally broken in the same way `combined` was before its fix.

---

## 2026-08-16 — avg_rr metric bugfix (hardcoded 2% risk -> real per-trade stop distance) + supertrend reconciliation

**Trigger:** Round-1 execution-log entry flagged an unresolved concern — supertrend's reported avg_rr (1.49) at 37.5% win rate implied a slightly negative naive expectancy that didn't obviously reconcile with the reported +9.75% total PnL.

**Diagnosis (confirmed):** `backend/app/modules/lab/backtester.py`'s `run_backtest`, in the metrics section, computed `avg_rr` per trade using `risk = abs(t.entry_price - (t.entry_price * (1 - 0.02)))` — a **flat 2% of entry price**, applied identically to every trade regardless of strategy or actual stop distance. This is inconsistent with position sizing earlier in the same function, which correctly uses `stop_dist = abs(signal.entry_price - signal.stop_loss)` — the real per-trade stop distance. `BacktestTrade` (`backend/app/modules/lab/schemas.py`) did not store `stop_loss`, so the metrics section had no way to reference the real value and fell back to a guess.

**Fix applied:**
- `BacktestTrade` schema: added `stop_loss: float` field.
- `backtester.py`: both `BacktestTrade(...)` construction sites (SL/TP-hit close, and end-of-backtest forced close) now record `stop_loss=round(pos["stop_loss"], 4)` from the actual open position.
- `avg_rr` calc changed to `risk = abs(t.entry_price - t.stop_loss)` — the real stop distance — instead of the flat 2% guess.
- `frontend/src/lib/api.ts`: `BacktestTrade` interface updated to include `stop_loss: number` for consistency.
- Rebuilt `backend`/`worker` images (`docker-compose up -d --build backend worker`) — code is baked into images, confirmed via `docker exec` that the rebuilt container has the fix before re-testing (same operational lesson as the `combined`-fix round).

**Re-ran supertrend BTCUSDT/1h/6mo** (job_id `d188c463-24c1-4744-b859-ed25107996fc`, date range 2026-03-03 -> 2026-08-16 — near-identical window to the original round-1 run, few-hour drift from live data refetch):

| Metric | Old (flat 2% bug) | New (real stop distance) | Change |
|---|---|---|---|
| Total trades | 80 | 80 | unchanged (fix doesn't touch trade generation) |
| Win rate | 37.50% | 37.50% | unchanged |
| Total PnL % | +9.75% | +9.75% | unchanged |
| Max drawdown % | 8.00% | 7.99% | trivial (data-window rounding, not the fix) |
| **Avg RR** | **1.49** | **1.33** | **-0.16** |

Trade count, win rate, PnL, and max DD are unaffected by this fix (as expected — it only changes a metrics-section calculation, not trade generation or sizing). Only `avg_rr` moved, modestly (1.49 -> 1.33).

**Does this resolve the reconciliation flag? Partially, and the fuller answer is more interesting than "yes/no":**

The flat-2% bug was real and worth fixing, but fixing it alone does **not** fully explain the round-1 reconciliation concern, because `avg_rr` (both before and after this fix) is computed as an **unsigned** ratio: `abs(exit_price - entry_price) / risk`, averaged across *all* trades including losers. A trade that exits at its stop-loss contributes `risk/risk = 1.0` to this average (not `-1.0`), and a trade that exits at take-profit contributes roughly `rr_ratio` (e.g. ~2.0). So `avg_rr` is really "average reward:risk ratio traveled, ignoring direction" — a real descriptive stat, but **not** the signed R-multiple expectancy that the round-1 back-of-envelope formula (`win_rate × avg_rr − loss_rate × 1`) implicitly assumed. That formula was always going to misfire when fed an unsigned avg_rr, independent of whether the risk denominator used a flat 2% or the real stop.

To properly check reconciliation, we computed a **signed** per-trade R-multiple directly from the trade log (now possible because `stop_loss` is stored on each trade): `R = (exit_price - entry_price)/risk` for longs (sign-preserving), `R = (entry_price - exit_price)/risk` for shorts, using the real stop distance as 1R.

**Supertrend signed-R reconciliation (from the 80-trade log above):**
- avg signed R-multiple (true expectancy/trade): **+0.123R**
- avg win R: +1.94, avg loss R: -0.97, win rate 37.5%, loss rate 62.5% → expectancy = 0.375×1.94 + 0.625×(-0.97) = **+0.123R**
- Sum of signed R across 80 trades: **+9.85R**
- Actual reported total PnL: **+9.75%** (risk_pct=1% per trade, so 1R ≈ ~1% of balance at entry)
- **+9.85R (theoretical, from trade-level signed R) vs +9.75% (actual, compounded) — these reconcile almost exactly.**

**Conclusion:** the flat-2% bug was real, confirmed, and fixed — but it turns out it was never the actual source of the round-1 "doesn't reconcile" puzzle. The real source was applying a signed-expectancy formula to an unsigned metric. Once stop_loss is available per trade (this fix) and a properly signed R-multiple is computed directly from real trade outcomes, supertrend's economics **do** reconcile cleanly with its reported PnL. This is a materially better answer than "unresolved" — it demonstrates the strategy's numbers are internally consistent, not resting on an unexplained gap.

**Note for future use of the `avg_rr` field:** it remains, by design/unchanged scope, an unsigned average reward:risk ratio across all trades (now correctly computed against real stop distances, but still not sign-aware). Do not plug it directly into a signed expectancy formula in future analysis — compute a signed R-multiple from `entry_price`/`exit_price`/`stop_loss`/`side` per trade instead, as done above. Not changing the field's public meaning in this pass (out of scope; would need a docs/API-consumer discussion first) — flagging as a possible follow-up only.

**Cross-check — avg_rr now clusters sanely across unrelated strategies:** re-running fibonacci, macd, and triple_ema_stoch_rsi below (same round) with the fix in place produced avg_rr values of 1.30-1.39 across all of them, despite very different win rates (31-39%) and totally different signal logic. Before the fix, avg_rr varied wildly and non-meaningfully across strategies in the original 6-strategy round (0.18 to 0.72) because the flat-2%-of-price denominator didn't reflect each strategy's real stop distance. The new tight clustering (near rr_ratio's typical default of ~2.0, weighted down by ~60-70% of trades exiting near breakeven-risk at their stop) is itself evidence the fix produces sane, comparable numbers.

---

## 2026-08-16 — Fibonacci overtrading bugfix (entry_tolerance scaled to swing move, not raw price)

**Trigger:** Round `2026-08-16 — Six untested strategies` flagged fibonacci as a strong candidate for the same class of overtrading bug the `combined` strategy had (1187 trades/6mo on 1h, 4423 on 15m — implausibly frequent for a "price within tolerance of a specific Fib level" signal), but did not diagnose or fix it (out of scope for that round).

**Diagnosis (confirmed empirically, not just theoretically):** `backend/app/modules/bot/strategies/fibonacci.py`'s `evaluate()` computed the "is price near a Fib level" distance as `dist_pct = abs(entry - lvl.price) / entry * 100` — **a % of raw price**, compared against `entry_tolerance` (default 0.5%). This does not scale with the size of the underlying swing (`swing_high - swing_low`, recalculated fresh every candle over a 50-candle lookback). For a typical BTC 1h swing over that window (~4-5% move), the gap between adjacent Fib levels (38.2%/50%/61.8%) is roughly 11.8% of the move ≈ 0.5-0.6% of price — i.e. **the tolerance band was comparable in size to the entire gap between levels**, so "near a level" was true far more often than a real, rare confluence signal should be.

**Empirical confirmation** (diagnostic script run inside the rebuilt backend container against real BTCUSDT/1h/6mo candles, `swing_lookback=50`, `min_move_pct=1.0`, `entry_tolerance=0.5`, pre-guard i.e. before the uptrend/downtrend/already-broken-out checks):
- 4070 evaluated candles; only 3 (0.1%) rejected for "swing too small."
- **1963 candles (48.2%) were "near a Fib level"** under the old (price-relative) tolerance — roughly half of all candles, not a rare event.
- Average move_pct among "fired" candles: 4.04% (min 1.17%, max 13.32%) — the bug wasn't confined to tiny/marginal swings near the 1% floor, it applied broadly across typical swing sizes.

**Fix applied:** changed the distance calculation to `dist_pct = abs(entry - lvl.price) / move * 100` — i.e. **% of the swing move**, not of price — where `move = swing_high - swing_low`. Kept the same default numeric value (`entry_tolerance = 0.5`), now correctly interpreted as 0.5% of the move. Docstring (module-level and `evaluate()`) updated to explain the change and why it matters.

**Re-validated the fix with the same diagnostic methodology** before choosing the default: at `entry_tolerance = 0.5` (% of move), pre-guard fire rate dropped to **3.17%** of evaluated candles (129/4070) — in the same ballpark as macd's ~3.6% and lower than bollinger's ~5.2%, both of which the 6-strategy round found to be trading at a plausible frequency. Chose to keep the default numeric value unchanged (0.5) rather than hand-tune a new number — the fix is a units correction, not a re-tune.

**Backtest validation, before vs after (BTCUSDT, 6mo, default params, avg_rr also benefits from the Priority-1 fix above):**

| Timeframe | Metric | Before (bug) | After (fixed) | Change |
|---|---|---|---|---|
| 1h | Trades | 1187 | 127 | -89.3% |
| 1h | Win rate | 31.00% | 32.28% | +1.28pp |
| 1h | Total PnL % | -64.16% | -5.22% | +58.94pp |
| 1h | Max drawdown % | 68.79% | 24.92% | -43.87pp |
| 1h | Avg RR | 0.27 (old broken calc) | 1.32 | n/a (calc method changed) |
| 15m | Trades | 4423 | 426 | -90.4% |
| 15m | Win rate | 31.88% | 36.62% | +4.74pp |
| 15m | Total PnL % | -93.90% | **+44.45%** | +138.35pp |
| 15m | Max drawdown % | 97.05% | 14.72% | -82.33pp |
| 15m | Avg RR | 0.19 (old broken calc) | 1.37 | n/a (calc method changed) |

Job IDs: 1h `f1483d36-c3ed-4765-acb4-9de57cb6e47b` (2026-03-02 -> 2026-08-16), 15m `4694db75-61bf-45ea-8add-8689ee8cae05` (2026-02-21 -> 2026-08-14).

**Sanity-checked the 15m +44.45% result for a compounding-inflation artifact** (same method as the macd/triple_ema_stoch_rsi check below): signed per-trade R-multiple average +0.099R, sum of signed R across 426 trades = +42.0R, non-compounding counterfactual (fixed $100 risk/trade on $10,000 initial) = +42.00% vs actual compounded +44.45% — very close, negligible compounding effect. This is a modest, credible real edge on this single backtest window, not a compounding illusion.

**Assessment:** same pattern as the `combined` strategy's earlier threshold fix — this is a genuine, well-reasoned unit-of-measurement bug (not a parameter retune), and fixing it converts a catastrophic, statistically-meaningless overtrading result into sane numbers. The 15m result is now net-positive (+44.45%) with a believable drawdown (14.72%); the 1h result is still net-negative but no longer catastrophic (-5.22%, 24.92% max DD). **Neither clears the spec's live-readiness bar** (55% win rate over 100+ trades, <8% max DD) — win rates are 32-37%, well short, and 1h is still unprofitable. **Not recommended for testnet/live deployment on this evidence** — this round is a bugfix validation, not a deployment recommendation. Worth a follow-up cross-symbol/cross-regime check before drawing further conclusions, same caveat as every other strategy in this log.

---

## 2026-08-16 — macd / triple_ema_stoch_rsi 15m PnL verification (compounding vs real edge)

**Trigger:** Round `2026-08-16 — Six untested strategies` flagged macd (+186.20% PnL, 38.99% win rate, avg RR 0.19) and triple_ema_stoch_rsi (+30.66% PnL, 35.25% win rate, avg RR 0.21) on 15m as needing scrutiny — that combination of sub-40% win rate and sub-1 avg RR should not normally produce strongly positive PnL, raising a compounding/position-sizing-artifact question. Deferred until after the avg_rr fix above, since the old avg_rr (flat-2%-of-price denominator) was itself unreliable and could have been distorting the picture.

**Method:** Re-ran macd and triple_ema_stoch_rsi on BTCUSDT, 1h and 15m, 6mo, default params, on the rebuilt (fixed) backend. Then, using the now-available real `stop_loss` on every trade, computed a **signed** per-trade R-multiple directly from entry/exit/stop/side (same method validated against supertrend above), and compared the resulting linear (non-compounding) equivalent return against the actual (compounding, 1%-of-current-balance sizing) result, to isolate how much of the headline % return is a real per-trade edge vs an amplification effect of compounding position sizing.

**Results (job IDs: macd 1h `71e78bb2-97d6-4148-a530-33ffc784b925`, macd 15m `76be3bff-f8af-4ce7-a88e-155a4cd66fab`, tesr 1h `476150cb-714b-4a2e-8bdf-085c747c5d9a`, tesr 15m `06b4c505-c5ec-408c-9f69-7931a5ab9e52`):**

| Strategy/TF | Trades | Win rate | Total PnL % | Max DD % | Avg RR (fixed calc) |
|---|---|---|---|---|---|
| macd 1h | 147 | 34.69% | +5.46% | 12.67% | 1.34 |
| macd 15m | 672 | 38.84% | +180.91% | 16.21% | 1.39 |
| tesr 1h | 157 | 31.21% | -9.81% | 19.86% | 1.30 |
| tesr 15m | 590 | 35.25% | +30.66% | 26.70% | 1.35 |

(1h numbers are effectively unchanged from Round 1/prior rounds, as expected — this fix doesn't touch macd/triple_ema_stoch_rsi strategy logic, only the metrics calc. macd 15m trade count/PnL differ marginally from the original 6-strategy round — 672 trades both times, but wins/losses shifted by 1 and final balance moved from $28,619.71 to $28,090.52 — this is expected data-window drift from re-fetching live Binance candles hours later in the day, not a regression.)

**Signed-R reconciliation and compounding check:**

| Strategy/TF | Avg signed R/trade | Sum signed R | Non-compounding equivalent (fixed $100/trade risk on $10k) | Actual (compounding) PnL % | Compounding effect |
|---|---|---|---|---|---|
| macd 15m | **+0.165R** | +111.0R | +111.00% | **+180.91%** | **~1.63x amplification** |
| tesr 15m | **+0.058R** | +34.0R | +34.00% | +30.66% | ~1.0x (negligible, slightly negative from loss sequencing) |

**Conclusion — both things are true, not either/or:**
1. **The underlying per-trade edge is real, not a metric artifact.** Both strategies show a genuine positive signed R-multiple computed directly from real entry/exit/stop prices (macd15m +0.165R/trade over 672 trades, tesr15m +0.058R/trade over 590 trades) — this is not the same broken calculation that produced misleadingly-low avg RR figures before the Priority-1 fix.
2. **Compounding position sizing (1% of *current* balance per trade, not fixed) meaningfully inflates macd15m's headline number**: the same real edge produces +111.00% in a fixed-risk/non-compounding equivalent vs the actual reported **+180.91%** — roughly 1.6x amplification purely from growing position sizes as the account compounds. This confirms part of the original suspicion: the "+186%"-class headline number is partly a compounding effect layered on top of a real edge, not the edge itself being illusory, and should not be read as "this strategy returns 180% reliably" — a large chunk of that magnitude depends on this specific win/loss sequence compounding favorably.
3. **Compounding is not a universal inflator — it's path-dependent.** For triple_ema_stoch_rsi 15m, the compounding and non-compounding results are nearly identical (30.66% vs 34.00%, actually slightly lower) — its win/loss sequence didn't happen to compound favorably. This rules out "any large 15m PnL number is fake" as a blanket claim.
4. **Neither strategy is being recommended for testnet/live deployment on this evidence.** Both remain below the spec's 55% win-rate/100+-trade bar (38.84% and 35.25% respectively), this is still a single BTCUSDT/Feb-Aug-2026 regime, and macd15m's magnitude specifically should be treated with real caution given the compounding-amplification finding above — a different trade sequence (different symbol, different window) could compound far less favorably even with the same underlying per-trade edge.

---

## 2026-08-16 (evening) — 5-year regime validation: supertrend/fibonacci/macd, BTCUSDT, 1h+4h

**Method:** Custom batch script (`/lab/backtest` per combo, submit → poll `/lab/jobs/{id}` → collect metrics), run directly by the orchestrating session rather than an LLM calling each combination individually — the grid itself is not LLM-mediated, keeping this cheap regardless of grid size. Requested 60 months (5 years) per combo; both timeframes returned ~96-98% coverage of that request (limited by how far back Binance's public klines actually go, not a script issue).

**Motivation:** every strategy validated so far (including the already-deployed `supertrend`) had only been tested on a single ~6-month window (Feb-Aug 2026). Poom asked whether deeper history (multiple years, multiple regimes) would change the picture, rather than trusting a short window. This round answers that directly.

**Results — BTCUSDT, full period per timeframe (~2021-09/10 → 2026-08-16, 3year+):**

| Strategy | TF | Trades | Win% | Total PnL% | Max DD% | Avg RR |
|---|---|---|---|---|---|---|
| supertrend | 1h | 806 | 32.88% | **-16.52%** | **36.07%** | 1.32 |
| supertrend | 4h | 213 | 32.39% | **-7.74%** | **22.98%** | 1.31 |
| fibonacci | 1h | 1349 | 31.95% | -51.09% | 65.25% | 1.32 |
| fibonacci | 4h | 320 | 29.69% | -32.00% | 46.04% | 1.30 |
| macd | 1h | 1616 | 33.66% | -1.93% | 43.96% | 1.34 |
| macd | 4h | 389 | 31.11% | -26.01% | 32.50% | 1.31 |

**Every combination is net-negative over the full period.** Critically, `supertrend`/1h — the strategy applied to `/bot/config` on 2026-08-16 based on its 6-month result (+9.75% PnL, 8.00% max DD, the reason it was chosen over everything else) — is **-16.52% PnL with 36.07% max drawdown** (4.5x the 8% ceiling that was the actual decision criterion) over the full ~5-year history. `supertrend`/4h is also negative (-7.74%, 22.98% DD).

**Known limitation of this run:** the script also computed a `recent6mo`/`older` sub-split using a simplified 100-base compounding chain over each trade's `pnl_pct` (position-relative), which does NOT match the real backtester's risk-scaled position sizing (1% of *current account* balance per trade). This produced internally inconsistent numbers (e.g. `older` period showing ~100% drawdown / near-total wipeout for supertrend/1h, which doesn't reconcile with the real, correctly-computed full-period max drawdown of 36.07% from the same trades). **The recent/older split columns in the raw CSV should be disregarded** — only the `full_*` columns above (computed the same validated way as every prior round in this log) are trustworthy.

**Conclusion:** the 2026-08-16 decision to deploy `supertrend` to `/bot/config` was very likely based on a favorable, non-representative 6-month slice, not a durable edge. This is exactly the regime-dependency risk flagged as unresolved since the very first round of this log. See `docs/execution-log.md` for the resulting decision update. Bot remained suspended throughout — no testnet track record was affected by this finding.

---
