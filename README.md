# StockSoup

> Value Investing meets Technical Trading. Built by Poom, for Poom.

---

## What it does

| Module | Status | Description |
|--------|--------|-------------|
| **VI Scanner** | Phase 1 (active) | Screens US stocks using Warren Buffett / Peter Lynch criteria |
| **Trading Bot** | Phase 2 | Automated Binance Futures trading with RSI, MACD, Elliott Wave strategies |
| **Formula Lab** | Phase 3 | Backtesting engine + Pine Script export for TradingView |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- That's it. No Python or Node needed locally.

### 1. Clone and configure

```bash
git clone <repo-url>
cd stock-soup
cp .env.example .env
```

Open `.env` and set at minimum:
```
SECRET_KEY=any-long-random-string
NEXTAUTH_SECRET=any-long-random-string
```

### 2. Start everything

```bash
docker-compose up -d
```

This starts:
- PostgreSQL + TimescaleDB on port `5432`
- Redis on port `6379`
- FastAPI backend on port `8000`
- Celery worker (background scan processor)
- Next.js frontend on port `3000`

First run takes ~3-5 minutes to pull images and build.

### 3. Open the app

```
http://localhost:3000
```

### 4. Run your first scan

Click **"Scan US Markets"** on the VI Scanner page.

> Scanning 500+ stocks takes **15–30 minutes** because we fetch fundamentals
> from Yahoo Finance one ticker at a time (free, no API key needed).
> The scan runs in the background — you can close the tab and come back.

---

## Development (with hot reload)

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Backend reloads on file save. Frontend uses Next.js hot reload.

---

## API

Auto-generated API docs at:

```
http://localhost:8000/docs
```

Key endpoints:

```
POST /vi/scan           — start a new scan
GET  /vi/scans          — list recent scans
GET  /vi/scans/{id}     — get scan + results
GET  /health            — service health check
```

---

## Database migrations

After changing a SQLAlchemy model:

```bash
# Enter the backend container
docker-compose exec backend bash

# Generate migration
alembic revision --autogenerate -m "describe your change"

# Apply
alembic upgrade head
```

---

## VI Scoring criteria

| Metric | Threshold | Points |
|--------|-----------|--------|
| P/E ratio | < 15 | 15 |
| P/B ratio | < 1.5 | 15 |
| Debt/Equity | < 0.5 | 15 |
| ROE | > 15% | 15 |
| Revenue growth | > 10% YoY | 15 |
| Free cash flow | Positive | 15 |
| Insider ownership | > 5% | 10 |

**Hidden gem bonus (+5):** market cap < $2B AND analyst coverage < 5 firms

Verdict thresholds: Strong Buy ≥ 75 · Buy ≥ 55 · Hold ≥ 35 · Skip < 35

---

## Project structure

```
stock-soup/
├── backend/
│   ├── app/
│   │   ├── config.py          # All settings (Pydantic Settings v2)
│   │   ├── database.py        # Async SQLAlchemy engine
│   │   ├── main.py            # FastAPI app
│   │   ├── models/            # ORM models: User, Stock, Scan, ScanResult
│   │   ├── modules/vi/        # VI screener, scorer, API routes
│   │   └── tasks/             # Celery tasks
│   └── alembic/               # DB migrations
├── frontend/
│   └── src/
│       ├── app/               # Next.js pages (App Router)
│       ├── components/        # Nav, shared UI
│       └── lib/api.ts         # Typed API client
├── docs/                      # Architecture + decision docs
├── docker-compose.yml
└── .env.example
```

---

## Tech stack rationale

Python over C# for the backend — not preference, necessity. The financial data
ecosystem (yfinance, pandas, ta-lib, ccxt) lives in Python. There's no
equivalent .NET alternative.

Full rationale in [docs/architecture.md](docs/architecture.md).

---

## Roadmap

| Phase | Feature | Timeline (1hr/day) |
|-------|---------|-------------------|
| 1 | VI Scanner — US stocks | 6–8 weeks |
| 2 | Trading Bot — Binance testnet | 8–12 weeks |
| 3 | Formula Lab + backtesting | 8–12 weeks |
| 4 | Thai/EU markets + ML layer | Ongoing |

**Rule:** Live trading only after 30+ profitable testnet days and > 55% win rate over 100+ trades.
