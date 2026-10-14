from fastapi import APIRouter

from .routes import admin, auth, auth_social, bot, defi, futures, health, market, news, token, wallet

api_router = APIRouter()

# Public, so visitors see what the app can do without an account: market data,
# futures, DeFi, the news radar, wallet lookups (read-only) and the bot as a
# spectator. Driving the bot needs an account (checked in routes/bot.py).
api_router.include_router(health.router, tags=["health"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(futures.router, prefix="/futures", tags=["futures"])
api_router.include_router(defi.router, prefix="/defi", tags=["defi"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(bot.router, prefix="/bot", tags=["bot"])
api_router.include_router(token.router, prefix="/token", tags=["token"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(auth_social.router, prefix="/auth", tags=["auth"])

# Admins only (checked inside each route).
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
