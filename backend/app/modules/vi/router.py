from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.scan import Scan, ScanResult
from app.modules.vi.schemas import ScanOut, ScanWithResults, ScanResultOut, VIMetrics

router = APIRouter()


@router.post("/scan", response_model=ScanOut, status_code=201)
async def start_scan(db: AsyncSession = Depends(get_db)):
    """Trigger a new VI scan of the US market. Runs in background via Celery."""
    from app.tasks.scan_tasks import run_vi_scan_task  # local import avoids circular init

    scan = Scan(status="pending")
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    run_vi_scan_task.delay(scan.id)
    return scan


@router.get("/scans", response_model=list[ScanOut])
async def list_scans(db: AsyncSession = Depends(get_db)):
    """List the 20 most recent scans."""
    result = await db.execute(
        select(Scan).order_by(Scan.created_at.desc()).limit(20)
    )
    return result.scalars().all()


@router.get("/scans/{scan_id}", response_model=ScanWithResults)
async def get_scan(scan_id: int, db: AsyncSession = Depends(get_db)):
    """Get a scan with its full results, sorted by VI score."""
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    results_query = await db.execute(
        select(ScanResult)
        .where(ScanResult.scan_id == scan_id)
        .order_by(ScanResult.vi_score.desc())
    )
    db_results = results_query.scalars().all()

    return ScanWithResults(
        id=scan.id,
        status=scan.status,
        total_scanned=scan.total_scanned,
        results_count=scan.results_count,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        results=[
            ScanResultOut(
                ticker=r.ticker,
                company_name=r.company_name,
                vi_score=r.vi_score,
                verdict=r.verdict,
                metrics=VIMetrics(**r.metrics),
            )
            for r in db_results
        ],
    )
