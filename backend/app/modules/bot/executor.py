"""
Order executor — ties together signal, risk check, and Binance API.

Flow:
  1. Get current price, balance, equity, open positions
  2. Run risk check (size_position, drawdown, concurrent limit)
  3. If approved → set leverage → place order → set SL → set TP → log Position to DB
  4. If drawdown kill triggered → close all positions → suspend bot → log
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import settings
from app.models.bot import BotConfig, Position, PortfolioSnapshot
from app.modules.bot.binance_client import BinanceClient
from app.modules.bot.risk import approve_trade, check_drawdown
from app.modules.bot.strategies.rsi import Signal

logger = logging.getLogger(__name__)

_DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
_DEFAULT_LEVERAGE = 3
_TIMEFRAME = "15m"
_CANDLE_LIMIT = 100


async def _get_or_create_config(db: AsyncSession) -> BotConfig:
    result = await db.execute(select(BotConfig).where(BotConfig.id == 1))
    config = result.scalar_one_or_none()
    if not config:
        config = BotConfig(id=1)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def _open_position_count(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).select_from(Position).where(
            Position.trading_mode == settings.trading_mode
        )
    )
    return result.scalar_one()


async def _record_portfolio_snapshot(
    db: AsyncSession,
    client: BinanceClient,
    high_water_mark: float,
) -> PortfolioSnapshot:
    balance = await client.get_balance()
    equity = await client.get_equity()
    hwm = max(high_water_mark, equity)
    _, drawdown_pct = check_drawdown(equity, hwm)

    snap = PortfolioSnapshot(
        trading_mode=settings.trading_mode,
        balance_usdt=balance,
        equity_usdt=equity,
        high_water_mark=hwm,
        drawdown_pct=drawdown_pct,
    )
    db.add(snap)
    await db.commit()
    return snap


async def _latest_hwm(db: AsyncSession) -> float:
    result = await db.execute(
        select(func.max(PortfolioSnapshot.high_water_mark)).where(
            PortfolioSnapshot.trading_mode == settings.trading_mode
        )
    )
    return result.scalar_one() or 0.0


async def execute_signal(
    db: AsyncSession,
    client: BinanceClient,
    symbol: str,
    signal: Signal,
    strategy: str,
) -> None:
    """Attempt to open a position based on an approved signal."""
    if signal.action == "none":
        return

    config = await _get_or_create_config(db)
    if config.is_suspended:
        logger.info("Bot suspended — skipping signal execution")
        return

    balance = await client.get_balance()
    equity = await client.get_equity()
    hwm = await _latest_hwm(db)
    open_count = await _open_position_count(db)

    check = approve_trade(
        is_suspended=config.is_suspended,
        open_positions=open_count,
        balance=balance,
        equity=equity,
        high_water_mark=hwm,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        leverage=_DEFAULT_LEVERAGE,
    )

    if not check.approved:
        logger.info(f"[{symbol}] Risk rejected: {check.reason}")
        # If it was a kill switch, suspend the bot
        if "Kill switch" in check.reason:
            await _trigger_kill_switch(db, client, check.reason)
        return

    logger.info(
        f"[{symbol}] Opening {signal.action.upper()} — "
        f"size={check.position_size} entry={signal.entry_price} "
        f"sl={signal.stop_loss} tp={signal.take_profit}"
    )

    await client.set_leverage(symbol, _DEFAULT_LEVERAGE)

    binance_side = "BUY" if signal.action == "long" else "SELL"
    sl_side = "SELL" if signal.action == "long" else "BUY"

    order = await client.place_order(symbol, binance_side, check.position_size)
    await client.set_stop_loss(symbol, sl_side, check.position_size, signal.stop_loss)
    await client.set_take_profit(symbol, sl_side, check.position_size, signal.take_profit)

    position = Position(
        trading_mode=settings.trading_mode,
        symbol=symbol,
        side=signal.action,
        size=check.position_size,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        leverage=_DEFAULT_LEVERAGE,
        strategy=strategy,
        binance_order_id=order.get("orderId"),
    )
    db.add(position)
    await db.commit()
    logger.info(f"[{symbol}] Position recorded id={position.id}")


async def _trigger_kill_switch(
    db: AsyncSession,
    client: BinanceClient,
    reason: str,
) -> None:
    """Close all open positions and suspend the bot."""
    logger.critical(f"KILL SWITCH TRIGGERED: {reason}")

    positions_result = await db.execute(
        select(Position).where(Position.trading_mode == settings.trading_mode)
    )
    positions = positions_result.scalars().all()

    for pos in positions:
        try:
            await client.close_position(pos.symbol, pos.side, pos.size)
            logger.info(f"Kill switch: closed {pos.symbol} {pos.side}")
        except Exception as e:
            logger.error(f"Kill switch: failed to close {pos.symbol}: {e}")
        await db.delete(pos)

    config = await _get_or_create_config(db)
    config.is_suspended = True
    config.suspension_reason = reason
    await db.commit()
    logger.critical("Bot suspended. Manual reset required via UI.")
