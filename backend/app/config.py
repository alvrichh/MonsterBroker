"""Runtime settings, read from the environment and an optional .env file.

Everything has a working default: with no keys at all the app serves public
prices, trades on paper and collects news without AI summaries.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # The repo-root .env first, then backend/.env on top of it.
    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MonsterBroker API"
    environment: str = "development"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Market data and trading. Live keys are read but never used for orders:
    # see app/agent/executor.py.
    exchange_id: str = "binance"
    exchange_api_key: str = ""
    exchange_api_secret: str = ""
    paper_trading: bool = True
    paper_starting_balance: float = 10_000.0
    default_symbols: list[str] = ["BTC/USDT", "ETH/USDT", "LTC/USDT", "SOL/USDT"]
    default_timeframe: str = "1h"
    default_strategy: str = "sma_cross"

    # Claude: reviews the agent's signals and writes the news digest.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"

    # Web3: any JSON-RPC endpoint. Empty disables the wallet routes.
    web3_rpc_url: str = ""

    # News radar
    news_auto_refresh: bool = False
    news_refresh_minutes: int = 60

    # Auth
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24

    data_dir: Path = BACKEND_DIR / "data"
    logs_dir: Path = BACKEND_DIR / "logs"
    docs_dir: Path = REPO_DIR / "docs"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def web3_enabled(self) -> bool:
        return bool(self.web3_rpc_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
