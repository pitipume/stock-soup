"""
Celery task for the trading bot loop.

run_bot_cycle() is called on a schedule (every 5 minutes via Celery Beat,
or manually triggered from the UI). It:
  1. Takes a portfolio snapshot (balance, equity, drawdown)
  2. For each tracked symbol, fetches candles and runs the active strategy
  3. If a signal fires and passes risk checks, opens a position
  4. If drawdown kill switch triggers, closes all positions and suspends

Why asyncio.run(): same reason as scan_tasks — Celery is sync, SQLAlchemy is async.
"""
import asyncio
import logging

from app.database import AsyncSessionLocal
from app.config import settings
from app.modules.bot.binance_client import BinanceClient
from app.modules.bot.executor import (
    execute_signal,
    _record_portfolio_snapshot,
    _get_or_create_config,
    _latest_hwm,
    _trigger_kill_switch,
)
from app.modules.bot.risk import check_drawdown
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Symbols the bot monitors — extend this list to add more markets
_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
_TIMEFRAME = "15m"
_CANDLE_LIMIT = 100


@celery_app.task(bind=True, name="tasks.run_bot_cycle")
def run_bot_cycle(self):
    """One iteration of the bot loop. Triggered every 5 min by Celery Beat."""
    asyncio.run(_execute_bot_cycle())


async def _execute_bot_cycle():
    async with BinanceClient() as client:
        async with AsyncSessionLocal() as db:
            config = await _get_or_create_config(db)
            if config.is_suspended:
                logger.info("Bot suspended — skipping cycle")
                return

            # Portfolio snapshot + kill switch check
            hwm = await _latest_hwm(db)
            snap = await _record_portfolio_snapshot(db, client, hwm)

            kill, drawdown_pct = check_drawdown(snap.equity_usdt, snap.high_water_mark)
            if kill:
                await _trigger_kill_switch(
                    db, client, f"Drawdown {drawdown_pct:.2f}% exceeded limit"
                )
                return

        # Signal check per symbol
        for symbol in _SYMBOLS:
            await _check_symbol(client, symbol, config.active_strategy, config.strategy_params)


async def _check_symbol(client: BinanceClient, symbol: str, strategy: str, params: dict):
    candles = await client.get_klines(symbol, _TIMEFRAME, _CANDLE_LIMIT)

    if strategy == "rsi":
        from app.modules.bot.strategies.rsi import evaluate
        signal = evaluate(candles, params)
    else:
        logger.warning(f"Unknown strategy '{strategy}' — skipping {symbol}")
        return

    logger.info(f"[{symbol}] {strategy.upper()} signal: {signal.action} | {signal.reason}")

    if signal.action != "none":
        async with AsyncSessionLocal() as db:
            async with BinanceClient() as exec_client:
                await execute_signal(db, exec_client, symbol, signal, strategy)
