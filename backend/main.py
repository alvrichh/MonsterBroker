"""MonsterBroker API entry point: `uvicorn main:app --reload`."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.config import get_settings
from app.services.exchange import get_market_service
from app.utils.logger import get_logger, setup_logging

log = get_logger("monsterbroker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.logs_dir)
    log.info("%s v%s starting (%s, paper=%s)", settings.app_name, __version__, settings.environment,
             settings.paper_trading)

    scheduler = None
    if settings.news_auto_refresh:
        scheduler = _start_news_scheduler(settings.news_refresh_minutes)

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
    await get_market_service().close()


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
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
