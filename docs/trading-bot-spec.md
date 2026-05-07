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

### 1. RSI Mean Reversion (start here)
- Signal: RSI < 30 = oversold (long) · RSI > 70 = overbought (short)
- Simplest to implement, easiest to understand and debug
- Works well in ranging markets

### 2. MACD + EMA Trend Following
- Signal: MACD line crosses signal line in direction of EMA trend
- Adds momentum confirmation to RSI
- Works well in trending markets

### 3. Fibonacci Retracement
- Identify recent swing high/low
- Enter at key retracement levels: 38.2%, 50%, 61.8%
- Stop just beyond the level (invalidation point)

### 4. Bollinger Band Squeeze
- Low volatility (band squeeze) → anticipate breakout
- Enter on breakout direction with volume confirmation

### 5. Elliott Wave + Fibonacci Confluence
- Most complex — requires wave counting logic
- Build last, after simpler strategies are proven

### 6. Combined Score (the real edge)
- Weighted composite of multiple signals
- Weight each strategy by its recent win rate in current market regime
- This is what separates the bot from simple signal following

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
