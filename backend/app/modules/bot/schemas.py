from pydantic import BaseModel
from datetime import datetime


class BotStatusOut(BaseModel):
    is_suspended: bool
    suspension_reason: str | None
    active_strategy: str
    strategy_params: dict
    trading_mode: str
    is_stub: bool


class PositionOut(BaseModel):
    id: int
    symbol: str
    side: str
    size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    leverage: int
    strategy: str
    opened_at: datetime

    class Config:
        from_attributes = True


class TradeOut(BaseModel):
    id: int
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: float
    pnl_usdt: float
    pnl_pct: float
    outcome: str
    strategy: str
    close_reason: str
    opened_at: datetime
    closed_at: datetime

    class Config:
        from_attributes = True


class PortfolioOut(BaseModel):
    balance_usdt: float
    equity_usdt: float
    high_water_mark: float
    drawdown_pct: float
    trading_mode: str
    is_stub: bool


class TradeStatsOut(BaseModel):
    total_trades: int
    win_rate_pct: float
    avg_pnl_usdt: float
    total_pnl_usdt: float
    avg_rr: float


class BotConfigUpdateIn(BaseModel):
    active_strategy: str | None = None
    strategy_params: dict | None = None
