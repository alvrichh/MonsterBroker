import asyncio

import httpx
from fastapi import APIRouter

from app import __version__
from app.api.deps import SettingsDep

router = APIRouter()


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, object]:
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
        "paper_trading": settings.paper_trading,
        "llm_enabled": settings.llm_enabled,
        "web3_enabled": settings.web3_enabled,
    }


@router.get("/health/upstreams")
async def upstreams(settings: SettingsDep) -> dict[str, object]:
    """Which public data sources answer from where this API runs. Some
    (Binance) refuse cloud addresses with 418/451; this tells at a glance."""
    targets = {
        "binance_spot": f"{settings.binance_spot_url}/ping",
        "binance_futures": f"{settings.binance_futures_url}/fapi/v1/ping",
        "bybit": "https://api.bybit.com/v5/market/time",
        "coingecko": "https://api.coingecko.com/api/v3/ping",
        "alternative_me": "https://api.alternative.me/fng/?limit=1",
        "defillama": "https://api.llama.fi/v2/chains",
    }

    async def probe(client: httpx.AsyncClient, url: str) -> dict[str, object]:
        try:
            response = await client.get(url)
            return {"ok": response.status_code < 400, "status": response.status_code}
        except httpx.HTTPError as error:
            return {"ok": False, "error": type(error).__name__}

    async with httpx.AsyncClient(timeout=8.0) as client:
        results = await asyncio.gather(*(probe(client, url) for url in targets.values()))
    return {name: result for name, result in zip(targets, results, strict=True)}
