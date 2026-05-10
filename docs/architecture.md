# Architecture

## System overview

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend (port 3000)          │
│    VI Scanner  │  Trading Bot (Phase 2)  │  Lab (Phase 3)│
└───────────────────────────┬─────────────────────────────┘
                            │ REST API + WebSocket (Phase 2)
┌───────────────────────────▼─────────────────────────────┐
│                   FastAPI Backend (port 8000)            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  /modules/vi │  │  /modules/bot│  │ /modules/lab  │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│  ┌──────▼─────────────────▼───────────────────▼──────┐  │
│  │              Celery Task Queue (Redis broker)       │  │
│  │     scan_tasks  ·  bot_tasks (Phase 2)             │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
       PostgreSQL +       Redis       External APIs
       TimescaleDB      (cache +     ├── yfinance (US stocks)
                        broker)      ├── Binance API (Phase 2)
                                     └── FRED API (macro, Phase 3)
```

## Why this stack

### Python over C# for the backend

This was not a preference call. The financial data ecosystem lives in Python:

| Library | Purpose |
|---------|---------|
| `yfinance` | Yahoo Finance wrapper — US stocks, no API key |
| `pandas` / `numpy` | Time-series data manipulation |
| `ta-lib` | 150+ technical indicators |
| `ccxt` | Unified Binance Futures API (Phase 2) |
| `sqlalchemy` | Async ORM for PostgreSQL |

None of these have .NET equivalents of comparable quality.

FastAPI was chosen specifically because it's the closest Python framework to what a C# developer would recognize — strong typing (Pydantic), async-first, dependency injection, and OpenAPI docs out of the box.

### PostgreSQL + TimescaleDB

Regular PostgreSQL for users, scans, and results. TimescaleDB extension for OHLCV price time-series in Phase 2 — TimescaleDB makes time-range queries on price data 10-100× faster than vanilla Postgres via automatic partitioning.

### Celery + Redis

VI scans take 15-30 minutes (500+ tickers, one HTTP call each). They cannot block the API request. Celery offloads this to a worker process and Redis acts as the message broker.

### Next.js 14 + Tailwind

Server-side rendering for fast first loads. Tailwind for utility-first CSS that's fast to write and easy to maintain without a design system. Phase 1 has no complex UI interactions that would justify a heavier framework.

---

## Data flow: VI scan

```
User clicks "Scan Now"
        │
        ▼
POST /vi/scan
  → Create Scan(status=pending) in DB
  → run_vi_scan_task.delay(scan_id)  ← queues to Redis
  → return Scan immediately (201)
        │
        ▼ (background, in Celery worker)
run_vi_scan_task(scan_id)
  → fetch_us_universe()      ← static list ~200 tickers (S&P 500 + NASDAQ-100)
  → run_vi_scan(tickers)     ← yfinance per-ticker, ~500 calls
       └── score_stock(metrics)  ← VI scoring algorithm
  → Save ScanResult rows to DB
  → Update Scan(status=done)
        │
        ▼ (frontend polls every 3s)
GET /vi/scans/{id}
  → Returns Scan + ScanResult[] ordered by vi_score DESC
```

---

## Environment modes

| `APP_ENV` | Purpose |
|-----------|---------|
| `development` | Local dev. API docs enabled. SQLAlchemy logs queries. |
| `testnet` | Production-like but using Binance testnet (Phase 2) |
| `live` | Real money. API docs disabled. Never set this until testnet is proven. |

| `TRADING_MODE` | Purpose |
|----------------|---------|
| `testnet` | Binance testnet fake money |
| `paper` | Our own historical simulation |
| `live` | Real Binance account — guarded by 30-day testnet requirement |

---

## Data flow: Trading Bot (Phase 2)

```
Celery Beat triggers run_bot_cycle every 5 min
        │
        ▼
_execute_bot_cycle()
  → Record PortfolioSnapshot (balance, equity, drawdown)
  → check_drawdown() — if > 10%, trigger kill switch
  → For each symbol in _SYMBOLS (BTCUSDT, ETHUSDT):
       → get_klines() from Binance (or stub)
       → RSI strategy evaluate(candles) → Signal
       → If signal != "none":
            → approve_trade() — risk checks (suspended?, concurrent limit, position size)
            → If approved: set_leverage → place_order → set_stop_loss → set_take_profit
            → Write Position to DB
        │
        ▼ (kill switch path)
_trigger_kill_switch()
  → Close all open positions at market price
  → Set BotConfig.is_suspended = True
  → Manual resume required from UI (POST /bot/resume)
```

---

## Module boundaries

Each module (`vi`, `bot`, `lab`) is fully self-contained:
- `router.py` — FastAPI routes
- `schemas.py` — Pydantic request/response models
- `screener.py` / `executor.py` — business logic
- `scorer.py` / `strategies/` — domain algorithms

No cross-module imports. Shared infra (DB session, config) comes from `app/database.py` and `app/config.py`.

### Bot module structure
```
modules/bot/
├── binance_client.py   — Binance Futures API wrapper (testnet/live routing + stub mode)
├── executor.py         — Signal → risk check → order placement → DB write
├── risk.py             — Position sizing, drawdown check, concurrent position gate
├── router.py           — REST endpoints: /bot/status, /portfolio, /positions, /trades, /stats
├── schemas.py          — Pydantic schemas
└── strategies/
    ├── rsi.py          — RSI mean-reversion: RSI<30=long, RSI>70=short, ATR-based stops
    ├── macd.py         — MACD + EMA-200 trend filter: cross must align with trend direction
    ├── fibonacci.py    — Fib retracement: entry within 0.5% of 38.2/50/61.8% levels
    ├── bollinger.py    — BB squeeze: squeeze + breakout + volume confirmation (3-gate)
    ├── elliott_wave.py — EWT W3 entry: confirmed pivots, W2 retracement 23.6–78.6%, 161.8% target
    └── combined.py     — Weighted vote across all 5 strategies; weights from DB win rates
```

---

## Async strategy

The backend is fully async (FastAPI + asyncpg). The one exception is the Celery worker — Celery is sync by default. The bridge is `asyncio.run()` at the task entry point, which creates a dedicated event loop per task. This is safe because each Celery worker process handles one task at a time.

yfinance uses `requests` (sync/blocking) under the hood. This blocks the event loop inside the task's async helpers. This is acceptable because the Celery worker is dedicated to that task and there's no concurrency concern within a single worker. If we needed to scan faster, we'd use multiple Celery workers (`--concurrency=4`).

**NullPool on the SQLAlchemy engine:** Celery forks worker processes after importing the module. The parent creates the engine (and its asyncpg connection pool) bound to event loop A. Forked children inherit the engine object but run a fresh event loop B — any pooled connections are now "attached to a different loop" and will crash. `NullPool` disables connection reuse entirely: each `AsyncSessionLocal()` creates a fresh connection and closes it immediately. Slightly slower but correct. FastAPI is unaffected since it uses a single long-lived event loop.
