# Execution Log

Running record of lucy-trading-execution decisions — recommendations drafted, whether applied, and the evidence behind them. Append-only — do not overwrite prior entries.

---

## 2026-08-16 — First real backtest validation: draft recommendation only, nothing applied

**Trigger:** First-ever real backtest run through stock-soup's own `/lab/compare` pipeline (see `docs/backtest-log.md`, entry `2026-08-16 — First real backtest validation run`, job_id `1e08ad27-95a6-4f3b-b5ab-7e69e7df2c52`). Poom has not yet reviewed these numbers. Per explicit instruction for this run: **DRAFT ONLY — no config changes applied**, regardless of trading_mode.

**Current bot state (read-only check, not modified):**
- `GET /bot/status` → `active_strategy: "combined"`, `trading_mode: "testnet"`, `is_suspended: false`
- `GET /bot/stats/by-strategy` → `[]` (no live/testnet trade history yet on any strategy)

**Backtest evidence (BTCUSDT, 1h, 6 months, 2026-02-27 → 2026-08-16, default params, no tuning):**

| Strategy | Trades | Win rate | Total PnL% | Max DD% | Avg RR |
|---|---|---|---|---|---|
| supertrend | 80 | 37.50% | +9.75% | 8.00% | 1.49 |
| macd | 147 | 34.69% | +5.33% | 12.67% | 0.41 |
| rsi | 314 | 32.17% | -15.72% | 45.83% | 0.43 |
| combined | 1232 | 30.36% | -59.09% | 75.97% | 0.36 |

Market regime context (`docs/research-log.md`, 2026-08-16): BTC has been in a choppy, low-momentum downtrend for most of the window (~-50% from Oct 2025 highs, thin August liquidity, no sustained trend). Supertrend is trend-following — this regime plausibly understates its true edge, or its modest positive result is noise from a few trending pockets. Cuts both ways; not resolved by this data alone.

**stock-soup's own live-readiness bar** (`docs/trading-bot-spec.md`): >55% win rate over 100+ trades, max drawdown <8%, before live is even considered. **None of the four strategies clear this bar.** This recommendation is not a live-readiness claim.

### Recommendation

**1. supertrend — worth moving to testnet paper-trading validation, with caveats, NOT a live-readiness claim.**
- It's the only strategy that is both net-positive and at/under the spec's 8% max-drawdown ceiling (8.00% exactly — right at the line, not comfortably under it).
- Rationale for accumulating a real testnet track record toward the spec gate: +9.75% PnL over 80 trades, 37.50% win rate, 8.00% max DD, avg RR 1.49, over the BTCUSDT/1h/6-month window above.
- **Explicit caveats:**
  - Single symbol (BTCUSDT), single timeframe (1h), single 6-month backtest window, single market regime (choppy downtrend) — this is a thin evidentiary base. No cross-regime (bull, sharp-crash, high-liquidity) validation has been done.
  - Win rate (37.5%) is well below the spec's 55% live gate — the positive PnL relies on average winners being larger than losers (RR), not on hit rate. That's a legitimate strategy shape (trend-following systems often run low win rate / high RR) but it means this strategy's results are fragile to regime change and to the RR figure being right.
  - **Metric-definition flag, unresolved:** Avg RR 1.49 at 37.5% win rate implies a simple expectancy of ~0.375×1.49 − 0.625×1 ≈ **−0.066R/trade** (slightly negative), which doesn't obviously reconcile with the reported +9.75% total PnL. Possible explanations: compounding effects, fees/funding not captured in the simple R-multiple calc, or "Avg RR" being computed differently than realized win/loss ratio (e.g., planned TP/SL ratio rather than realized). This should be double-checked against the raw trade log before trusting the magnitude of supertrend's edge — flagged as a question, not a disqualifier.
  - Regime dependency noted above: this backtest window may under- or over-state supertrend's real edge; direction of the bias is unclear.
- Bar for moving forward: this is "worth accumulating real testnet track record toward the spec's 30-day/100-trade/55%-win-rate/<8%-drawdown gate" — nothing more. Not a signal to consider live trading.
- **Invalidation condition going forward:** if testnet win rate drops materially below the backtested 37.5% (e.g., under ~25-30% over the first 30-50 testnet trades) or drawdown exceeds 8% on testnet, treat the backtest edge as regime-specific/not robust and revert before any live discussion.

**2. Explicitly recommend AGAINST testnet deployment right now for:**
- **macd** — net positive (+5.33%) but max drawdown 12.67% exceeds spec's 8% ceiling; avg RR only 0.41 (needs high win rate to be viable, and win rate is only 34.69%).
- **rsi** — net negative (-15.72% PnL), max drawdown 45.83%, win rate 32.17%. Clearly unviable on this evidence.
- **combined** — net negative (-59.09% PnL), max drawdown 75.97%, 1232 trades in 6 months on 1h bars (i.e., roughly one trade every ~3.5 hours, near-continuous). This trade frequency combined with the severity of the drawdown looks like overtrading/whipsaw in the weighted-vote logic, not a viable signal. **Flagging this as worth a separate engineering/code review of the weighted-vote combination logic — not something to recommend for any deployment as-is.**

**3. Follow-up backtest suggested (no numbers invented, just what to test next):**
- Re-run supertrend via `/lab/compare` or `/lab/backtest` with alternate ATR period / multiplier settings (e.g., a longer ATR period and/or higher multiplier to reduce whipsaw sensitivity in choppy regimes, and a shorter/tighter setting to test if it's leaving RR on the table in the trending pockets) to see whether performance is robust to reasonable parameter perturbation, not just the single default configuration tested here.
- Separately, re-run supertrend over a different symbol and/or a prior trending regime (if historical data supports it) to test the regime-dependency question raised in the research log, before treating the +9.75%/8.00%DD result as representative.
- Pull the raw trade-level log for the supertrend run and manually verify the Avg RR calculation against realized win/loss R-multiples to resolve the expectancy-reconciliation flag above.

### Action taken

**Nothing applied.** `PATCH /bot/config` was not called. Current bot state remains unchanged: `active_strategy: "combined"`, `trading_mode: "testnet"`. This is a draft recommendation for Poom's review only — per instruction for this run, no config change was made regardless of trading_mode, since this is the first real backtest validation and results have not yet been reviewed by Poom.

**Confidence:** Low-to-medium on supertrend specifically being worth testnet validation (directionally reasonable given it's the only strategy clearing both the PnL-positive and ≤8%-DD bars, but the thin single-regime/single-symbol/single-timeframe base and the unresolved RR/PnL reconciliation keep confidence capped). High confidence on ruling out rsi and combined for now — their numbers are unambiguous. Medium confidence on ruling out macd — its drawdown breach is clear-cut against the spec's own threshold, even though its PnL is positive.

**Main risks:** (1) thin backtest history — one symbol, one timeframe, one 6-month regime; (2) regime mismatch — trend-following strategy tested in a choppy/downtrend window, direction of bias on true edge unknown; (3) unresolved metric-definition question on Avg RR vs. reported PnL for supertrend; (4) `combined` strategy's overtrading behavior may indicate a logic bug worth fixing before it's ever reconsidered, independent of parameter tuning.

---

## 2026-08-16 (later same day) — supertrend applied to /bot/config, after Poom's review

**Trigger:** Poom reviewed the evidence accumulated across three rounds and explicitly chose "commit to supertrend, plan testnet deploy" — this is his decision, not an automated one.

**Evidence supporting this, beyond the single-symbol result above:**
- Round 2 (`docs/backtest-log.md`): `supertrend`/1h held up across BTCUSDT, ETHUSDT, SOLUSDT — all net-positive (+4.9% to +9.75% PnL), consistent drawdown (7.75-8.5%) and trade counts (80-81). No longer a single-symbol result; this was the deciding factor that resolved risk (2) from the round-1 entry above (regime/symbol dependency) partially — still only one calendar window, but no longer only one asset.
- Round 3 (`docs/backtest-log.md`): the other 8 strategies tested (including the newly-fixed `combined`) all remained worse than `supertrend` — none cleared both the PnL-positive and 8%-drawdown bars.
- The Avg-RR/PnL reconciliation flag from the round-1 entry above **remains unresolved** — not re-verified before this decision. Worth doing before trusting the magnitude of the edge, not before starting testnet accumulation (testnet trade data will itself help resolve it).

**Action taken:** `PATCH /bot/config {"active_strategy": "supertrend", "strategy_params": {}}` applied. Confirmed via `GET /bot/status`: `active_strategy: "supertrend"`.

**Bot deliberately left `is_suspended: true`.** Not resumed. Reason: starting the actual testnet validation clock (the 30-consecutive-day gate in `docs/trading-bot-spec.md`) only means something on a stable, continuously-running deployment — currently this is Poom's local laptop, which cannot guarantee that (see hosting discussion, `~/.claude/agents/lucy-trading-lead.md` hard constraints). Resuming now would risk burning testnet days that get invalidated by a laptop closing. Resume only once a stable deployment (VPS or laptop kept genuinely 24/7) is actually in place.

**Confidence:** Medium — meaningfully higher than the round-1 entry given multi-symbol confirmation, but still capped by single-timeframe/single-regime evidence and the unresolved RR reconciliation.

---

## 2026-08-16 (later) — RR reconciliation bugfix: confidence update on the deployed supertrend decision

**Trigger:** Follow-up to the two entries above. The round-1 entry flagged an unresolved metric-definition question (avg RR 1.49 at 37.5% win rate didn't obviously reconcile with +9.75% PnL); the later entry noted this was "not re-verified before" the decision to apply supertrend to `/bot/config`. This round resolves it. Full diagnosis, fix, and validation detail is in `docs/backtest-log.md` (`2026-08-16 — avg_rr metric bugfix` and `2026-08-16 — Fibonacci overtrading bugfix` entries) — this entry summarizes what it changes for the supertrend decision specifically.

**What was found:** the flagged concern had two layered causes, not one:
1. A real bug — `avg_rr` used a hardcoded flat 2% "risk" for every trade instead of each position's actual stop-loss distance, inconsistent with position sizing elsewhere in the same function. Confirmed and fixed (`backend/app/modules/lab/backtester.py`, `schemas.py`, `frontend/src/lib/api.ts`). Re-running supertrend BTCUSDT/1h/6mo: avg_rr moved 1.49 -> 1.33; trades/win-rate/PnL/max-DD are all unchanged (74/50-trade breakdown, 37.50%, +9.75%, ~8.00% — this fix doesn't touch trade generation, only the metrics calc).
2. A deeper, previously-unnoticed issue — `avg_rr` (even after the fix) is an **unsigned** ratio, not a true win/loss-weighted expectancy, so it was never going to cleanly "reconcile" via the simple formula the round-1 entry used, independent of the flat-2% bug. Using the now-available real stop_loss to compute a properly **signed** R-multiple per trade directly from the trade log, supertrend's expectancy comes out to +0.123R/trade, summing to +9.85R across 80 trades — which lines up almost exactly with the actual +9.75% total return.

**Does this change confidence in the supertrend decision already applied to `/bot/config`?**

**Yes, modestly upward — the unresolved flag from round 1 is now resolved, and resolved in supertrend's favor, not against it.** The concern was never "supertrend is unprofitable" — the raw PnL/win-rate/drawdown numbers were never in question. The concern was a nagging "the RR math doesn't add up, so maybe something about this result isn't trustworthy." That specific concern is now closed: the trade-level economics are internally consistent (signed R-multiple sum reconciles with reported PnL to within rounding), and the source of the earlier confusion (an unsigned metric being read as a signed one, compounded by a real-but-secondary flat-2% calculation bug) is identified and explained, not just patched over.

**What this does NOT change:**
- Still single-symbol-confirmed-multi (BTCUSDT/ETHUSDT/SOLUSDT per the earlier round-2 entry), single-timeframe (1h), single calendar regime (Feb-Aug 2026) — the regime-dependency risk from the original round-1 entry is untouched by this fix.
- Still below the spec's live-readiness bar (37.5% win rate vs the 55% gate) — this fix does not and could not change that; positive expectancy with a sub-40% win rate is a legitimate but fragile strategy shape, as already noted.
- No config change made this round. `active_strategy` remains `supertrend`, bot remains `is_suspended: true`, per standing instruction not to touch `/bot/config` in a validation-only round.

**Confidence:** raised from "medium, capped by the unresolved RR flag" (prior entry) to **medium, with the RR flag now closed rather than open**. Still not high — the regime/timeframe/win-rate caveats from the original decision are unchanged and remain the binding constraints, not this metric question.

---
