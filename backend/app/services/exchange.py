"""Market data from Binance's public REST API. No key needed.

Only reads: tickers, candles, last price. Orders never go through here.
"""

from __future__ import annotations

import asyncio
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


_service: MarketDataService | None = None


def get_market_service() -> MarketDataService:
    global _service
    if _service is None:
        from app.config import get_settings

        _service = MarketDataService(get_settings().binance_spot_url)
    return _service
