"""CoinGecko: global market metrics and the top coins by market cap.

Works without a key (IP rate limit). A free Demo key raises the limit to
100 calls/min; set COINGECKO_API_KEY.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import get_settings
from app.utils.cache import cache

from .http import JsonClient

COINGECKO_API = "https://api.coingecko.com/api/v3"
SPARKLINE_STEP = 4  # 168 hourly points → 42, plenty for a 7d sparkline


class GlobalMetrics(BaseModel):
    total_market_cap: float
    total_volume: float
    volume_scope: str = "coingecko"  # "top100" when summed from the coin list
    market_cap_change_24h: float  # percent
    btc_dominance: float
    eth_dominance: float
    active_cryptocurrencies: int
    markets: int
    updated_at: int


class CoinRow(BaseModel):
    id: str
    symbol: str
    name: str
    image: str = ""
    rank: int | None = None
    price: float | None = None
    market_cap: float | None = None
    volume_24h: float | None = None
    change_24h: float | None = None
    change_7d: float | None = None
    sparkline_7d: list[float] = Field(default_factory=list)


def parse_global(payload: dict) -> GlobalMetrics:
    d = payload["data"]
    share = d.get("market_cap_percentage", {})
    return GlobalMetrics(
        total_market_cap=d["total_market_cap"]["usd"],
        total_volume=d["total_volume"]["usd"],
        market_cap_change_24h=d.get("market_cap_change_percentage_24h_usd", 0.0),
        btc_dominance=share.get("btc", 0.0),
        eth_dominance=share.get("eth", 0.0),
        active_cryptocurrencies=d.get("active_cryptocurrencies", 0),
        markets=d.get("markets", 0),
        updated_at=d.get("updated_at", 0),
    )


def parse_coins(rows: list[dict]) -> list[CoinRow]:
    coins = []
    for row in rows:
        spark = (row.get("sparkline_in_7d") or {}).get("price") or []
        coins.append(CoinRow(
            id=row["id"],
            symbol=str(row.get("symbol", "")).upper(),
            name=row.get("name", row["id"]),
            image=row.get("image", ""),
            rank=row.get("market_cap_rank"),
            price=row.get("current_price"),
            market_cap=row.get("market_cap"),
            volume_24h=row.get("total_volume"),
            change_24h=row.get("price_change_percentage_24h_in_currency"),
            change_7d=row.get("price_change_percentage_7d_in_currency"),
            sparkline_7d=[float(v) for v in spark[::SPARKLINE_STEP]],
        ))
    return coins


MAX_VOLUME_RATIO = 0.5  # 24h volume above half the market cap is not a real market


def is_stablecoin(coin: CoinRow) -> bool:
    return coin.price is not None and 0.97 <= coin.price <= 1.03


def sane_volume(coins: list[CoinRow]) -> float:
    """Sum of 24h volumes, skipping glitches. CoinGecko has reported
    trillion-dollar daily volumes for BTC/ETH (10-30x reality); a coin whose
    volume exceeds half its cap is dropped, unless it is a stablecoin, which
    legitimately turns over most of its supply."""
    total = 0.0
    for coin in coins:
        volume, cap = coin.volume_24h or 0.0, coin.market_cap or 0.0
        if volume <= 0:
            continue
        if cap and volume / cap > MAX_VOLUME_RATIO and not is_stablecoin(coin):
            continue
        total += volume
    return total


class CoinGeckoService(JsonClient):
    def __init__(self, api_key: str = "") -> None:
        headers = {"x-cg-demo-api-key": api_key} if api_key else {}
        super().__init__(COINGECKO_API, headers=headers)

    async def global_metrics(self) -> GlobalMetrics:
        return await cache.get_or_fetch("gecko:global", 60, lambda: self._global())

    async def _global(self) -> GlobalMetrics:
        return parse_global(await self.get("/global"))

    async def top_coins(self, limit: int = 20) -> list[CoinRow]:
        # One call for the top 100 serves every page size (same credit cost).
        coins = await cache.get_or_fetch("gecko:top100", 90, lambda: self._top(100))
        return coins[:limit]

    async def _top(self, limit: int) -> list[CoinRow]:
        rows = await self.get(
            "/coins/markets", vs_currency="usd", order="market_cap_desc", per_page=limit, page=1,
            sparkline="true", price_change_percentage="24h,7d",
        )
        return parse_coins(rows)


_service: CoinGeckoService | None = None


def get_coingecko() -> CoinGeckoService:
    global _service
    if _service is None:
        _service = CoinGeckoService(get_settings().coingecko_api_key)
    return _service
