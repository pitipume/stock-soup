# StockSoup

> A personal investment platform that combines Value Investing fundamentals with technical trading precision.
> Built by Poom. For Poom first. Designed to scale.

---

## The Idea

Most investors pick a lane: value OR technical. StockSoup uses both.

- **Value Investing** (Warren Buffett / Peter Lynch) for the long game — finding undervalued stocks, hidden gems, and growth companies before the market notices
- **Technical Analysis** (Elliott Wave, Fibonacci, Quant, RSI) for the short-to-mid game — timing entries and managing risk
- **Crypto Futures Trading Bot** — automated trading on Binance with configurable strategies and strict risk management
- **Formula Lab** — research and backtesting environment to develop, refine, and export custom trading indicators

The combination is the edge. Cross-validating VI fundamentals with technical signals produces higher-conviction trades than either approach alone.

---

## Products

### 1. VI Scanner
Scan global markets for undervalued stocks, hidden gems, and growth opportunities using Value Investing screening criteria. Phase 1 targets US markets. Thai and other markets added later.

### 2. Trading Bot
Automated Binance Futures trading. Runs on testnet (fake money) until proven, then optionally live. Configurable strategies, strict risk management, portfolio dashboard.

### 3. Formula Lab
Research environment. Backtest strategies, develop custom indicators, generate Pine Script for TradingView export. The "gets better over time" learning layer lives here.

---

## Tech Stack

### Why Python backend (not C# .NET)

Python is the correct choice for this project — not because C# is bad, but because the financial ecosystem lives in Python:

| Library | Purpose |
|---------|---------|
| `fastapi` | Async backend API (typed, fast, closest to C# in Python) |
| `pandas` / `numpy` | Time-series financial data manipulation |
| `yfinance` | Free Yahoo Finance wrapper — US stocks, fundamentals, historical data |
| `ta-lib` | 150+ technical indicators (RSI, MACD, Bollinger Bands, etc.) |
| `ccxt` | Unified API for Binance Futures (and 100+ other exchanges) |
| `celery` | Background job queue — scanning, strategy execution, alerts |
| `sqlalchemy` | ORM for PostgreSQL |

There is no equivalent .NET ecosystem for financial data. This is one of the rare cases where switching stacks is the right call.

### Full Stack Decision

| Layer | Technology | Reason |
|-------|-----------|--------|
| **Backend** | Python 3.12 + FastAPI | Async, typed, financial library ecosystem |
| **Task Queue** | Celery + Redis | Background scans, scheduled jobs, real-time strategy execution |
| **Database** | PostgreSQL + TimescaleDB | TimescaleDB extension handles time-series OHLCV price data efficiently |
| **Cache** | Redis | Real-time price caching, rate limit management, Celery broker |
| **Frontend** | Next.js 14 + Tailwind CSS + shadcn/ui | SSR, minimal clean UI, excellent charting ecosystem |
| **Charts** | Lightweight Charts (TradingView library) | Free, embeddable, same rendering engine as TradingView |
| **Auth** | NextAuth.js | Simple, extensible — single user now, multi-user later |
| **Containerization** | Docker Compose | One command to run everything locally |
| **Deployment** | AWS (when ready) | ECS + RDS + ElastiCache — standard, scalable |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│    Dashboard  │  VI Scanner  │  Bot UI  │  Formula Lab  │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API + WebSocket
┌───────────────────────▼─────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  VI Module   │  │  Bot Module  │  │   Lab Module  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│  ┌──────▼─────────────────▼───────────────────▼──────┐  │
│  │                 Celery Task Queue                   │  │
│  │   (scan jobs · strategy execution · price feeds)   │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
     PostgreSQL +     Redis        External APIs
     TimescaleDB    (cache +       ├── yfinance (US stocks)
                    broker)        ├── Binance API (crypto futures)
                                   ├── FRED API (macro data)
                                   └── SET Smart (Thai stocks, Phase 3+)
```

---

## Build Phases

### Phase 1 — VI Scanner (Build This First)

**Why first:** No real money at risk. Uses free APIs. Teaches the full stack (Python + Next.js + PostgreSQL) without the complexity of real-time trading. If the platform breaks, nothing burns.

**Goal:** Log in → click Scan → wait 30-60 seconds → see a ranked list of undervalued US stocks with clear reasoning for each.

#### VI Screening Criteria

| Metric | Threshold | Theory |
|--------|-----------|--------|
| P/E ratio | < industry median | Cheap relative to sector peers |
| P/B ratio | < 1.5 | Asset-backed value |
| Debt/Equity | < 0.5 | Financial health, not overleveraged |
| ROE | > 15% | Management quality (Peter Lynch standard) |
| Revenue growth | > 10% YoY | Growth, not value trap |
| Free Cash Flow | Positive | Real earnings, not accounting illusion |
| Insider ownership | > 5% | Skin in the game |

#### Hidden Gem Filter (what makes this different from basic screeners)

| Filter | Value | Reason |
|--------|-------|--------|
| Market cap | < $2B | Mid/small cap — where gems hide before institutions find them |
| Analyst coverage | < 5 firms | Underfollowed = potentially mispriced |
| Earnings beat + no price reaction | — | Market ignorance = opportunity |
| 52-week low proximity | Within 20% | Contrarian entry signal |

#### Phase 1 Deliverables

- [ ] Docker Compose environment runs with one command
- [ ] Login page + persistent session
- [ ] "Scan Now" triggers US stock scan (S&P 500 + NASDAQ universe)
- [ ] Results appear within 60 seconds
- [ ] Each result shows: ticker, company name, VI score, P/E, P/B, ROE, market cap, verdict
- [ ] Click a stock → full metric breakdown page
- [ ] Hidden gems filter works
- [ ] Previous scan results saved to database (scan history)

**That's the MVP. No charts, no alerts, no Thai stocks yet. Working beats feature-rich.**

---

### Phase 2 — Trading Bot

**Goal:** Automated Binance Futures trading with strategy selection. Starts on testnet with fake money. Goes live only after 30+ days of profitable testnet results.

#### Three Trading Environments

| Environment | Money | When to Use |
|-------------|-------|-------------|
| **Testnet** | Fake (Binance testnet) | All development and strategy testing |
| **Paper** | Fake (our simulation on historical data) | Backtesting before deploying to testnet |
| **Live** | Real | Only after testnet is proven profitable |

A single `TRADING_MODE` environment variable switches between them. The code is identical — only the API endpoint and credentials change. This is non-negotiable architecture.

#### Strategies (build in this order)

1. **RSI Mean Reversion** — oversold (< 30) / overbought (> 70) signals. Simplest to implement and understand.
2. **MACD + EMA Trend Following** — momentum confirmation with trend filter
3. **Fibonacci Retracement** — key support/resistance entry zones (38.2%, 61.8%)
4. **Bollinger Band Squeeze** — volatility breakout signals
5. **Elliott Wave** — wave count detection + Fibonacci confluence (complex, last)
6. **Combined Score** — weighted composite of multiple signals. This is your edge.

#### Risk Management Rules (enforced in code, not optional)

- Max risk per trade: **1-2% of portfolio** (configurable)
- Stop loss: always set before order executes, never after
- Hard portfolio drawdown stop: **-10% total** → kills all positions, suspends bot
- Max concurrent positions: **3** (prevents overexposure)
- Minimum R:R ratio: **1:2** (only take trades where potential gain ≥ 2× potential loss)

#### Bot UI

- Portfolio balance (testnet vs live clearly labeled)
- Active positions with live P&L
- Open/close positions manually
- Strategy selector + parameter configuration
- Risk settings (% per trade, max drawdown)
- Trade history with win rate, average R:R, total P&L stats

#### Binance API Setup

1. Go to **binance.com** (not the app, not binance.th — international only)
2. Login → Profile → **API Management** → Create API Key
3. Enable: **Enable Futures** (required)
4. Restrict access to your IP address (security)
5. Store API Key + Secret in `.env` — never committed to git

**Testnet keys are separate.** Register at `testnet.binancefuture.com` for dedicated testnet API keys.

> Note: Verify your account is on binance.com (international), not binance.th (Thai regulated version has limited API access for futures).

---

### Phase 3 — Formula Lab

**Goal:** Research environment. Develop custom indicators, backtest against historical data, export Pine Script for TradingView.

#### Features

- Historical OHLCV data storage (top 50 crypto pairs)
- Backtesting engine with configurable date ranges
- Strategy performance reports: win rate, max drawdown, Sharpe ratio, profit factor
- Pine Script export for TradingView
- Comparison view: test multiple strategies against same timeframe

#### The "Gets Better Over Time" Component

Not full AI from day one. Phased approach:

**Phase 3a — Rule-based learning:**
Record every bot trade with outcome (profit/loss, strategy used, market conditions). Calculate rolling win rates per strategy per market condition. The combined score weights strategies by their recent performance automatically.

Example: RSI has 62% win rate on BTC in trending markets → weight it higher than MACD (48%) in those conditions.

**Phase 4+ — Machine learning:**
Once enough trade history exists (500+ trades), train a model to predict which strategy performs best given current market regime (trend, range, volatility). This is reinforcement learning territory — serious ML work, not a weekend project.

---

## Data Sources

| Data | Source | Cost | Notes |
|------|--------|------|-------|
| US stocks — prices + fundamentals | `yfinance` | **Free** | Yahoo Finance wrapper, reliable, no key needed |
| US stock financial statements | `yfinance` | **Free** | Pulls 10-Q/10-K data |
| Crypto OHLCV | Binance API | **Free** | Direct from exchange |
| Crypto testnet | Binance Futures Testnet | **Free** | `testnet.binancefuture.com` |
| Macro data (rates, inflation) | FRED API | **Free** | Federal Reserve data |
| Thai stocks | SET Smart / Finnomena | TBD | Phase 3+, requires investigation |
| EU / Vietnam / China stocks | Alpha Vantage or similar | Paid tier likely | Phase 3+ |

**Phase 1 runs entirely on free data.** No API costs until the trading bot is live.

---

## Project Structure

```
stock-soup/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Settings, env vars (Pydantic Settings)
│   │   ├── database.py             # PostgreSQL + TimescaleDB connection
│   │   ├── models/                 # SQLAlchemy database models
│   │   │   ├── user.py
│   │   │   ├── stock.py
│   │   │   ├── scan.py
│   │   │   ├── portfolio.py
│   │   │   └── trade.py
│   │   ├── modules/
│   │   │   ├── vi/                 # Value Investing scanner
│   │   │   │   ├── screener.py     # Fetch + filter stocks
│   │   │   │   ├── scorer.py       # VI score calculation
│   │   │   │   ├── schemas.py      # Pydantic request/response models
│   │   │   │   └── router.py       # API routes: /vi/scan, /vi/stocks
│   │   │   ├── bot/                # Trading bot
│   │   │   │   ├── strategies/
│   │   │   │   │   ├── base.py     # Abstract strategy class
│   │   │   │   │   ├── rsi.py
│   │   │   │   │   ├── macd.py
│   │   │   │   │   ├── fibonacci.py
│   │   │   │   │   └── combined.py
│   │   │   │   ├── executor.py     # Order execution (testnet / live)
│   │   │   │   ├── portfolio.py    # Position + risk management
│   │   │   │   ├── schemas.py
│   │   │   │   └── router.py       # API routes: /bot/portfolio, /bot/trade
│   │   │   └── lab/                # Formula research
│   │   │       ├── backtest.py
│   │   │       ├── schemas.py
│   │   │       └── router.py
│   │   └── tasks/                  # Celery background jobs
│   │       ├── celery_app.py
│   │       ├── scan_tasks.py       # Periodic VI scans
│   │       └── bot_tasks.py        # Strategy execution loop
│   ├── alembic/                    # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router
│   │   │   ├── (auth)/
│   │   │   │   └── login/
│   │   │   ├── (dashboard)/
│   │   │   │   └── page.tsx        # Overview dashboard
│   │   │   ├── vi/
│   │   │   │   ├── page.tsx        # VI Scanner
│   │   │   │   └── [ticker]/
│   │   │   │       └── page.tsx    # Stock detail
│   │   │   ├── bot/
│   │   │   │   └── page.tsx        # Bot UI
│   │   │   └── lab/
│   │   │       └── page.tsx        # Formula Lab
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn/ui components
│   │   │   ├── charts/             # Lightweight Charts wrappers
│   │   │   └── vi/                 # VI-specific components
│   │   └── lib/
│   │       ├── api.ts              # API client
│   │       └── auth.ts             # NextAuth config
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml              # PostgreSQL + TimescaleDB + Redis + Backend + Frontend
├── docker-compose.dev.yml          # Dev overrides (hot reload)
├── .env.example                    # Template — copy to .env, never commit .env
├── .gitignore
└── STOCKSOUP.md                    # This file
```

---

## Environment Variables

```bash
# App
APP_ENV=development                 # development | testnet | live

# Database
DATABASE_URL=postgresql://stocksoup:password@localhost:5432/stocksoup

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
NEXTAUTH_SECRET=your-secret-here
NEXTAUTH_URL=http://localhost:3000

# Binance — Testnet (safe to use during development)
BINANCE_TESTNET_API_KEY=
BINANCE_TESTNET_SECRET_KEY=
BINANCE_TESTNET_BASE_URL=https://testnet.binancefuture.com

# Binance — Live (only fill when ready to trade real money)
BINANCE_LIVE_API_KEY=
BINANCE_LIVE_SECRET_KEY=
BINANCE_LIVE_BASE_URL=https://fapi.binance.com

# Trading risk limits
MAX_RISK_PER_TRADE_PCT=1.0         # % of portfolio per trade
MAX_PORTFOLIO_DRAWDOWN_PCT=10.0    # Hard stop — kills all positions
MAX_CONCURRENT_POSITIONS=3
```

---

## Development Setup (When We're Ready)

```bash
# Clone and enter project
cd stock-soup

# Copy env template
cp .env.example .env
# Fill in your values in .env

# Start everything
docker-compose up -d

# Backend available at: http://localhost:8000
# Frontend available at: http://localhost:3000
# API docs (auto-generated): http://localhost:8000/docs
```

---

## What We Are NOT Building Yet

| Feature | Why Not Now |
|---------|-------------|
| Mobile app | Unnecessary complexity at MVP stage |
| Multi-user / membership | Build for yourself first, validate it works |
| Thai / EU / Vietnam stocks | Phase 3+ — US data is cleaner and free |
| Elliott Wave automation | Complex signal detection — research first, automate later |
| Real money trading | Testnet must be profitable for 30+ days first |
| ML / AI learning bot | Needs 500+ trade history to be meaningful |
| TradingView webhook sync | Nice to have, not core functionality |

These are real features on the roadmap. They're just not what makes Phase 1 useful.

---

## Risk Acknowledgement

**The trading bot can lose real money.** This is not hypothetical. Before switching `APP_ENV=live`:

- Testnet must show positive P&L over 30+ consecutive days
- Win rate must be > 55% across 100+ testnet trades
- Max drawdown on testnet must stay below 8%
- All risk management rules must be verified working (stop loss, position sizing, drawdown kill switch)

Start small when going live. The first real money test should be an amount you are fully prepared to lose.

---

## Roadmap Summary

| Phase | Focus | Timeline Estimate |
|-------|-------|-------------------|
| **1** | VI Scanner — US stocks, full stack setup | 6–8 weeks at 1hr/day |
| **2** | Trading Bot — Binance testnet, RSI + MACD strategies | 8–12 weeks |
| **3** | Formula Lab — backtesting, more strategies, Pine Script export | 8–12 weeks |
| **4** | Expand markets (Thai, EU), ML learning layer, membership | Ongoing |

These are honest estimates for 1 hour per day. Adjust based on your actual pace — don't rush Phase 1 to get to the bot. A solid foundation makes Phase 2 dramatically faster.

---

*Project name: StockSoup*
*Status: Pre-development — architecture locked, ready to build*
*Last updated: 2026-05-07*
