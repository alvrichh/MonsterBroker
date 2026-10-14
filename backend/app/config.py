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

    # Public data APIs. All work without a key; a free key raises the limits.
    coingecko_api_key: str = ""  # Demo plan: 100 calls/min
    coinmarketcap_api_key: str = ""  # Basic plan: 15k credits/month (not wired yet)
    etherscan_api_key: str = ""  # Free: 3 calls/s, 50+ chains (not wired yet)

    # Web3: any JSON-RPC endpoint. Empty disables the wallet routes.
    web3_rpc_url: str = ""

    # News radar
    news_auto_refresh: bool = False
    news_refresh_minutes: int = 60

    # Auth. ADMIN_EMAILS: whoever registers with one of these becomes admin.
    # JWT_SECRET must be at least 32 random bytes (HS256); the default only works for local play.
    jwt_secret: str = "change-me-generate-32-random-bytes-for-prod"
    jwt_expire_minutes: int = 60 * 24
    verification_token_hours: int = 24
    reset_token_minutes: int = 30
    require_email_verification: bool = True
    admin_emails: list[str] = []
    frontend_url: str = "http://localhost:5173"  # where the email links point

    # Database: empty = SQLite under data/. Postgres: postgresql+asyncpg://user:pass@host/db
    database_url: str = ""

    # Email: console | resend | smtp
    email_backend: str = "console"
    email_from: str = "MonsterBroker <onboarding@resend.dev>"
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True

    data_dir: Path = BACKEND_DIR / "data"
    logs_dir: Path = BACKEND_DIR / "logs"
    docs_dir: Path = REPO_DIR / "docs"

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite+aiosqlite:///{(self.data_dir / 'monsterbroker.db').as_posix()}"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def web3_enabled(self) -> bool:
        return bool(self.web3_rpc_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
