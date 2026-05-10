"""
Binance Futures connector.

Routes to testnet or live based on TRADING_MODE.
When no API keys are set, falls back to stub responses so the rest of
the system (strategy, risk, DB) can be developed and tested without credentials.
"""
import hmac
import hashlib
import time
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TESTNET_BASE = "https://testnet.binancefuture.com"
_LIVE_BASE = "https://fapi.binance.com"

# Stub portfolio returned when no keys are configured
_STUB_BALANCE = 10_000.0


class BinanceClient:
    """
    Thin async wrapper around the Binance Futures REST API.

    Usage:
        async with BinanceClient() as client:
            balance = await client.get_balance()
    """

    def __init__(self) -> None:
        if settings.trading_mode == "live":
            self._base = _LIVE_BASE
            self._api_key = settings.binance_live_api_key
            self._secret = settings.binance_live_secret_key
        else:
            self._base = _TESTNET_BASE
            self._api_key = settings.binance_testnet_api_key
            self._secret = settings.binance_testnet_secret_key

        self._stub = not (self._api_key and self._secret)
        if self._stub:
            logger.warning(
                "Binance API keys not set — running in stub mode. "
                "Set BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_SECRET_KEY to connect."
            )

    async def __aenter__(self):
        self._client = httpx.AsyncClient(base_url=self._base, timeout=10.0)
        return self

    async def __aexit__(self, *_):
        await self._client.aclose()

    # ── Signed request ────────────────────────────────────────────────────────

    def _sign(self, params: dict) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        query = urlencode(params)
        sig = hmac.new(self._secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    async def _get(self, path: str, params: dict | None = None, signed: bool = False) -> Any:
        p = params or {}
        if signed:
            p = self._sign(p)
        r = await self._client.get(path, params=p, headers={"X-MBX-APIKEY": self._api_key})
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, params: dict) -> Any:
        params = self._sign(params)
        r = await self._client.post(
            path,
            params=params,
            headers={"X-MBX-APIKEY": self._api_key},
        )
        r.raise_for_status()
        return r.json()

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_balance(self) -> float:
        """Return available USDT balance."""
        if self._stub:
            return _STUB_BALANCE

        data = await self._get("/fapi/v2/balance", signed=True)
        for asset in data:
            if asset["asset"] == "USDT":
                return float(asset["availableBalance"])
        return 0.0

    async def get_equity(self) -> float:
        """Return total equity (balance + unrealised PnL)."""
        if self._stub:
            return _STUB_BALANCE

        data = await self._get("/fapi/v2/account", signed=True)
        return float(data["totalWalletBalance"]) + float(data["totalUnrealizedProfit"])

    async def get_price(self, symbol: str) -> float:
        """Latest mark price for a symbol (e.g. BTCUSDT)."""
        if self._stub:
            return _STUB_PRICES.get(symbol, 100.0)

        data = await self._get("/fapi/v1/premiumIndex", params={"symbol": symbol})
        return float(data["markPrice"])

    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> list[dict]:
        """
        OHLCV candles. interval: 1m, 5m, 15m, 1h, 4h, 1d.
        Returns list of dicts with keys: open_time, open, high, low, close, volume.
        """
        if self._stub:
            return _stub_klines(limit, symbol)

        raw = await self._get(
            "/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        return [
            {
                "open_time": r[0],
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4]),
                "volume": float(r[5]),
            }
            for r in raw
        ]

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ) -> dict:
        """Place a futures order. side: BUY | SELL."""
        if self._stub:
            logger.info(f"[stub] {order_type} {side} {quantity} {symbol}")
            return {
                "orderId": f"stub-{int(time.time())}",
                "status": "FILLED",
                "symbol": symbol,
                "side": side,
                "executedQty": str(quantity),
                "avgPrice": str(await self.get_price(symbol)),
            }

        return await self._post(
            "/fapi/v1/order",
            {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
            },
        )

    async def set_stop_loss(self, symbol: str, side: str, quantity: float, stop_price: float) -> dict:
        """Place a STOP_MARKET order (stop loss). side is the closing side (opposite of position)."""
        if self._stub:
            logger.info(f"[stub] STOP_MARKET {side} {quantity} {symbol} @ {stop_price}")
            return {"orderId": f"stub-sl-{int(time.time())}", "status": "NEW"}

        return await self._post(
            "/fapi/v1/order",
            {
                "symbol": symbol,
                "side": side,
                "type": "STOP_MARKET",
                "quantity": quantity,
                "stopPrice": stop_price,
                "closePosition": "false",
            },
        )

    async def set_take_profit(self, symbol: str, side: str, quantity: float, stop_price: float) -> dict:
        """Place a TAKE_PROFIT_MARKET order."""
        if self._stub:
            logger.info(f"[stub] TAKE_PROFIT_MARKET {side} {quantity} {symbol} @ {stop_price}")
            return {"orderId": f"stub-tp-{int(time.time())}", "status": "NEW"}

        return await self._post(
            "/fapi/v1/order",
            {
                "symbol": symbol,
                "side": side,
                "type": "TAKE_PROFIT_MARKET",
                "quantity": quantity,
                "stopPrice": stop_price,
                "closePosition": "false",
            },
        )

    async def close_position(self, symbol: str, side: str, quantity: float) -> dict:
        """Close an open position at market price."""
        close_side = "SELL" if side == "long" else "BUY"
        return await self.place_order(symbol, close_side, quantity)

    async def set_leverage(self, symbol: str, leverage: int) -> dict:
        if self._stub:
            return {"leverage": leverage, "symbol": symbol}
        return await self._post("/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage})

    @property
    def is_stub(self) -> bool:
        return self._stub

    @property
    def mode(self) -> str:
        return settings.trading_mode


# ── Stub helpers ──────────────────────────────────────────────────────────────

_STUB_PRICES: dict[str, float] = {"BTCUSDT": 65_000.0, "ETHUSDT": 3_200.0, "SOLUSDT": 145.0}


def _stub_klines(n: int, symbol: str = "BTCUSDT") -> list[dict]:
    """Generate synthetic trending candles for strategy testing."""
    import random
    price = _STUB_PRICES.get(symbol, 100.0)
    candles = []
    t = int(time.time() * 1000) - n * 60_000
    for _ in range(n):
        change = random.uniform(-0.015, 0.015)
        open_ = price
        close = price * (1 + change)
        high = max(open_, close) * random.uniform(1.0, 1.005)
        low = min(open_, close) * random.uniform(0.995, 1.0)
        candles.append({
            "open_time": t,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": random.uniform(100, 2000),
        })
        price = close
        t += 60_000
    return candles
