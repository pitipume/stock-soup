"""
Celery task for running VI scans in the background.

Why asyncio.run() here: Celery workers are sync by default. The DB layer is
async (SQLAlchemy asyncpg). asyncio.run() creates a fresh event loop per task,
which is the standard pattern for calling async code from Celery.

The yfinance calls inside run_vi_scan() are blocking/sync — that's fine because
the Celery worker process is dedicated to this task anyway.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.scan import Scan, ScanResult
from app.modules.vi.screener import fetch_us_universe, run_vi_scan
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.run_vi_scan")
def run_vi_scan_task(self, scan_id: int):
    asyncio.run(_execute_scan(scan_id))


async def _execute_scan(scan_id: int):
    async with AsyncSessionLocal() as db:
        scan = await db.get(Scan, scan_id)
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return

        scan.status = "running"
        await db.commit()

    try:
        logger.info(f"Scan {scan_id}: fetching universe")
        tickers = fetch_us_universe()

        logger.info(f"Scan {scan_id}: scanning {len(tickers)} tickers")
        results = run_vi_scan(tickers)

        async with AsyncSessionLocal() as db:
            scan = await db.get(Scan, scan_id)
            scan.status = "done"
            scan.total_scanned = len(tickers)
            scan.results_count = len(results)
            scan.completed_at = datetime.now(timezone.utc)

            for r in results:
                db.add(ScanResult(
                    scan_id=scan_id,
                    ticker=r["ticker"],
                    company_name=r["company_name"],
                    vi_score=r["vi_score"],
                    verdict=r["verdict"],
                    metrics=r["metrics"],
                ))

            await db.commit()
            logger.info(f"Scan {scan_id}: done — {len(results)} results saved")

    except Exception as e:
        logger.exception(f"Scan {scan_id} failed: {e}")
        async with AsyncSessionLocal() as db:
            scan = await db.get(Scan, scan_id)
            if scan:
                scan.status = "failed"
                await db.commit()
