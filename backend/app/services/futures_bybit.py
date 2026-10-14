"""Bybit USDT perpetuals as a stand-in for Binance Futures: the same
service surface, built on Bybit's public v5 market endpoints. Used when
Binance refuses the host the API runs on (cloud addresses get 418/451).
Bybit publishes no top-trader or taker ratios and no quarterly list, so
those come back empty and the UI shows a dash."""

from __future__ import annotations

from typing import Any

from app.services.exchange import Candle
from app.utils.cache import cache
from app.utils.helpers import utc_now

from .futures import (
    FUNDING_PERIODS_PER_YEAR,
    BinanceFuturesService,
    FundingPoint,
    OpenInterestPoint,
    PerpTicker,
    PremiumIndex,
    QuarterlyRow,
    RatioPoint,
    TakerPoint,
    is_usdt_perp,
)
from .http import UpstreamError

BYBIT = "https://api.bybit.com"
# Our periods/timeframes in Bybit's vocabulary (nearest when there is no match).
OI_PERIODS = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "2h": "1h", "4h": "4h", "6h": "4h",
              "12h": "4h", "1d": "1d"}
KLINE_INTERVALS = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240", "1d": "D", "1w": "W"}


def _ms_now() -> int:
    return int(utc_now().timestamp() * 1000)


def parse_bybit_premium(d: dict, now_ms: int | None = None) -> PremiumIndex:
    rate = float(d.get("fundingRate") or 0.0)
    return PremiumIndex(
        symbol=d["symbol"], mark_price=float(d["markPrice"]), index_price=float(d["indexPrice"]),
        funding_rate=rate, funding_annualized=rate * FUNDING_PERIODS_PER_YEAR,
        next_funding_time=int(d.get("nextFundingTime") or 0), time=now_ms or _ms_now(),
    )


def parse_bybit_ticker(d: dict) -> PerpTicker:
    return PerpTicker(
        symbol=d["symbol"], last_price=float(d["lastPrice"]), change_24h=float(d.get("price24hPcnt") or 0.0) * 100,
        high_24h=float(d["highPrice24h"]), low_24h=float(d["lowPrice24h"]), volume_24h=float(d.get("turnover24h") or 0),
    )


def parse_bybit_funding(rows: list[dict]) -> list[FundingPoint]:
    points = [FundingPoint(time=int(r["fundingRateTimestamp"]), rate=float(r["fundingRate"])) for r in rows]
    return sorted(points, key=lambda p: p.time)  # Bybit answers newest first


def parse_bybit_oi(rows: list[dict], mark_price: float) -> list[OpenInterestPoint]:
    points = [
        OpenInterestPoint(time=int(r["timestamp"]), contracts=float(r["openInterest"]),
                          value=float(r["openInterest"]) * mark_price)
        for r in rows
    ]
    return sorted(points, key=lambda p: p.time)


def parse_bybit_ratio(rows: list[dict]) -> list[RatioPoint]:
    points = []
    for r in rows:
        long, short = float(r["buyRatio"]), float(r["sellRatio"])
        points.append(RatioPoint(time=int(r["timestamp"]), long=long, short=short,
                                 ratio=round(long / short, 4) if short else 0.0))
    return sorted(points, key=lambda p: p.time)


def parse_bybit_klines(rows: list[list]) -> list[Candle]:
    candles = [
        Candle(time=int(r[0]), open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]),
               volume=float(r[5]))
        for r in rows
    ]
    return sorted(candles, key=lambda c: c.time)


class BybitFuturesService(BinanceFuturesService):
    provider = "bybit"

    def __init__(self, base_url: str = BYBIT) -> None:
        super().__init__(base_url)

    async def _result(self, path: str, **params: Any) -> Any:
        payload = await self.get(path, category="linear", **params)
        if payload.get("retCode") != 0:
            raise UpstreamError(f"{self.base_url}{path}: {payload.get('retMsg') or payload.get('retCode')}")
        return payload["result"]

    # ------------------------------------------------------------ primitives

    async def _fetch_raw_tickers(self) -> list[dict]:
        """One call carries last/mark/index prices, funding and open interest for every contract."""
        return await cache.get_or_fetch(self._key("raw"), 15, self._download_tickers)

    async def _download_tickers(self) -> list[dict]:
        return (await self._result("/v5/market/tickers"))["list"]

    async def _premium(self, symbol: str) -> PremiumIndex:
        rows = (await self._result("/v5/market/tickers", symbol=symbol))["list"]
        if not rows:
            raise UpstreamError(f"{self.base_url}: unknown symbol {symbol}")
        return parse_bybit_premium(rows[0])

    async def _premium_all(self) -> dict[str, PremiumIndex]:
        now = _ms_now()
        return {r["symbol"]: parse_bybit_premium(r, now) for r in await self._fetch_raw_tickers()
                if is_usdt_perp(r["symbol"]) and r.get("markPrice")}

    async def _funding(self, symbol: str, limit: int) -> list[FundingPoint]:
        result = await self._result("/v5/market/funding/history", symbol=symbol, limit=min(limit, 200))
        return parse_bybit_funding(result["list"])

    async def _open_interest(self, symbol: str) -> float:
        rows = (await self._result("/v5/market/tickers", symbol=symbol))["list"]
        return float(rows[0]["openInterest"]) if rows else 0.0

    async def _oi_history(self, symbol: str, period: str, limit: int) -> list[OpenInterestPoint]:
        premium = await self.premium(symbol)
        result = await self._result("/v5/market/open-interest", symbol=symbol,
                                    intervalTime=OI_PERIODS.get(period, "1h"), limit=min(limit, 200))
        return parse_bybit_oi(result["list"], premium.mark_price)

    async def long_short(self, symbol: str, period: str = "1h", limit: int = 48) -> list[RatioPoint]:
        return await cache.get_or_fetch(self._key("ls", symbol, period, limit), 300,
                                        lambda: self._long_short(symbol, period, limit))

    async def _long_short(self, symbol: str, period: str, limit: int) -> list[RatioPoint]:
        result = await self._result("/v5/market/account-ratio", symbol=symbol,
                                    period=OI_PERIODS.get(period, "1h"), limit=min(limit, 500))
        return parse_bybit_ratio(result["list"])

    async def top_traders(self, symbol: str, period: str = "1h", limit: int = 48) -> list[RatioPoint]:
        return []  # not published by Bybit

    async def taker(self, symbol: str, period: str = "1h", limit: int = 48) -> list[TakerPoint]:
        return []  # not published by Bybit

    async def _tickers(self) -> dict[str, PerpTicker]:
        return {r["symbol"]: parse_bybit_ticker(r) for r in await self._fetch_raw_tickers()
                if is_usdt_perp(r["symbol"])}

    async def klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> list[Candle]:
        result = await self._result("/v5/market/kline", symbol=symbol,
                                    interval=KLINE_INTERVALS.get(interval, "60"), limit=min(max(limit, 1), 1000))
        return parse_bybit_klines(result["list"])

    async def _symbols(self) -> list[dict]:
        return []

    async def quarterly(self) -> list[QuarterlyRow]:
        return []  # dated contracts are not part of Bybit's linear USDT list we use
