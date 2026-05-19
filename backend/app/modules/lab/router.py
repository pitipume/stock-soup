import asyncio
import logging
from fastapi import APIRouter, HTTPException

from app.modules.lab.schemas import (
    BacktestRequest, BacktestResult,
    CompareRequest,
    PineScriptRequest, PineScriptResult,
)
from app.modules.lab.backtester import fetch_candles, run_backtest, _STRATEGIES
from app.modules.lab import pinescript

router = APIRouter()
logger = logging.getLogger(__name__)

_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
_TIMEFRAMES = ["15m", "1h", "4h", "1d"]


@router.get("/config")
async def get_config():
    """Available symbols, timeframes, and strategies for the UI dropdowns."""
    return {
        "symbols": _SYMBOLS,
        "timeframes": _TIMEFRAMES,
        "strategies": _STRATEGIES,
    }


@router.post("/backtest", response_model=BacktestResult)
async def backtest(req: BacktestRequest):
    """Run a walk-forward backtest for a single strategy."""
    try:
        candles = await fetch_candles(req.symbol, req.timeframe, req.months)
    except Exception as e:
        logger.error(f"Failed to fetch candles: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch candles from Binance: {e}")

    if len(candles) < 300:
        raise HTTPException(status_code=400, detail="Not enough historical data for this timeframe/months combination.")

    result = await asyncio.get_event_loop().run_in_executor(
        None,
        run_backtest,
        candles,
        req.symbol,
        req.strategy,
        req.params,
        req.initial_balance,
        req.leverage,
        req.risk_pct,
        req.timeframe,
        req.months,
    )
    return result


@router.post("/compare", response_model=list[BacktestResult])
async def compare(req: CompareRequest):
    """Run all strategies on the same data and return results for comparison."""
    try:
        candles = await fetch_candles(req.symbol, req.timeframe, req.months)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch candles: {e}")

    if len(candles) < 300:
        raise HTTPException(status_code=400, detail="Not enough historical data.")

    loop = asyncio.get_event_loop()
    results = []
    for strategy in _STRATEGIES:
        result = await loop.run_in_executor(
            None,
            run_backtest,
            candles,
            req.symbol,
            strategy,
            {},
            req.initial_balance,
            req.leverage,
            req.risk_pct,
            req.timeframe,
            req.months,
        )
        results.append(result)

    results.sort(key=lambda r: r.metrics.total_pnl_usdt, reverse=True)
    return results


@router.post("/pinescript", response_model=PineScriptResult)
async def export_pinescript(req: PineScriptRequest):
    """Generate TradingView Pine Script v5 code for a strategy."""
    try:
        code = pinescript.generate(req.strategy, req.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PineScriptResult(strategy=req.strategy, code=code)
