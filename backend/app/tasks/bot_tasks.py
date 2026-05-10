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


@celery_app.task(bind=True, name="tasks.sync_positions")
def sync_positions(self):
    """
    Poll Binance every minute to detect closed positions (SL/TP filled).
    Moves closed positions from positions table → trades table with P&L.
    """
    asyncio.run(_sync_closed_positions())


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


async def _fetch_strategy_weights(
    trading_mode: str,
    min_trades: int = 5,
    lookback_days: int = 30,
) -> dict:
    """
    Query the trades table for each strategy's recent win rate.
    Returns a dict like {"rsi": 0.62, "macd": 0.48, ...}.

    Strategies with fewer than min_trades records default to 0.5 (neutral).
    This prevents a lucky early trade from over-weighting a strategy before
    it has enough data to be statistically meaningful.
    """
    from app.models.bot import Trade
    from sqlalchemy import select, func, case
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                Trade.strategy,
                func.count().label("total"),
                func.sum(
                    case((Trade.outcome == "win", 1), else_=0)
                ).label("wins"),
            )
            .where(Trade.trading_mode == trading_mode)
            .where(Trade.opened_at >= cutoff)
            .group_by(Trade.strategy)
        )
        rows = result.all()

    weights = {}
    for row in rows:
        if row.total >= min_trades:
            weights[row.strategy] = round(row.wins / row.total, 4)
        else:
            weights[row.strategy] = 0.5

    for strat in ["rsi", "macd", "fibonacci", "bollinger", "elliott_wave"]:
        weights.setdefault(strat, 0.5)

    logger.debug(f"Strategy weights ({lookback_days}d, mode={trading_mode}): {weights}")
    return weights


async def _check_symbol(client: BinanceClient, symbol: str, strategy: str, params: dict):
    candles = await client.get_klines(symbol, _TIMEFRAME, _CANDLE_LIMIT)

    if strategy == "rsi":
        from app.modules.bot.strategies.rsi import evaluate
        signal = evaluate(candles, params)
    elif strategy == "macd":
        from app.modules.bot.strategies.macd import evaluate
        signal = evaluate(candles, params)
    elif strategy == "fibonacci":
        from app.modules.bot.strategies.fibonacci import evaluate
        signal = evaluate(candles, params)
    elif strategy == "bollinger":
        from app.modules.bot.strategies.bollinger import evaluate
        signal = evaluate(candles, params)
    elif strategy == "elliott_wave":
        from app.modules.bot.strategies.elliott_wave import evaluate
        signal = evaluate(candles, params)
    elif strategy == "combined":
        from app.modules.bot.strategies.combined import evaluate
        weights = await _fetch_strategy_weights(settings.trading_mode)
        # Merge live weights into user params — user params take precedence if set explicitly
        merged = {
            "rsi_weight":          weights["rsi"],
            "macd_weight":         weights["macd"],
            "fibonacci_weight":    weights["fibonacci"],
            "bollinger_weight":    weights["bollinger"],
            "elliott_wave_weight": weights["elliott_wave"],
        }
        merged.update(params or {})
        signal = evaluate(candles, merged)
    else:
        logger.warning(f"Unknown strategy '{strategy}' — skipping {symbol}")
        return

    logger.info(f"[{symbol}] {strategy.upper()} signal: {signal.action} | {signal.reason}")

    if signal.action != "none":
        async with AsyncSessionLocal() as db:
            async with BinanceClient() as exec_client:
                await execute_signal(db, exec_client, symbol, signal, strategy)


async def _sync_closed_positions():
    """
    For each open Position in DB, check if Binance still has it open.
    If not, calculate P&L and record a Trade.

    In stub mode: randomly close ~10% of positions per cycle to simulate SL/TP hits.
    """
    from app.models.bot import Position, Trade
    from sqlalchemy import select
    from datetime import datetime, timezone
    import random

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Position).where(Position.trading_mode == settings.trading_mode)
        )
        positions = result.scalars().all()

        if not positions:
            return

        async with BinanceClient() as client:
            for pos in positions:
                closed = await _is_position_closed(client, pos)
                if not closed:
                    continue

                exit_price = await client.get_price(pos.symbol)
                pnl_usdt, pnl_pct, outcome, close_reason = _calc_pnl(pos, exit_price)

                trade = Trade(
                    trading_mode=pos.trading_mode,
                    symbol=pos.symbol,
                    side=pos.side,
                    size=pos.size,
                    entry_price=pos.entry_price,
                    exit_price=exit_price,
                    stop_loss=pos.stop_loss,
                    take_profit=pos.take_profit,
                    pnl_usdt=pnl_usdt,
                    pnl_pct=pnl_pct,
                    outcome=outcome,
                    strategy=pos.strategy,
                    close_reason=close_reason,
                    opened_at=pos.opened_at,
                )
                db.add(trade)
                await db.delete(pos)
                logger.info(
                    f"Position closed: {pos.symbol} {pos.side} | "
                    f"P&L={pnl_usdt:+.2f} USDT ({outcome})"
                )

        await db.commit()


async def _is_position_closed(client: BinanceClient, pos) -> bool:
    """Return True if the position has been closed on Binance."""
    if client.is_stub:
        # Stub: 10% chance per check that the position closes (simulates SL/TP)
        import random
        return random.random() < 0.10

    try:
        data = await client._get(
            "/fapi/v2/positionRisk",
            params={"symbol": pos.symbol},
            signed=True,
        )
        for p in data:
            if p["symbol"] == pos.symbol:
                return float(p["positionAmt"]) == 0.0
    except Exception as e:
        logger.error(f"Failed to check position {pos.symbol}: {e}")
    return False


def _calc_pnl(pos, exit_price: float) -> tuple[float, float, str, str]:
    """Calculate P&L and determine outcome and close reason."""
    if pos.side == "long":
        pnl_usdt = (exit_price - pos.entry_price) * pos.size * pos.leverage
        hit_tp = exit_price >= pos.take_profit
        hit_sl = exit_price <= pos.stop_loss
    else:
        pnl_usdt = (pos.entry_price - exit_price) * pos.size * pos.leverage
        hit_tp = exit_price <= pos.take_profit
        hit_sl = exit_price >= pos.stop_loss

    pnl_pct = pnl_usdt / (pos.entry_price * pos.size) * 100
    outcome = "win" if pnl_usdt > 0 else ("loss" if pnl_usdt < 0 else "breakeven")

    if hit_tp:
        close_reason = "take_profit"
    elif hit_sl:
        close_reason = "stop_loss"
    else:
        close_reason = "manual"

    return round(pnl_usdt, 4), round(pnl_pct, 4), outcome, close_reason
