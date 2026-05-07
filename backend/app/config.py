from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "testnet", "live"] = "development"
    secret_key: str = "dev-secret-change-in-production"

    database_url: str = "postgresql+asyncpg://stocksoup:stocksoup@localhost:5432/stocksoup"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    trading_mode: Literal["testnet", "paper", "live"] = "testnet"
    binance_testnet_api_key: str = ""
    binance_testnet_secret_key: str = ""
    binance_live_api_key: str = ""
    binance_live_secret_key: str = ""

    max_risk_per_trade_pct: float = 1.0
    max_portfolio_drawdown_pct: float = 10.0
    max_concurrent_positions: int = 3


settings = Settings()
