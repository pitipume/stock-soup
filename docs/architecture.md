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
  → fetch_us_universe()      ← Wikipedia scrape (S&P 500 + NASDAQ-100)
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

## Module boundaries

Each module (`vi`, `bot`, `lab`) is fully self-contained:
- `router.py` — FastAPI routes
- `schemas.py` — Pydantic request/response models
- `screener.py` / `executor.py` — business logic
- `scorer.py` / `strategies/` — domain algorithms

No cross-module imports. Shared infra (DB session, config) comes from `app/database.py` and `app/config.py`.

---

## Async strategy

The backend is fully async (FastAPI + asyncpg). The one exception is the Celery worker — Celery is sync by default. The bridge is `asyncio.run()` at the task entry point, which creates a dedicated event loop per task. This is safe because each Celery worker process handles one task at a time.

yfinance uses `requests` (sync/blocking) under the hood. This blocks the event loop inside the task's async helpers. This is acceptable because the Celery worker is dedicated to that task and there's no concurrency concern within a single worker. If we needed to scan faster, we'd use multiple Celery workers (`--concurrency=4`).
