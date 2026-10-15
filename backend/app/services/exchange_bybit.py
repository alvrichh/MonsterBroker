"""Bybit spot as a stand-in for Binance spot: the same surface as
MarketDataService, on Bybit's public v5 market endpoints. Used when Binance
refuses the host the API runs on (cloud addresses get 418/451)."""

from __future__ import annotations

from app.utils.helpers import to_exchange_symbol

from .exchange import TIMEFRAMES, Candle, MarketDataError, MarketDataService, Ticker
from .futures_bybit import BYBIT, KLINE_INTERVALS, parse_bybit_klines


def parse_bybit_spot_ticker(symbol: str, d: dict) -> Ticker:
    return Ticker(
        symbol=symbol,
        price=float(d["lastPrice"]),
        change_24h=float(d.get("price24hPcnt") or 0.0) * 100,  # Bybit sends a fraction
        high_24h=float(d["highPrice24h"]),
        low_24h=float(d["lowPrice24h"]),
        volume_24h=float(d.get("turnover24h") or 0.0),
    )


class BybitSpotService(MarketDataService):
    provider = "bybit"

    def __init__(self, base_url: str = BYBIT, timeout: float = 10.0) -> None:
        super().__init__(base_url, timeout)

    async def _result(self, path: str, **params: object) -> dict:
        payload = await self._get(path, category="spot", **params)
        if not isinstance(payload, dict) or payload.get("retCode") != 0:
            message = payload.get("retMsg") if isinstance(payload, dict) else "bad payload"
            raise MarketDataError(f"{path}: {message}")
        return payload["result"]

    async def ticker(self, symbol: str) -> Ticker:
        rows = (await self._result("/v5/market/tickers", symbol=to_exchange_symbol(symbol)))["list"]
        if not rows:
            raise MarketDataError(f"unknown symbol {symbol}")
        return parse_bybit_spot_ticker(symbol, rows[0])

    async def ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list[Candle]:
        if timeframe not in TIMEFRAMES:
            raise MarketDataError(f"unsupported timeframe {timeframe!r}; use one of {', '.join(TIMEFRAMES)}")
        result = await self._result("/v5/market/kline", symbol=to_exchange_symbol(symbol),
                                    interval=KLINE_INTERVALS[timeframe], limit=min(max(limit, 1), 1000))
        return parse_bybit_klines(result["list"])  # Bybit answers newest first; this sorts

    async def price(self, symbol: str) -> float:
        return (await self.ticker(symbol)).price
