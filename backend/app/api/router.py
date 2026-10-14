from fastapi import APIRouter

from .routes import auth, bot, defi, futures, health, market, news, wallet

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(futures.router, prefix="/futures", tags=["futures"])
api_router.include_router(defi.router, prefix="/defi", tags=["defi"])
api_router.include_router(bot.router, prefix="/bot", tags=["bot"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
