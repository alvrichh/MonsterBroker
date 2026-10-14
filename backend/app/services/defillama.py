"""DefiLlama: total value locked by chain and by protocol, plus the history
of the total. Free, keyless (yields are a paid tier, not used)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from app.utils.cache import cache

from .http import JsonClient

LLAMA_API = "https://api.llama.fi"
# Exchanges report reserves as "TVL"; that is not DeFi, so they're left out.
EXCLUDED_CATEGORIES = {"CEX"}


class ChainTvl(BaseModel):
    name: str
    tvl: float
    symbol: str | None = None
    gecko_id: str | None = None


class ProtocolTvl(BaseModel):
    name: str
    slug: str
    logo: str = ""
    category: str = ""
    chain: str = ""
    tvl: float
    change_1d: float | None = None
    change_7d: float | None = None
    url: str = ""


class TvlPoint(BaseModel):
    date: str
    tvl: float


def parse_chains(rows: list[dict], limit: int) -> list[ChainTvl]:
    chains = [
        ChainTvl(name=r["name"], tvl=float(r.get("tvl") or 0), symbol=r.get("tokenSymbol"), gecko_id=r.get("gecko_id"))
        for r in rows
        if r.get("tvl")
    ]
    chains.sort(key=lambda c: c.tvl, reverse=True)
    return chains[:limit]


def parse_protocols(rows: list[dict], limit: int) -> list[ProtocolTvl]:
    protocols = [
        ProtocolTvl(
            name=r["name"], slug=r.get("slug", r["name"].lower()), logo=r.get("logo") or "",
            category=r.get("category") or "", chain=r.get("chain") or "", tvl=float(r.get("tvl") or 0),
            change_1d=r.get("change_1d"), change_7d=r.get("change_7d"), url=r.get("url") or "",
        )
        for r in rows
        if r.get("tvl") and r.get("category") not in EXCLUDED_CATEGORIES
    ]
    protocols.sort(key=lambda p: p.tvl, reverse=True)
    return protocols[:limit]


def parse_history(rows: list[dict], days: int) -> list[TvlPoint]:
    return [
        TvlPoint(date=datetime.fromtimestamp(int(r["date"]), UTC).date().isoformat(), tvl=float(r["tvl"]))
        for r in rows[-days:]
    ]


class DefiLlamaService(JsonClient):
    def __init__(self) -> None:
        super().__init__(LLAMA_API, timeout=20.0)

    async def chains(self, limit: int = 12) -> list[ChainTvl]:
        return await cache.get_or_fetch(f"llama:chains:{limit}", 600,
                                        lambda: self._chains(limit))

    async def _chains(self, limit: int) -> list[ChainTvl]:
        return parse_chains(await self.get("/v2/chains"), limit)

    async def protocols(self, limit: int = 15) -> list[ProtocolTvl]:
        return await cache.get_or_fetch(f"llama:protocols:{limit}", 600,
                                        lambda: self._protocols(limit))

    async def _protocols(self, limit: int) -> list[ProtocolTvl]:
        return parse_protocols(await self.get("/protocols"), limit)

    async def tvl_history(self, days: int = 180) -> list[TvlPoint]:
        return await cache.get_or_fetch(f"llama:history:{days}", 3600,
                                        lambda: self._history(days))

    async def _history(self, days: int) -> list[TvlPoint]:
        return parse_history(await self.get("/v2/historicalChainTvl"), days)


_service: DefiLlamaService | None = None


def get_defillama() -> DefiLlamaService:
    global _service
    if _service is None:
        _service = DefiLlamaService()
    return _service
