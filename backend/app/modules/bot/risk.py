"""
Risk management — enforced hard limits from the spec.

All limits are READ from config (settings), never from user input.
"""
import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RiskCheck:
    approved: bool
    reason: str
    position_size: float = 0.0  # contracts to trade


def check_drawdown(equity: float, high_water_mark: float) -> tuple[bool, float]:
    """
    Returns (kill_triggered, drawdown_pct).
    Kill is triggered when drawdown from HWM exceeds max_portfolio_drawdown_pct.
    """
    if high_water_mark <= 0:
        return False, 0.0
    drawdown_pct = (high_water_mark - equity) / high_water_mark * 100
    kill = drawdown_pct >= settings.max_portfolio_drawdown_pct
    return kill, round(drawdown_pct, 4)


def size_position(
    balance: float,
    entry_price: float,
    stop_loss: float,
    leverage: int = 3,
) -> float:
    """
    Position size using fixed fractional (Kelly-lite) sizing.

    Risk amount = balance * max_risk_per_trade_pct / 100
    Risk per contract = |entry - stop| * leverage
    Size = risk_amount / risk_per_contract

    Returns 0 if stop distance is zero (refuses to trade without a stop).
    """
    risk_amount = balance * settings.max_risk_per_trade_pct / 100
    stop_distance = abs(entry_price - stop_loss)

    if stop_distance == 0:
        logger.warning("Stop distance is 0 — refusing to size position")
        return 0.0

    size = risk_amount / stop_distance
    return round(size, 3)


def approve_trade(
    *,
    is_suspended: bool,
    open_positions: int,
    balance: float,
    equity: float,
    high_water_mark: float,
    entry_price: float,
    stop_loss: float,
    leverage: int = 3,
) -> RiskCheck:
    """
    Full pre-trade risk gate. Returns RiskCheck with approved=True only if ALL
    conditions pass. Every rejection reason is logged.
    """
    if is_suspended:
        return RiskCheck(False, "Bot is suspended — manual reset required")

    kill, drawdown_pct = check_drawdown(equity, high_water_mark)
    if kill:
        logger.critical(
            f"Drawdown {drawdown_pct:.2f}% >= limit {settings.max_portfolio_drawdown_pct}% — KILL SWITCH"
        )
        return RiskCheck(False, f"Kill switch: drawdown {drawdown_pct:.2f}%")

    if open_positions >= settings.max_concurrent_positions:
        return RiskCheck(
            False,
            f"Max concurrent positions reached ({settings.max_concurrent_positions})",
        )

    size = size_position(balance, entry_price, stop_loss, leverage)
    if size <= 0:
        return RiskCheck(False, "Position size is zero — stop distance may be invalid")

    return RiskCheck(True, "All risk checks passed", position_size=size)
