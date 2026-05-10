from sqlalchemy import String, Float, DateTime, Integer, Boolean, JSON, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.database import Base


class BotConfig(Base):
    """Stores active bot settings. Only one row expected (id=1)."""
    __tablename__ = "bot_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    suspension_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active_strategy: Mapped[str] = mapped_column(String(50), default="rsi")  # rsi | macd | fibonacci | bb
    strategy_params: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PortfolioSnapshot(Base):
    """Periodic snapshots of portfolio balance — used for drawdown calculation."""
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    trading_mode: Mapped[str] = mapped_column(String(20))  # testnet | paper | live
    balance_usdt: Mapped[float] = mapped_column(Float)
    equity_usdt: Mapped[float] = mapped_column(Float)  # balance + unrealised PnL
    high_water_mark: Mapped[float] = mapped_column(Float)  # peak equity seen so far
    drawdown_pct: Mapped[float] = mapped_column(Float)  # current drawdown from HWM
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Position(Base):
    """Currently open position on Binance Futures."""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    trading_mode: Mapped[str] = mapped_column(String(20))  # testnet | paper | live
    symbol: Mapped[str] = mapped_column(String(20), index=True)  # e.g. BTCUSDT
    side: Mapped[str] = mapped_column(String(10))  # long | short
    size: Mapped[float] = mapped_column(Float)  # position size in contracts
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    leverage: Mapped[int] = mapped_column(Integer, default=3)
    strategy: Mapped[str] = mapped_column(String(50))
    binance_order_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Trade(Base):
    """Completed (closed) trade record — source of truth for P&L and win rate."""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    trading_mode: Mapped[str] = mapped_column(String(20))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    side: Mapped[str] = mapped_column(String(10))  # long | short
    size: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    pnl_usdt: Mapped[float] = mapped_column(Float)
    pnl_pct: Mapped[float] = mapped_column(Float)
    outcome: Mapped[str] = mapped_column(String(10))  # win | loss | breakeven
    strategy: Mapped[str] = mapped_column(String(50))
    close_reason: Mapped[str] = mapped_column(String(50))  # take_profit | stop_loss | manual | kill_switch
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
