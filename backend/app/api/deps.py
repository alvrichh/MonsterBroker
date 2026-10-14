"""FastAPI dependencies: one instance of each service, built lazily from
settings so tests can point them at a temporary data dir."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.agent.agent import TradingAgent
from app.agent.executor import LiveExecutor, PaperExecutor
from app.agent.memory import Memory
from app.agent.state import AgentConfig, AgentState, Portfolio
from app.config import Settings, get_settings
from app.news.collector import NewsCollector, get_news_collector
from app.onchain.wallet import WalletService
from app.services.auth import AuthService, User
from app.services.exchange import MarketDataService, get_market_service

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_market() -> MarketDataService:
    return get_market_service()


_agent: TradingAgent | None = None
_auth: AuthService | None = None


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
        _agent = TradingAgent(get_market_service(), memory, executor, reviewer=_build_reviewer(settings))
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
        _auth = AuthService(settings.data_dir / "users.json", settings.jwt_secret, settings.jwt_expire_minutes)
    return _auth


def reset_singletons() -> None:
    """For tests: forget the cached services so new settings apply."""
    global _agent, _auth
    _agent = _auth = None


_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[AuthService, Depends(get_auth)],
) -> User:
    user = auth.user_from_token(credentials.credentials) if credentials else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida o caducada.",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


AgentDep = Annotated[TradingAgent, Depends(get_agent)]
MarketDep = Annotated[MarketDataService, Depends(get_market)]
NewsDep = Annotated[NewsCollector, Depends(get_news)]
WalletDep = Annotated[WalletService, Depends(get_wallet)]
AuthDep = Annotated[AuthService, Depends(get_auth)]
CurrentUser = Annotated[User, Depends(get_current_user)]
