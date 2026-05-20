"""
Celery tasks for Formula Lab backtests.

Each job is stored in Redis under lab:job:{job_id} (7-day TTL).
A compact summary is also pushed to lab:history (max 100 entries) so the
history tab can list past runs without loading every full result.

Why asyncio.run(): fetch_candles is async; Celery workers are sync threads.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

import redis

from app.config import settings
from app.modules.lab.backtester import fetch_candles, run_backtest, _STRATEGIES
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_redis = redis.from_url(settings.redis_url, decode_responses=True)
_JOB_TTL = 604_800   # 7 days
_HISTORY_KEY = "lab:history"
_HISTORY_MAX = 100

_STRATEGY_LABELS = {
    "rsi": "RSI",
    "macd": "MACD",
    "fibonacci": "Fibonacci",
    "bollinger": "Bollinger Bands",
    "elliott_wave": "Elliott Wave",
    "combined": "Combined",
    "triple_ema_stoch_rsi": "Triple EMA + StochRSI",
}


def _set_job(job_id: str, data: dict):
    _redis.set(f"lab:job:{job_id}", json.dumps(data), ex=_JOB_TTL)


def _update_job(job_id: str, updates: dict):
    raw = _redis.get(f"lab:job:{job_id}")
    if raw:
        data = json.loads(raw)
        data.update(updates)
        _redis.set(f"lab:job:{job_id}", json.dumps(data), ex=_JOB_TTL)


def get_job(job_id: str) -> dict | None:
    raw = _redis.get(f"lab:job:{job_id}")
    return json.loads(raw) if raw else None


def _push_history(entry: dict):
    _redis.lpush(_HISTORY_KEY, json.dumps(entry))
    _redis.ltrim(_HISTORY_KEY, 0, _HISTORY_MAX - 1)


def get_history() -> list[dict]:
    items = _redis.lrange(_HISTORY_KEY, 0, -1)
    return [json.loads(i) for i in items]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summary_from_metrics(metrics) -> dict:
    return {
        "total_pnl_usdt": metrics.total_pnl_usdt,
        "total_pnl_pct": metrics.total_pnl_pct,
        "win_rate_pct": metrics.win_rate_pct,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "total_trades": metrics.total_trades,
    }


@celery_app.task(bind=True, name="tasks.run_lab_backtest")
def run_lab_backtest(self, job_id: str, params: dict):
    created_at = params.get("created_at", _now_iso())
    strategy_label = _STRATEGY_LABELS.get(params.get("strategy", ""), params.get("strategy", ""))
    _update_job(job_id, {"status": "running", "progress": 0, "phase": "Fetching candles…"})
    try:
        candles = asyncio.run(fetch_candles(params["symbol"], params["timeframe"], params["months"]))
        if len(candles) < 300:
            raise ValueError("Not enough historical data for this timeframe/months combination.")
        _update_job(job_id, {"progress": 50, "phase": f"Running {strategy_label}…"})
        result = run_backtest(
            candles,
            params["symbol"],
            params["strategy"],
            params.get("params", {}),
            params["initial_balance"],
            params["leverage"],
            params["risk_pct"],
            params["timeframe"],
            params["months"],
        )
        _set_job(job_id, {
            "status": "done", "mode": "backtest",
            "result": result.model_dump(), "error": None,
            "progress": 100, "phase": "Done",
        })
        _push_history({
            "job_id": job_id,
            "created_at": created_at,
            "mode": "backtest",
            "symbol": params["symbol"],
            "timeframe": params["timeframe"],
            "months": params["months"],
            "strategy": params["strategy"],
            "status": "done",
            **_summary_from_metrics(result.metrics),
        })
    except Exception as e:
        logger.error(f"Lab backtest {job_id} failed: {e}")
        _update_job(job_id, {"status": "failed", "result": None, "error": str(e), "phase": "Failed"})
        _push_history({
            "job_id": job_id,
            "created_at": created_at,
            "mode": "backtest",
            "symbol": params["symbol"],
            "timeframe": params["timeframe"],
            "months": params["months"],
            "strategy": params["strategy"],
            "status": "failed",
        })


@celery_app.task(bind=True, name="tasks.run_lab_compare")
def run_lab_compare(self, job_id: str, params: dict):
    created_at = params.get("created_at", _now_iso())
    _update_job(job_id, {"status": "running", "progress": 0, "phase": "Fetching candles…"})
    try:
        candles = asyncio.run(fetch_candles(params["symbol"], params["timeframe"], params["months"]))
        if len(candles) < 300:
            raise ValueError("Not enough historical data.")

        strategies = params.get("strategies") or _STRATEGIES
        n = len(strategies)
        results = []
        for i, strategy in enumerate(strategies):
            label = _STRATEGY_LABELS.get(strategy, strategy)
            pct = 10 + int((i / n) * 85)
            _update_job(job_id, {"progress": pct, "phase": f"Strategy {i + 1}/{n} — {label}"})
            r = run_backtest(
                candles,
                params["symbol"],
                strategy,
                {},
                params["initial_balance"],
                params["leverage"],
                params["risk_pct"],
                params["timeframe"],
                params["months"],
            )
            results.append(r)

        results.sort(key=lambda r: r.metrics.total_pnl_usdt, reverse=True)
        best = results[0]
        _set_job(job_id, {
            "status": "done", "mode": "compare",
            "result": [r.model_dump() for r in results],
            "error": None, "progress": 100, "phase": "Done",
        })
        _push_history({
            "job_id": job_id,
            "created_at": created_at,
            "mode": "compare",
            "symbol": params["symbol"],
            "timeframe": params["timeframe"],
            "months": params["months"],
            "strategy": "compare_all",
            "status": "done",
            **_summary_from_metrics(best.metrics),
        })
    except Exception as e:
        logger.error(f"Lab compare {job_id} failed: {e}")
        _update_job(job_id, {"status": "failed", "result": None, "error": str(e), "phase": "Failed"})
        _push_history({
            "job_id": job_id,
            "created_at": created_at,
            "mode": "compare",
            "symbol": params["symbol"],
            "timeframe": params["timeframe"],
            "months": params["months"],
            "strategy": "compare_all",
            "status": "failed",
        })
