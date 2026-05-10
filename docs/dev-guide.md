# Developer Guide

## Documentation rule

**Docs stay in sync with code — always, in the same change.**
See `CLAUDE.md` for the full rule and which doc to update for each type of change.

---

## Port assignments

| Service | Host port | Container port | Note |
|---------|-----------|---------------|------|
| Frontend | 3000 | 3000 | Next.js |
| Backend API | 8000 | 8000 | FastAPI |
| PostgreSQL | **5433** | 5432 | Non-standard — 5432 may be taken by other projects |
| Redis | **6380** | 6379 | Non-standard — 6379 may be taken by other projects |

---

## First time setup

```bash
# 1. Clone
git clone <repo>
cd stock-soup

# 2. Copy env
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and NEXTAUTH_SECRET

# 3. Start
docker-compose up -d

# 4. Watch logs
docker-compose logs -f backend worker beat
```

---

## Daily dev workflow

```bash
# Start with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Backend logs
docker-compose logs -f backend

# Worker logs (see scan progress + bot trades)
docker-compose logs -f worker

# Beat logs (see scheduled task firings)
docker-compose logs -f beat

# Open shell in backend container
docker-compose exec backend bash

# Open shell in frontend container
docker-compose exec frontend sh
```

---

## Adding a new API endpoint

1. Add the route in `backend/app/modules/<module>/router.py`
2. Add request/response Pydantic schemas in `schemas.py`
3. Add business logic in the appropriate service file (`screener.py`, `scorer.py`, etc.)
4. Register the router in `backend/app/main.py` if it's a new module

---

## Adding a database model

1. Create or edit the model in `backend/app/models/`
2. Import it in `backend/app/models/__init__.py`
3. Generate a migration:
   ```bash
   docker-compose exec backend alembic revision --autogenerate -m "add your description"
   ```
4. Apply it:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```
5. The migration file is in `backend/alembic/versions/` — commit it to git

---

## Adding a new Celery task

1. Create or edit `backend/app/tasks/scan_tasks.py` (or a new file)
2. Decorate with `@celery_app.task`
3. Add the module to `include` in `celery_app.py` if new file
4. Call with `.delay(args)` from your router

For scheduled (periodic) tasks, add an entry to `beat_schedule` in `celery_app.py`:
```python
beat_schedule={
    "my-task-every-5-minutes": {
        "task": "tasks.my_task_name",
        "schedule": 300,
    },
}
```
The `beat` Docker service handles firing these — no code change needed to the worker.

---

## Adding a new frontend page

Next.js App Router: file path = URL path.

```
src/app/vi/page.tsx          → /vi
src/app/vi/[ticker]/page.tsx → /vi/AAPL
src/app/bot/page.tsx         → /bot
```

For client-side data fetching, use React Query:
```tsx
const { data, isLoading } = useQuery({
  queryKey: ['vi-scans'],
  queryFn: viApi.listScans,
})
```

For polling (scan status updates):
```tsx
useQuery({
  queryKey: ['vi-scan', id],
  queryFn: () => viApi.getScan(id),
  refetchInterval: (query) =>
    query.state.data?.status === 'running' ? 3000 : false,
})
```

---

## Running scans locally (without Docker)

If you prefer running the backend directly:

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set env vars (or create .env in backend/)
export DATABASE_URL=postgresql+asyncpg://stocksoup:stocksoup@localhost:5432/stocksoup
export REDIS_URL=redis://localhost:6379/0

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload

# In another terminal, start worker
celery -A app.tasks.celery_app worker --loglevel=info
```

PostgreSQL and Redis still need to be running (Docker is the easiest way).

---

## Useful Docker commands

```bash
# Stop everything
docker-compose down

# Stop and delete data (WARNING: deletes the database)
docker-compose down -v

# Rebuild after Dockerfile changes
docker-compose build

# Rebuild one service
docker-compose build backend

# Check resource usage
docker stats
```

---

## Environment variables reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | `development` | App mode: development \| testnet \| live |
| `SECRET_KEY` | Yes | — | JWT secret for auth (Phase 2) |
| `POSTGRES_PASSWORD` | No | `stocksoup` | DB password |
| `DATABASE_URL` | No | localhost URL | Full async DB URL |
| `REDIS_URL` | No | localhost URL | Redis connection |
| `TRADING_MODE` | No | `testnet` | Bot mode: testnet \| paper \| live |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | API URL for frontend |

---

## Known issues

### Wikipedia ticker fetch returns 403 in Docker

**Status: Resolved** — switched to static `_US_UNIVERSE` list in `screener.py` (~200 tickers). Cloudflare blocks Wikipedia HTML scraping from Docker IPs. The static list covers S&P 500 + NASDAQ-100 major constituents and is maintained manually.

---

## Troubleshooting

### Scan stays "pending" forever
→ The Celery worker is not running. Check `docker-compose logs worker`.

### "Connection refused" on API calls
→ Backend not started or unhealthy. Check `docker-compose logs backend`.

### "relation does not exist" DB error
→ Migrations not run. Run `docker-compose exec backend alembic upgrade head`.

### yfinance returns empty data for a ticker
→ Normal for some tickers. The screener skips tickers with no `regularMarketPrice`.
The ticker may be delisted, halted, or the symbol format differs (e.g., `BRK-B` not `BRK.B`).

### Frontend can't reach API
→ Check `NEXT_PUBLIC_API_URL` in `.env`. Must be reachable from the browser, not just inside Docker (so `http://localhost:8000`, not `http://backend:8000`).
