# StockSoup — Claude Code Context

## Documentation rule (mandatory)

**Any time you add, change, or remove code — update the relevant docs in the same response.**
No separate "update docs later" steps. Docs and code change together, always.

What to update:
- `CLAUDE.md` — if project structure, commands, or key decisions change
- `README.md` — if setup steps, env vars, or API surface change
- `docs/architecture.md` — if data flow, stack, or module boundaries change
- `docs/vi-scoring.md` — if scoring criteria, thresholds, or universe change
- `docs/trading-bot-spec.md` — if bot logic, risk rules, or strategy order change
- `docs/dev-guide.md` — if dev commands, migration steps, or troubleshooting change

If you add a new module or major feature, create a new file in `docs/`.

## What this project is

Personal investment platform built by Poom. Three modules:
1. **VI Scanner** (Phase 1 — active) — scan US stocks for Value Investing criteria
2. **Trading Bot** (Phase 2) — Binance Futures automation with risk management
3. **Formula Lab** (Phase 3) — backtesting and Pine Script export

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI (async) |
| Task queue | Celery + Redis |
| Database | PostgreSQL + TimescaleDB |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic |
| Frontend | Next.js 14 + Tailwind CSS |
| Data source | yfinance (free, US stocks) |
| Trading API | Binance Futures (Phase 2) |

## Project structure

```
stock-soup/
├── backend/
│   ├── app/
│   │   ├── config.py          # Pydantic Settings — all env vars
│   │   ├── database.py        # SQLAlchemy async engine + Base
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── modules/
│   │   │   ├── vi/            # Value Investing scanner
│   │   │   ├── bot/           # Trading bot (Phase 2)
│   │   │   └── lab/           # Formula Lab (Phase 3)
│   │   └── tasks/             # Celery background jobs
│   ├── alembic/               # DB migrations (run: alembic upgrade head)
│   └── alembic.ini
├── frontend/
│   └── src/
│       ├── app/               # Next.js App Router pages
│       ├── components/        # Shared UI components
│       └── lib/api.ts         # Typed API client
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env.example               # Copy to .env and fill in values
```

## Dev commands

```bash
# First time setup
cp .env.example .env

# Start everything (production-like)
docker-compose up -d

# Start with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run DB migrations manually (inside backend container or with venv)
cd backend && alembic upgrade head

# Generate a new migration after model changes
cd backend && alembic revision --autogenerate -m "describe change"

# Backend API docs
open http://localhost:8000/docs

# Frontend
open http://localhost:3000
```

## Key architectural decisions

- **No auth in Phase 1** — `user_id` is nullable in `Scan` model. Phase 2 adds NextAuth.
- **Celery is sync** — VI scans run in background workers. `asyncio.run()` bridges sync Celery → async SQLAlchemy.
- **yfinance is slow** — scanning 500+ tickers takes 15-30 min. This is expected and by design (free API, no key needed).
- **TRADING_MODE env var** — switches between testnet/paper/live for the bot. Never touch live until 30+ days profitable testnet.
- **D/E ratio from yfinance** — `debtToEquity` is returned in percentage form (50 = 0.5 ratio). Threshold in scorer is `< 50`.

## Risk rules (enforced in code, not configurable in UI)

- Max 1-2% portfolio per trade
- Hard -10% drawdown kill switch
- Max 3 concurrent positions
- Min 1:2 risk-to-reward ratio
- Live trading disabled until `TRADING_MODE=live` is explicitly set

## Phase 1 scope (what to build now)

VI Scanner only:
- `POST /vi/scan` → triggers background scan
- `GET /vi/scans` → scan history
- `GET /vi/scans/{id}` → scan with results

Do NOT add bot or lab features yet. Phase 1 = working VI scanner first.

## Known issues (as of 2026-05-10)

- **Wikipedia scraping blocked in Docker** — Cloudflare 403s on Wikipedia ticker lists. Resolved by using a static `_US_UNIVERSE` list (~200 tickers) in `screener.py`. Update the list manually when index constituents change significantly.

## What NOT to do

- Don't add auth complexity in Phase 1
- Don't touch `TRADING_MODE=live` 
- Don't add Thai stocks yet (Phase 3+)
- Don't scope-creep into bot features during Phase 1
