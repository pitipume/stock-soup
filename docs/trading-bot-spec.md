# Trading Bot Specification (Phase 2)

> Status: Not yet implemented. This document is the design spec.
> Build Phase 1 (VI Scanner) completely before starting here.

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
- Key params: `threshold` (default 0.3), `conflict_max` (default 0.15)

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
