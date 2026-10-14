"""FastAPI dependencies: one instance of each service, built lazily from
settings so tests can point them at a temporary data dir and database."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import TradingAgent
from app.agent.executor import LiveExecutor, PaperExecutor, PerpExecutor
from app.agent.memory import Memory
from app.agent.state import AgentConfig, AgentState, Portfolio
from app.config import Settings, get_settings
from app.db.database import get_session
from app.db.models import ROLE_ADMIN, User
from app.news.collector import NewsCollector, get_news_collector
from app.onchain.wallet import WalletService
from app.services.auth import AuthService
from app.services.coingecko import CoinGeckoService, get_coingecko
from app.services.defillama import DefiLlamaService, get_defillama
from app.services.email import EmailService
from app.services.exchange import MarketDataService, get_market_service
from app.services.futures import BinanceFuturesService, get_futures
from app.services.oauth import build_oauth
from app.services.sentiment import SentimentService, get_sentiment
from app.services.siwe import SiweService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSession = Annotated[AsyncSession, Depends(get_session)]


def get_market() -> MarketDataService:
    return get_market_service()


_agent: TradingAgent | None = None
_auth: AuthService | None = None
_email: EmailService | None = None


def get_agent(settings: SettingsDep) -> TradingAgent:
    global _agent
    if _agent is None:
        initial = AgentState(
            mode="paper" if settings.paper_trading else "live",
            config=AgentConfig(symbols=settings.default_symbols, strategy=settings.default_strategy,
                               timeframe=settings.default_timeframe),
            portfolio=Portfolio(cash=settings.paper_starting_balance),
        )
        memory = Memory(settings.data_dir / "paper" / "state.json", initial)
        executor = PaperExecutor() if settings.paper_trading else LiveExecutor()
        # Perpetuals are paper-only, whatever PAPER_TRADING says.
        _agent = TradingAgent(get_market_service(), memory, executor, reviewer=_build_reviewer(settings),
                              futures=get_futures(), perp_executor=PerpExecutor())
    return _agent


def _build_reviewer(settings: Settings):
    if not settings.llm_enabled:
        return None
    from app.models.llm_client import get_llm

    return get_llm()


def get_news(settings: SettingsDep) -> NewsCollector:
    return get_news_collector()


def get_wallet(settings: SettingsDep) -> WalletService:
    return WalletService(settings.web3_rpc_url)


def get_auth(settings: SettingsDep) -> AuthService:
    global _auth
    if _auth is None:
        _auth = AuthService(settings.jwt_secret, settings.jwt_expire_minutes, settings.verification_token_hours,
                            settings.reset_token_minutes, settings.admin_emails)
    return _auth


def get_email(settings: SettingsDep) -> EmailService:
    global _email
    if _email is None:
        _email = EmailService(settings)
    return _email


_oauth = None
_siwe: SiweService | None = None


def get_oauth(settings: SettingsDep):
    """(Authlib client, [configured provider names])."""
    global _oauth
    if _oauth is None:
        _oauth = build_oauth(settings)
    return _oauth


def get_siwe(settings: SettingsDep) -> SiweService:
    global _siwe
    if _siwe is None:
        _siwe = SiweService(settings.siwe_host, settings.frontend_url, settings.chain_id)
    return _siwe


def reset_singletons() -> None:
    """For tests: forget the cached services so new settings apply."""
    global _agent, _auth, _email, _oauth, _siwe
    _agent = _auth = _email = _oauth = _siwe = None


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
    auth: Annotated[AuthService, Depends(get_auth)],
) -> User:
    user = await auth.user_from_token(session, credentials.credentials) if credentials else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida o caducada.",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo para administradores.")
    return user


AgentDep = Annotated[TradingAgent, Depends(get_agent)]
MarketDep = Annotated[MarketDataService, Depends(get_market)]
GeckoDep = Annotated[CoinGeckoService, Depends(get_coingecko)]
SentimentDep = Annotated[SentimentService, Depends(get_sentiment)]
DefiDep = Annotated[DefiLlamaService, Depends(get_defillama)]
FuturesDep = Annotated[BinanceFuturesService, Depends(get_futures)]
NewsDep = Annotated[NewsCollector, Depends(get_news)]
WalletDep = Annotated[WalletService, Depends(get_wallet)]
AuthDep = Annotated[AuthService, Depends(get_auth)]
EmailDep = Annotated[EmailService, Depends(get_email)]
OAuthDep = Annotated[tuple, Depends(get_oauth)]
SiweDep = Annotated[SiweService, Depends(get_siwe)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
