from pydantic import BaseModel
from typing import Any


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    strategy: str = "combined"
    params: dict[str, Any] = {}
    months: int = 3
    initial_balance: float = 10_000.0
    leverage: int = 3
    risk_pct: float = 0.01


class BacktestTrade(BaseModel):
    side: str
    entry_price: float
    exit_price: float
    pnl_usdt: float
    pnl_pct: float
    outcome: str
    close_reason: str
    entry_time: int
    exit_time: int


class BacktestMetrics(BaseModel):
    total_trades: int
    wins: int
    losses: int
    win_rate_pct: float
    total_pnl_usdt: float
    total_pnl_pct: float
    max_drawdown_pct: float
    avg_rr: float


class BacktestResult(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    months: int
    initial_balance: float
    final_balance: float
    metrics: BacktestMetrics
    trades: list[BacktestTrade]
    equity_curve: list[float]
    equity_times: list[int]


class CompareRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    months: int = 3
    initial_balance: float = 10_000.0
    leverage: int = 3
    risk_pct: float = 0.01


class PineScriptRequest(BaseModel):
    strategy: str
    params: dict[str, Any] = {}


class PineScriptResult(BaseModel):
    strategy: str
    code: str


class BacktestJobSubmit(BaseModel):
    job_id: str
    status: str


class BacktestHistoryEntry(BaseModel):
    job_id: str
    created_at: str
    mode: str          # "backtest" | "compare"
    symbol: str
    timeframe: str
    months: int
    strategy: str      # strategy name or "compare_all"
    status: str
    total_pnl_usdt: float | None = None
    total_pnl_pct: float | None = None
    win_rate_pct: float | None = None
    max_drawdown_pct: float | None = None
    total_trades: int | None = None


class BacktestJobResponse(BaseModel):
    job_id: str
    status: str
    mode: str
    result: Any = None
    error: str | None = None
