# Trading Bot Specification (Phase 2)

> Status: Implemented — all 6 strategies below are built and live in `backend/app/modules/bot/strategies/`.
> Not yet in continuous testnet validation (no stable 24/7 deployment running yet) — the go-live checklist's
> clock hasn't started. This document remains the design spec / source of truth for the risk rules and strategy logic.

---

## Core principle

The bot should never trade real money until it has proven itself with fake money.
This is not optional — it's the architecture.

```
Paper trading → Testnet (Binance fake) → Live (real money)
                30+ profitable days
                > 55% win rate (100+ trades)
                Max drawdown stayed < 8%
```

---

## Three environments

Controlled by a single env var: `TRADING_MODE=testnet|paper|live`

| Mode | Money | Binance endpoint | Use case |
|------|-------|------------------|---------|
| `testnet` | Fake (Binance provides) | testnet.binancefuture.com | All development and strategy testing |
| `paper` | Fake (our simulation) | Historical data only | Backtesting before deploying to testnet |
| `live` | Real | fapi.binance.com | Only after testnet is proven |

The code is **identical** across modes. Only the API credentials and base URL change.
The executor reads `TRADING_MODE` and routes accordingly.

---

## Risk rules (enforced in code, not configurable from UI)

These are not options. They are hard limits:

| Rule | Value | Why |
|------|-------|-----|
| Max risk per trade | 1-2% of portfolio | Kelly criterion — survive losing streaks |
| Stop loss timing | Set BEFORE order executes | Never place an unprotected trade |
| Portfolio drawdown kill | -10% total | Kill all positions, suspend bot, alert |
| Max concurrent positions | 3 | Prevent overexposure to correlated moves |
| Minimum R:R ratio | 1:2 | Only enter trades where gain potential ≥ 2× loss |

The kill switch: if total portfolio drops 10% from its high-water mark, the bot:
1. Closes all open positions immediately (market orders)
2. Sets `bot_suspended = True` in DB
3. Stops accepting new signals
4. Requires manual reset from the UI

---

## Strategies (implement in this order)

### 1. RSI Mean Reversion ✓ IMPLEMENTED
- Signal: RSI < 30 = oversold (long) · RSI > 70 = overbought (short)
- Stop: 1× ATR below/above entry · Take profit: 2× risk (1:2 R:R)
- File: `backend/app/modules/bot/strategies/rsi.py`

### 2. MACD + EMA Trend Following ✓ IMPLEMENTED
- Signal: MACD line crosses signal line IN the direction of the EMA-200 trend
  - Price > EMA + MACD bullish cross → LONG
  - Price < EMA + MACD bearish cross → SHORT
  - Prevents counter-trend entries (main weakness of RSI alone)
- Stop: 1× ATR · Take profit: 2× risk
- File: `backend/app/modules/bot/strategies/macd.py`
- Switch via: `PATCH /bot/config {"active_strategy": "macd"}`

### 3. Fibonacci Retracement ✓ IMPLEMENTED
- Find swing high and swing low in last 50 candles; whichever came last sets the trend
- Uptrend: price retraces to 38.2%, 50%, 61.8% (from swing_low→high) → LONG
- Downtrend: price bounces to 38.2%, 50%, 61.8% (from swing_high→low) → SHORT
- Entry when price is within 0.5% of a Fib level
- Stop: 0.5× ATR beyond the level (invalidation point)
- Take profit: 2× risk
- File: `backend/app/modules/bot/strategies/fibonacci.py`
- Switch via: `PATCH /bot/config {"active_strategy": "fibonacci"}`

### 4. Bollinger Band Squeeze ✓ IMPLEMENTED
- Three conditions must all fire together:
  1. SQUEEZE — band width in bottom 20% of last 50 candles (coiled energy)
  2. BREAKOUT — close above upper band (long) or below lower band (short)
  3. VOLUME — current volume > 1× average (confirms conviction, rejects fakeouts)
- The squeeze must have fired within the last 5 candles (prevents chasing old moves)
- Stop: middle band (SMA20), capped at 2× ATR — if price falls back to mean, setup failed
- Take profit: 2× risk
- File: `backend/app/modules/bot/strategies/bollinger.py`
- Switch via: `PATCH /bot/config {"active_strategy": "bollinger"}`

### 5. Elliott Wave + Fibonacci Confluence ✓ IMPLEMENTED
- Identifies the start of Wave 3 — the strongest impulse in EWT
- Pivot detection: N-bar confirmed swing highs/lows (not running extremes)
- Wave structure: finds most recent W0→W1→W2 sequence from confirmed pivots
- EWT Rule A: W2 must NOT exceed W0 (hard invalidation)
- EWT Rule B: W2 retracement must be 23.6%–78.6% of W1
- Entry: price breaks away from W2 in the W1 direction (W3 starting)
- Stop: W2 extreme ± 0.5× ATR (EWT rule — if W3 breaks W1 start, count is wrong)
- Take profit: 161.8% Fibonacci extension of W1 measured from W2
- Golden zone (38.2%–61.8% retracement) flagged in signal reason
- File: `backend/app/modules/bot/strategies/elliott_wave.py`
- Switch via: `PATCH /bot/config {"active_strategy": "elliott_wave"}`

### 6. Combined Score ✓ IMPLEMENTED
- Runs all 5 sub-strategies on every candle simultaneously
- Each strategy's vote is weighted by its recent win rate (fetched from `trades` table, last 30 days)
- Default weight = 0.5 when fewer than 5 trades exist for a strategy (prevents over-fitting on lucky early trades)
- `long_score = Σ weight_i` for strategies firing LONG; `short_score = Σ weight_i` for SHORT
- Fires LONG if: `long_score >= threshold` AND `short_score <= conflict_max` (opposing score small enough)
- `conflict_max` guard prevents trading when strong strategies disagree (e.g. RSI long vs MACD short)
- SL/TP comes from the "anchor" — the highest-weighted strategy that voted for the winning direction
- As testnet data accumulates, weights shift automatically toward strategies that are working now
- File: `backend/app/modules/bot/strategies/combined.py`
- Switch via: `PATCH /bot/config {"active_strategy": "combined"}`
- Key params: `threshold` (default 0.6, fixed from 0.3 on 2026-08-16 — see below), `conflict_max` (default 0.15)
- **BUGFIX (2026-08-16):** default `threshold` was 0.3, below a single sub-strategy's neutral default weight (0.5). That let any ONE sub-strategy fire the combined signal alone with zero opposition, defeating the confluence design — backtest (BTCUSDT/1h/6mo) showed 1232 trades, -59% PnL, 76% drawdown. Raised threshold to 0.6 so at least two neutral-weight strategies must agree (or one strategy with a proven win-rate weight ≥0.6 can act alone). See `docs/backtest-log.md` Round 3 for the validation backtest. `combined` was NOT applied to the bot config — this is a code-level default fix only, still evidence-gathering.

### 7. Time-Series Momentum ✓ IMPLEMENTED (2026-08-17), backtester-only so far
- After all 9 strategies above were run through a full 5-year/multi-timeframe backtest (`docs/backtest-log.md`, 2026-08-17), none cleared the live-readiness bar — several were severely broken (near-total drawdown), others showed large returns paired with equally large, timeframe-inconsistent drawdowns (the same "looks great on one slice" trap as the original `supertrend` decision). This strategy is a structurally different approach, grounded in peer-reviewed academic research on crypto time-series momentum rather than retail technical-indicator patterns (see `docs/execution-log.md`, 2026-08-17 entry, for the research summary and citations).
- Signal: trailing N-day return (default 90d) sign, evaluated only at periodic rebalance points (default every 7 days) — deliberately low-frequency, unlike every other strategy here which reacts to single-candle conditions.
- Requires **daily ("1d") candles** — this is the one strategy in this file that needs a different timeframe than 15m/1h/4h to make sense.
- Stop: wide, multi-day ATR-based (default 3x ATR). Take-profit: deliberately far (default 8x ATR) so exits are dominated by trend invalidation, not an early profit cap — "let winners run."
- File: `backend/app/modules/bot/strategies/time_series_momentum.py`
- **Adaptation caveat (UPDATED 2026-08-21):** `run_backtest` in `backend/app/modules/lab/backtester.py` now supports an opt-in `close_on_reversal: bool = False` parameter (default off, so all 9 other strategies' logged results are unaffected) that closes a position the moment the strategy's signal flips, instead of only via SL/TP. Tested against this strategy — it does **not** meaningfully help: mixed/negative effect on drawdown across BTC/ETH/SOL (see `docs/backtest-log.md`, 2026-08-21). The position-stacking approximation was not the main thing keeping this strategy above the 8% drawdown ceiling. Not wired into the executor or exposed via the `/lab/backtest` API — currently only reachable by calling `run_backtest(..., close_on_reversal=True)` directly, kept for any future ad hoc validation.
- **Robustness caveat (found 2026-08-21):** this strategy's rebalance boundaries (`(n - 1) % rebalance_days`) are indexed from the start of whatever candle window `fetch_candles` happens to return, not calendar-aligned. Since `fetch_candles` anchors to `datetime.now()`, re-running the identical backtest a few days later shifts which days count as rebalance days across the whole simulated history — enough to swing BTCUSDT's 5-year result from +11.51%/9.20%DD to +0.56%/8.59%DD in one observed case, just from a 4-day difference in when the backtest was run. This is a real fragility in the current implementation, not yet fixed. Before trusting this strategy further, rebalance boundaries should be made calendar-aligned (e.g. actual day-of-month) and results re-checked across multiple deliberately-shifted window starts. See `docs/backtest-log.md`, 2026-08-21 entry.
- **Not yet wired into the live executor** (`backend/app/tasks/bot_tasks.py`) — that file hardcodes a single 15m timeframe for every strategy's candle fetch, which doesn't work for this one. Registered in the backtester only for now (`/lab/backtest`, `/lab/compare`). Live wiring is a separate follow-up if backtesting shows this is worth deploying.

---

## Known gap: live executor strategy dispatch is incomplete

`backend/app/tasks/bot_tasks.py`'s `_check_symbol` only dispatches to `rsi`, `macd`, `fibonacci`, `bollinger`, `elliott_wave`, `combined` — **`supertrend`, `three_golden`, and `triple_ema_stoch_rsi` are missing** from this live/testnet dispatch table even though they exist in the backtester's `_STRATEGIES` list and `_get_signal` dispatcher. Found 2026-08-17 while `supertrend` was still set as `/bot/config`'s `active_strategy` (from a decision later reversed on backtest evidence, see `docs/execution-log.md`) — if the bot had been resumed with that config, `_check_symbol` would have hit its `else: logger.warning(...); return` branch every cycle and silently done nothing, not errored loudly. Not fixed yet since none of these three are currently being deployed, but worth closing this gap (mirror the backtester's dispatch table) before ever setting `active_strategy` to one of these three again.

---

## Binance API setup

1. Go to **binance.com** (not binance.th — Thai version has limited futures API)
2. Login → Profile → API Management → Create API Key
3. Enable: **Enable Futures** (required)
4. Restrict to your IP address (security)
5. Store in `.env` as `BINANCE_LIVE_API_KEY` and `BINANCE_LIVE_SECRET_KEY`

**Testnet is separate:**
- Register at `testnet.binancefuture.com`
- Get separate testnet API key + secret
- Store as `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_SECRET_KEY`

---

## Bot UI requirements

- Portfolio balance (clearly labeled TESTNET or LIVE)
- Active positions with live P&L
- Open/close positions manually
- Strategy selector + parameter controls
- Trade history: win rate, average R:R, total P&L
- Drawdown gauge with kill switch status

---

## Go-live checklist

Before setting `TRADING_MODE=live`, ALL of these must be true:

- [ ] Testnet showing positive P&L for 30+ consecutive days
- [ ] Win rate > 55% over 100+ testnet trades
- [ ] Max drawdown on testnet never exceeded 8%
- [ ] Kill switch tested and verified working
- [ ] Stop loss verified set before every order
- [ ] Position sizing verified at 1-2% per trade
- [ ] Start with the smallest amount you're comfortable losing entirely

---

## Why Binance Futures (not spot)

- Futures allow shorting — profit in both directions
- Leverage available (use conservatively: 2-3x max, not the 100x Binance offers)
- Binance has the best API stability and liquidity for retail algorithmic trading
- CCXT library abstracts the API cleanly if we ever want to add other exchanges

---

## Known testnet limitations

- **Conditional orders not supported**: Binance Futures testnet (`testnet.binancefuture.com`) rejects
  `STOP_MARKET` and `TAKE_PROFIT_MARKET` orders with error -4120. These work on the live API.
  On testnet, the bot places the entry order and records the position in DB, but SL/TP are not set
  on the exchange. Position lifecycle is handled by the `sync_positions` Celery task instead.
  **This will not be an issue in production** (live API supports these order types).

- **Position sizing bug (fixed 2026-05-13)**: Original formula `risk_amount / stop_distance` did not
  account for leverage, causing 3× oversizing. Fixed to `risk_amount / (stop_distance × leverage)`.

---

## Data flow (Phase 2)

```
Price feed (Binance WebSocket)
        │
        ▼
Strategy signal generator (per strategy, per timeframe)
        │
        ▼
Combined score calculator
        │
        ▼ (if signal strong enough)
Risk check (position size, drawdown, concurrent positions)
        │
        ▼ (if passes risk check)
Order executor → Binance API
        │
        ▼
Trade logged to DB
```
