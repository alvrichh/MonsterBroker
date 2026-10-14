"""MonsterBroker API entry point: `uvicorn main:app --reload`."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.api.router import api_router
from app.config import get_settings
from app.db.database import dispose_db, init_db
from app.services.exchange import get_market_service
from app.utils.logger import get_logger, setup_logging

log = get_logger("monsterbroker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.logs_dir)
    log.info("%s v%s starting (%s, paper=%s, db=%s, email=%s)", settings.app_name, __version__,
             settings.environment, settings.paper_trading, settings.db_url.split("://")[0], settings.email_backend)
    await init_db()
    if settings.jwt_secret.startswith("change-me") or len(settings.jwt_secret.encode()) < 32:
        log.warning("JWT_SECRET is the example value or shorter than 32 bytes; set a real one before exposing this")

    scheduler = None
    if settings.news_auto_refresh:
        scheduler = _start_news_scheduler(settings.news_refresh_minutes)

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
    await get_market_service().close()
    await dispose_db()


def _start_news_scheduler(minutes: int):
    """Refresh the news radar in the background. Optional: the daily GitHub
    Action does the same job for the committed data."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError:
        log.warning("apscheduler not installed; NEWS_AUTO_REFRESH ignored")
        return None

    from app.api.deps import get_news_collector

    scheduler = AsyncIOScheduler()
    scheduler.add_job(get_news_collector().run, "interval", minutes=minutes, id="news-refresh")
    scheduler.start()
    log.info("news radar refresh every %s min", minutes)
    return scheduler


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Paper trading agent, crypto news radar and on-chain balances.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Only the OAuth dance uses the cookie session (the `state` parameter);
    # API auth stays stateless with bearer tokens.
    app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret, same_site="lax",
                       https_only=not settings.debug, max_age=600)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
