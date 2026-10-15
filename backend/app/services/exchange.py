"""Market data from Binance's public REST API. No key needed.

Only reads: tickers, candles, last price. Orders never go through here.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

from app.utils.helpers import to_exchange_symbol
from app.utils.logger import get_logger

log = get_logger(__name__)

BINANCE_API = "https://data-api.binance.vision/api/v3"  # see Settings.binance_spot_url
TIMEFRAMES = ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w")


class MarketDataError(Exception):
    """The exchange could not be read: network, rate limit or unknown symbol."""


@dataclass(slots=True)
class Ticker:
    symbol: str
    price: float
    change_24h: float  # percent
    high_24h: float
    low_24h: float
    volume_24h: float  # in quote currency


@dataclass(slots=True)
class Candle:
    time: int  # open time, ms since epoch
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataService:
    provider = "binance"

    def __init__(self, base_url: str = BINANCE_API, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, **params: object) -> object:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise MarketDataError(f"{path}: HTTP {error.response.status_code}") from error
        except httpx.HTTPError as error:
            raise MarketDataError(f"{path}: {error}") from error
        return response.json()

    async def ticker(self, symbol: str) -> Ticker:
        data = await self._get("/ticker/24hr", symbol=to_exchange_symbol(symbol))
        return Ticker(
            symbol=symbol,
            price=float(data["lastPrice"]),
            change_24h=float(data["priceChangePercent"]),
            high_24h=float(data["highPrice"]),
            low_24h=float(data["lowPrice"]),
            volume_24h=float(data["quoteVolume"]),
        )

    async def tickers(self, symbols: list[str]) -> list[Ticker]:
        results = await asyncio.gather(*(self.ticker(s) for s in symbols), return_exceptions=True)
        tickers: list[Ticker] = []
        for symbol, result in zip(symbols, results, strict=True):
            if isinstance(result, Ticker):
                tickers.append(result)
            else:
                log.warning("ticker %s failed: %s", symbol, result)
        return tickers

    async def ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]:
        if timeframe not in TIMEFRAMES:
            raise MarketDataError(f"unsupported timeframe {timeframe!r}; use one of {', '.join(TIMEFRAMES)}")
        rows = await self._get(
            "/klines", symbol=to_exchange_symbol(symbol), interval=timeframe, limit=min(max(limit, 1), 1000)
        )
        return [
            Candle(time=int(r[0]), open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]),
                   volume=float(r[5]))
            for r in rows
        ]

    async def price(self, symbol: str) -> float:
        data = await self._get("/ticker/price", symbol=to_exchange_symbol(symbol))
        return float(data["price"])


BLOCKED_MARKERS = ("HTTP 418", "HTTP 451", "HTTP 403")  # Binance refusing this host, not a bad request


class ResilientMarket:
    """Binance first; when it refuses this host (cloud addresses get a 418
    ban or a 451 geo-block, even on the data-api mirror) the fallback
    exchange answers for a while, then Binance gets retried. Same surface as
    MarketDataService."""

    def __init__(self, primary: MarketDataService, fallback: MarketDataService | None,
                 cooldown: float = 600.0) -> None:
        self.primary, self.fallback, self.cooldown = primary, fallback, cooldown
        self._blocked_until = 0.0

    @property
    def blocked(self) -> bool:
        return time.monotonic() < self._blocked_until

    @property
    def provider(self) -> str:
        return self.fallback.provider if (self.blocked and self.fallback) else self.primary.provider

    async def _call(self, name: str, *args, **kwargs):
        if not (self.blocked and self.fallback):
            try:
                return await getattr(self.primary, name)(*args, **kwargs)
            except MarketDataError as error:
                if self.fallback is None or not any(marker in str(error) for marker in BLOCKED_MARKERS):
                    raise
                self._blocked_until = time.monotonic() + self.cooldown
                log.warning("%s refused us (%s); using %s for %.0f s", self.primary.provider, error,
                            self.fallback.provider, self.cooldown)
        return await getattr(self.fallback, name)(*args, **kwargs)

    async def ticker(self, symbol: str) -> Ticker:
        return await self._call("ticker", symbol)

    async def tickers(self, symbols: list[str]) -> list[Ticker]:
        # One ticker at a time through the switch: the primary's own tickers()
        # swallows per-symbol errors, so a ban would never be seen.
        results = await asyncio.gather(*(self.ticker(s) for s in symbols), return_exceptions=True)
        tickers: list[Ticker] = []
        for symbol, result in zip(symbols, results, strict=True):
            if isinstance(result, Ticker):
                tickers.append(result)
            else:
                log.warning("ticker %s failed: %s", symbol, result)
        return tickers

    async def ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]:
        return await self._call("ohlcv", symbol, timeframe, limit)

    async def price(self, symbol: str) -> float:
        return await self._call("price", symbol)

    async def close(self) -> None:
        await self.primary.close()
        if self.fallback:
            await self.fallback.close()


_service: ResilientMarket | None = None


def get_market_service() -> ResilientMarket:
    global _service
    if _service is None:
        from app.config import get_settings
        from app.services.exchange_bybit import BybitSpotService

        settings = get_settings()
        _service = ResilientMarket(MarketDataService(settings.binance_spot_url), BybitSpotService(settings.bybit_url))
    return _service
