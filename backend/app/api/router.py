from fastapi import APIRouter, Depends

from app.api.deps import get_current_user

from .routes import admin, auth, bot, defi, futures, health, market, news, wallet

api_router = APIRouter()

# Public: health, market data and the news radar (the home page shows them to visitors).
api_router.include_router(health.router, tags=["health"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(futures.router, prefix="/futures", tags=["futures"])
api_router.include_router(defi.router, prefix="/defi", tags=["defi"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Signed-in users only.
signed_in = [Depends(get_current_user)]
api_router.include_router(bot.router, prefix="/bot", tags=["bot"], dependencies=signed_in)
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"], dependencies=signed_in)

# Admins only (checked inside each route).
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
