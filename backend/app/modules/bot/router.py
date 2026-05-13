import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.config import settings
from app.models.bot import BotConfig, Position, Trade, PortfolioSnapshot
from app.modules.bot.binance_client import BinanceClient
from app.modules.bot.executor import _get_or_create_config
from app.modules.bot.schemas import (
    BotStatusOut,
    PositionOut,
    TradeOut,
    PortfolioOut,
    TradeStatsOut,
    StrategyStatsOut,
    BotConfigUpdateIn,
    PortfolioSnapshotOut,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status", response_model=BotStatusOut)
async def get_status(db: AsyncSession = Depends(get_db)):
    """Bot status: suspended state, active strategy, trading mode."""
    config = await _get_or_create_config(db)
    async with BinanceClient() as client:
        stub = client.is_stub
    return BotStatusOut(
        is_suspended=config.is_suspended,
        suspension_reason=config.suspension_reason,
        active_strategy=config.active_strategy,
        strategy_params=config.strategy_params,
        trading_mode=settings.trading_mode,
        is_stub=stub,
    )


@router.post("/resume", response_model=BotStatusOut)
async def resume_bot(db: AsyncSession = Depends(get_db)):
    """Manually reset the kill switch and resume the bot."""
    config = await _get_or_create_config(db)
    config.is_suspended = False
    config.suspension_reason = None
    await db.commit()
    await db.refresh(config)
    async with BinanceClient() as client:
        stub = client.is_stub
    return BotStatusOut(
        is_suspended=config.is_suspended,
        suspension_reason=config.suspension_reason,
        active_strategy=config.active_strategy,
        strategy_params=config.strategy_params,
        trading_mode=settings.trading_mode,
        is_stub=stub,
    )


@router.patch("/config", response_model=BotStatusOut)
async def update_config(body: BotConfigUpdateIn, db: AsyncSession = Depends(get_db)):
    """Update strategy and/or params."""
    config = await _get_or_create_config(db)
    if body.active_strategy is not None:
        config.active_strategy = body.active_strategy
    if body.strategy_params is not None:
        config.strategy_params = body.strategy_params
    await db.commit()
    await db.refresh(config)
    async with BinanceClient() as client:
        stub = client.is_stub
    return BotStatusOut(
        is_suspended=config.is_suspended,
        suspension_reason=config.suspension_reason,
        active_strategy=config.active_strategy,
        strategy_params=config.strategy_params,
        trading_mode=settings.trading_mode,
        is_stub=stub,
    )


@router.get("/portfolio", response_model=PortfolioOut)
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    """Latest portfolio balance and drawdown."""
    async with BinanceClient() as client:
        balance = await client.get_balance()
        equity = await client.get_equity()
        stub = client.is_stub

    hwm_result = await db.execute(
        select(func.max(PortfolioSnapshot.high_water_mark)).where(
            PortfolioSnapshot.trading_mode == settings.trading_mode
        )
    )
    hwm = hwm_result.scalar_one() or equity
    drawdown_pct = max(0.0, (hwm - equity) / hwm * 100) if hwm > 0 else 0.0

    return PortfolioOut(
        balance_usdt=balance,
        equity_usdt=equity,
        high_water_mark=hwm,
        drawdown_pct=round(drawdown_pct, 4),
        trading_mode=settings.trading_mode,
        is_stub=stub,
    )


@router.post("/suspend", response_model=BotStatusOut)
async def suspend_bot(db: AsyncSession = Depends(get_db)):
    """Manually pause the bot. Does NOT close positions — use Resume to restart."""
    config = await _get_or_create_config(db)
    config.is_suspended = True
    config.suspension_reason = "Manually suspended via UI"
    await db.commit()
    await db.refresh(config)
    async with BinanceClient() as client:
        stub = client.is_stub
    return BotStatusOut(
        is_suspended=config.is_suspended,
        suspension_reason=config.suspension_reason,
        active_strategy=config.active_strategy,
        strategy_params=config.strategy_params,
        trading_mode=settings.trading_mode,
        is_stub=stub,
    )


@router.get("/positions", response_model=list[PositionOut])
async def get_positions(db: AsyncSession = Depends(get_db)):
    """Open positions enriched with live price and unrealized P&L from Binance."""
    result = await db.execute(
        select(Position)
        .where(Position.trading_mode == settings.trading_mode)
        .order_by(Position.opened_at.desc())
    )
    positions = result.scalars().all()

    prices: dict[str, float] = {}
    async with BinanceClient() as client:
        for symbol in {p.symbol for p in positions}:
            try:
                prices[symbol] = await client.get_price(symbol)
            except Exception:
                pass

    out = []
    for pos in positions:
        price = prices.get(pos.symbol)
        pnl = None
        if price is not None:
            if pos.side == "long":
                pnl = (price - pos.entry_price) * pos.size * pos.leverage
            else:
                pnl = (pos.entry_price - price) * pos.size * pos.leverage
        out.append(PositionOut(
            id=pos.id,
            symbol=pos.symbol,
            side=pos.side,
            size=pos.size,
            entry_price=pos.entry_price,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            leverage=pos.leverage,
            strategy=pos.strategy,
            opened_at=pos.opened_at,
            current_price=round(price, 4) if price is not None else None,
            unrealized_pnl=round(pnl, 2) if pnl is not None else None,
        ))
    return out


@router.get("/trades", response_model=list[TradeOut])
async def get_trades(db: AsyncSession = Depends(get_db), limit: int = 50):
    """Recent closed trades, newest first."""
    result = await db.execute(
        select(Trade)
        .where(Trade.trading_mode == settings.trading_mode)
        .order_by(Trade.closed_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/stats", response_model=TradeStatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Win rate, average P&L, total P&L over all closed trades."""
    result = await db.execute(
        select(Trade).where(Trade.trading_mode == settings.trading_mode)
    )
    trades = result.scalars().all()

    if not trades:
        return TradeStatsOut(
            total_trades=0,
            win_rate_pct=0.0,
            avg_pnl_usdt=0.0,
            total_pnl_usdt=0.0,
            avg_rr=0.0,
        )

    wins = sum(1 for t in trades if t.outcome == "win")
    total_pnl = sum(t.pnl_usdt for t in trades)
    avg_pnl = total_pnl / len(trades)

    # Average R:R — approximated as |pnl / (entry-stop) * entry| when data available
    rr_values = []
    for t in trades:
        risk = abs(t.entry_price - t.stop_loss)
        reward = abs(t.exit_price - t.entry_price)
        if risk > 0:
            rr_values.append(reward / risk)
    avg_rr = sum(rr_values) / len(rr_values) if rr_values else 0.0

    return TradeStatsOut(
        total_trades=len(trades),
        win_rate_pct=round(wins / len(trades) * 100, 2),
        avg_pnl_usdt=round(avg_pnl, 2),
        total_pnl_usdt=round(total_pnl, 2),
        avg_rr=round(avg_rr, 2),
    )


@router.get("/stats/by-strategy", response_model=list[StrategyStatsOut])
async def get_stats_by_strategy(db: AsyncSession = Depends(get_db)):
    """Per-strategy breakdown: trade count, win rate, and P&L."""
    result = await db.execute(
        select(Trade).where(Trade.trading_mode == settings.trading_mode)
    )
    trades = result.scalars().all()

    groups: dict[str, list] = {}
    for t in trades:
        groups.setdefault(t.strategy, []).append(t)

    out = []
    for strategy, ts in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
        wins = sum(1 for t in ts if t.outcome == "win")
        losses = sum(1 for t in ts if t.outcome == "loss")
        total_pnl = sum(t.pnl_usdt for t in ts)
        out.append(StrategyStatsOut(
            strategy=strategy,
            total_trades=len(ts),
            wins=wins,
            losses=losses,
            win_rate_pct=round(wins / len(ts) * 100, 1),
            total_pnl_usdt=round(total_pnl, 2),
            avg_pnl_usdt=round(total_pnl / len(ts), 2),
        ))
    return out


@router.get("/portfolio/history", response_model=list[PortfolioSnapshotOut])
async def get_portfolio_history(db: AsyncSession = Depends(get_db), limit: int = 288):
    """Portfolio snapshots ordered oldest-first for charting (default: last 24h at 5-min intervals)."""
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.trading_mode == settings.trading_mode)
        .order_by(PortfolioSnapshot.recorded_at.desc())
        .limit(limit)
    )
    snaps = result.scalars().all()
    return list(reversed(snaps))


@router.post("/trigger")
async def trigger_cycle():
    """Manually fire a bot cycle. Useful for testing without waiting for the 5-min schedule."""
    from app.tasks.celery_app import celery_app
    task = celery_app.send_task("tasks.run_bot_cycle")
    return {"task_id": task.id, "status": "queued"}
