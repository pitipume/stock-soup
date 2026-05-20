import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.modules.lab.schemas import (
    BacktestRequest,
    CompareRequest,
    PineScriptRequest, PineScriptResult,
    BacktestJobSubmit, BacktestJobResponse, BacktestHistoryEntry,
)
from app.modules.lab.backtester import _STRATEGIES
from app.modules.lab import pinescript
from app.tasks.lab_tasks import run_lab_backtest, run_lab_compare, get_job, get_history

router = APIRouter()
logger = logging.getLogger(__name__)

_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
_TIMEFRAMES = ["15m", "1h", "4h", "1d"]


@router.get("/config")
async def get_config():
    return {
        "symbols": _SYMBOLS,
        "timeframes": _TIMEFRAMES,
        "strategies": _STRATEGIES,
    }


@router.post("/backtest", response_model=BacktestJobSubmit)
async def backtest(req: BacktestRequest):
    job_id = str(uuid.uuid4())
    params = {
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "strategy": req.strategy,
        "params": req.params,
        "months": req.months,
        "initial_balance": req.initial_balance,
        "leverage": req.leverage,
        "risk_pct": req.risk_pct,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    run_lab_backtest.delay(job_id, params)
    return BacktestJobSubmit(job_id=job_id, status="pending")


@router.post("/compare", response_model=BacktestJobSubmit)
async def compare(req: CompareRequest):
    job_id = str(uuid.uuid4())
    params = {
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "months": req.months,
        "initial_balance": req.initial_balance,
        "leverage": req.leverage,
        "risk_pct": req.risk_pct,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    run_lab_compare.delay(job_id, params)
    return BacktestJobSubmit(job_id=job_id, status="pending")


@router.get("/jobs/{job_id}", response_model=BacktestJobResponse)
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired (7-day TTL).")
    return BacktestJobResponse(
        job_id=job_id,
        status=job["status"],
        mode=job["mode"],
        result=job.get("result"),
        error=job.get("error"),
    )


@router.get("/history", response_model=list[BacktestHistoryEntry])
async def list_history():
    return get_history()


@router.post("/pinescript", response_model=PineScriptResult)
async def export_pinescript(req: PineScriptRequest):
    try:
        code = pinescript.generate(req.strategy, req.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PineScriptResult(strategy=req.strategy, code=code)
