"""Binance USDT-M futures, public endpoints only (no key): mark and index
price, funding, open interest, long/short positioning, 24h tickers, candles
and the quarterly contracts with their basis. Read-only; cached briefly."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.services.exchange import Candle
from app.utils.cache import cache
from app.utils.helpers import utc_now

from .http import JsonClient

FAPI = "https://fapi.binance.com"
PERIODS = ("5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d")
TIMEFRAMES = ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w")
QUARTER_TYPES = ("CURRENT_QUARTER", "NEXT_QUARTER")
FUNDING_PERIODS_PER_YEAR = 3 * 365  # funding settles every 8 hours


class PremiumIndex(BaseModel):
    symbol: str
    mark_price: float
    index_price: float
    funding_rate: float  # per 8h period, as a fraction (0.0001 = 0.01%)
    funding_annualized: float  # fraction
    next_funding_time: int  # ms
    time: int


class FundingPoint(BaseModel):
    time: int
    rate: float
    mark_price: float | None = None


class OpenInterestPoint(BaseModel):
    time: int
    contracts: float
    value: float  # USDT


class RatioPoint(BaseModel):
    time: int
    long: float  # share of accounts/positions, 0-1
    short: float
    ratio: float


class TakerPoint(BaseModel):
    time: int
    buy: float
    sell: float
    ratio: float


class PerpTicker(BaseModel):
    symbol: str
    last_price: float
    change_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float  # quote (USDT)


class PerpRow(BaseModel):
    symbol: str
    base: str
    last_price: float
    change_24h: float
    volume_24h: float
    mark_price: float | None = None
    index_price: float | None = None
    funding_rate: float | None = None
    funding_annualized: float | None = None
    next_funding_time: int | None = None
    open_interest: float | None = None  # contracts (base units)
    open_interest_value: float | None = None  # USDT


class QuarterlyRow(BaseModel):
    symbol: str
    pair: str
    contract_type: str
    delivery_date: str
    days_to_delivery: float
    mark_price: float
    index_price: float
    basis: float  # percent, mark vs index
    annualized_basis: float  # percent


class FuturesOverview(BaseModel):
    index: PremiumIndex
    ticker: PerpTicker | None = None
    open_interest: float | None = None
    open_interest_value: float | None = None
    long_short: RatioPoint | None = None
    top_traders: RatioPoint | None = None
    taker: TakerPoint | None = None
    errors: list[str] = Field(default_factory=list)


class RatiosOut(BaseModel):
    long_short: list[RatioPoint] = Field(default_factory=list)
    top_traders: list[RatioPoint] = Field(default_factory=list)
    taker: list[TakerPoint] = Field(default_factory=list)


# ------------------------------------------------------------------ parsing


def is_usdt_perp(symbol: str) -> bool:
    return symbol.endswith("USDT") and "_" not in symbol


def parse_premium(d: dict) -> PremiumIndex:
    rate = float(d.get("lastFundingRate") or 0.0)
    return PremiumIndex(
        symbol=d["symbol"], mark_price=float(d["markPrice"]), index_price=float(d["indexPrice"]),
        funding_rate=rate, funding_annualized=rate * FUNDING_PERIODS_PER_YEAR,
        next_funding_time=int(d.get("nextFundingTime") or 0), time=int(d.get("time") or 0),
    )


def parse_funding(rows: list[dict]) -> list[FundingPoint]:
    return [
        FundingPoint(time=int(r["fundingTime"]), rate=float(r["fundingRate"]),
                     mark_price=float(r["markPrice"]) if r.get("markPrice") else None)
        for r in rows
    ]


def parse_oi_history(rows: list[dict]) -> list[OpenInterestPoint]:
    return [
        OpenInterestPoint(time=int(r["timestamp"]), contracts=float(r["sumOpenInterest"]),
                          value=float(r["sumOpenInterestValue"]))
        for r in rows
    ]


def parse_ratios(rows: list[dict]) -> list[RatioPoint]:
    return [
        RatioPoint(time=int(r["timestamp"]), long=float(r["longAccount"]), short=float(r["shortAccount"]),
                   ratio=float(r["longShortRatio"]))
        for r in rows
    ]


def parse_taker(rows: list[dict]) -> list[TakerPoint]:
    return [
        TakerPoint(time=int(r["timestamp"]), buy=float(r["buyVol"]), sell=float(r["sellVol"]),
                   ratio=float(r["buySellRatio"]))
        for r in rows
    ]


def parse_ticker(d: dict) -> PerpTicker:
    return PerpTicker(
        symbol=d["symbol"], last_price=float(d["lastPrice"]), change_24h=float(d["priceChangePercent"]),
        high_24h=float(d["highPrice"]), low_24h=float(d["lowPrice"]), volume_24h=float(d["quoteVolume"]),
    )


def parse_klines(rows: list[list]) -> list[Candle]:
    return [
        Candle(time=int(r[0]), open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]),
               volume=float(r[5]))
        for r in rows
    ]


def parse_quarterly(symbols: list[dict], premiums: dict[str, PremiumIndex], now_ms: int) -> list[QuarterlyRow]:
    rows = []
    for s in symbols:
        premium = premiums.get(s["symbol"])
        if s.get("contractType") not in QUARTER_TYPES or s.get("status") != "TRADING" or not premium:
            continue
        delivery_ms = int(s["deliveryDate"])
        days = max((delivery_ms - now_ms) / 86_400_000, 0.01)
        basis = (premium.mark_price / premium.index_price - 1) * 100 if premium.index_price else 0.0
        rows.append(QuarterlyRow(
            symbol=s["symbol"], pair=s["pair"], contract_type=s["contractType"],
            delivery_date=datetime.fromtimestamp(delivery_ms / 1000, UTC).date().isoformat(),
            days_to_delivery=round(days, 1), mark_price=premium.mark_price, index_price=premium.index_price,
            basis=basis, annualized_basis=basis * 365 / days,
        ))
    rows.sort(key=lambda r: (r.pair, r.delivery_date))
    return rows


# ------------------------------------------------------------------ service


class BinanceFuturesService(JsonClient):
    def __init__(self, base_url: str = FAPI) -> None:
        super().__init__(base_url, timeout=10.0)

    async def premium(self, symbol: str) -> PremiumIndex:
        return await cache.get_or_fetch(f"fut:premium:{symbol}", 10,
                                        lambda: self._premium(symbol))

    async def _premium(self, symbol: str) -> PremiumIndex:
        return parse_premium(await self.get("/fapi/v1/premiumIndex", symbol=symbol))

    async def premium_all(self) -> dict[str, PremiumIndex]:
        return await cache.get_or_fetch("fut:premium:all", 15, self._premium_all)

    async def _premium_all(self) -> dict[str, PremiumIndex]:
        rows = await self.get("/fapi/v1/premiumIndex")
        return {r["symbol"]: parse_premium(r) for r in rows if r.get("markPrice")}

    async def funding(self, symbol: str, limit: int = 30) -> list[FundingPoint]:
        return await cache.get_or_fetch(f"fut:funding:{symbol}:{limit}", 300,
                                        lambda: self._funding(symbol, limit))

    async def _funding(self, symbol: str, limit: int) -> list[FundingPoint]:
        return parse_funding(await self.get("/fapi/v1/fundingRate", symbol=symbol, limit=limit))

    async def open_interest(self, symbol: str) -> float:
        return await cache.get_or_fetch(f"fut:oi:{symbol}", 30, lambda: self._open_interest(symbol))

    async def _open_interest(self, symbol: str) -> float:
        return float((await self.get("/fapi/v1/openInterest", symbol=symbol))["openInterest"])

    async def open_interest_history(self, symbol: str, period: str = "1h", limit: int = 168) -> list[OpenInterestPoint]:
        return await cache.get_or_fetch(f"fut:oih:{symbol}:{period}:{limit}", 300,
                                        lambda: self._oi_history(symbol, period, limit))

    async def _oi_history(self, symbol: str, period: str, limit: int) -> list[OpenInterestPoint]:
        return parse_oi_history(await self.get("/futures/data/openInterestHist", symbol=symbol, period=period,
                                               limit=limit))

    async def _ratio(self, path: str, symbol: str, period: str, limit: int, parser) -> list:
        return parser(await self.get(path, symbol=symbol, period=period, limit=limit))

    async def long_short(self, symbol: str, period: str = "1h", limit: int = 48) -> list[RatioPoint]:
        return await cache.get_or_fetch(
            f"fut:ls:{symbol}:{period}:{limit}", 300,
            lambda: self._ratio("/futures/data/globalLongShortAccountRatio", symbol, period, limit, parse_ratios),
        )

    async def top_traders(self, symbol: str, period: str = "1h", limit: int = 48) -> list[RatioPoint]:
        return await cache.get_or_fetch(
            f"fut:top:{symbol}:{period}:{limit}", 300,
            lambda: self._ratio("/futures/data/topLongShortPositionRatio", symbol, period, limit, parse_ratios),
        )

    async def taker(self, symbol: str, period: str = "1h", limit: int = 48) -> list[TakerPoint]:
        return await cache.get_or_fetch(
            f"fut:taker:{symbol}:{period}:{limit}", 300,
            lambda: self._ratio("/futures/data/takerlongshortRatio", symbol, period, limit, parse_taker),
        )

    async def tickers(self) -> dict[str, PerpTicker]:
        return await cache.get_or_fetch("fut:tickers", 30, self._tickers)

    async def _tickers(self) -> dict[str, PerpTicker]:
        rows = await self.get("/fapi/v1/ticker/24hr")
        return {r["symbol"]: parse_ticker(r) for r in rows if is_usdt_perp(r["symbol"])}

    async def klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> list[Candle]:
        return parse_klines(await self.get("/fapi/v1/klines", symbol=symbol, interval=interval,
                                           limit=min(max(limit, 1), 1500)))

    async def symbols(self) -> list[dict]:
        return await cache.get_or_fetch("fut:symbols", 3600, self._symbols)

    async def _symbols(self) -> list[dict]:
        return (await self.get("/fapi/v1/exchangeInfo"))["symbols"]

    # ------------------------------------------------------------ composed

    async def overview(self, symbol: str) -> FuturesOverview:
        premium, oi, ls, top, taker, tickers = await asyncio.gather(
            self.premium(symbol), self.open_interest(symbol), self.long_short(symbol, "1h", 1),
            self.top_traders(symbol, "1h", 1), self.taker(symbol, "1h", 1), self.tickers(),
            return_exceptions=True,
        )
        if isinstance(premium, BaseException):
            raise premium
        out = FuturesOverview(index=premium)
        for name, value in (("open_interest", oi), ("long_short", ls), ("top_traders", top), ("taker", taker),
                            ("tickers", tickers)):
            if isinstance(value, BaseException):
                out.errors.append(f"{name}: {value}")
        if not isinstance(oi, BaseException):
            out.open_interest = oi
            out.open_interest_value = oi * premium.mark_price
        if not isinstance(ls, BaseException) and ls:
            out.long_short = ls[-1]
        if not isinstance(top, BaseException) and top:
            out.top_traders = top[-1]
        if not isinstance(taker, BaseException) and taker:
            out.taker = taker[-1]
        if not isinstance(tickers, BaseException):
            out.ticker = tickers.get(symbol)
        return out

    async def top_perps(self, limit: int = 15) -> list[PerpRow]:
        tickers, premiums = await asyncio.gather(self.tickers(), self.premium_all())
        top = sorted(tickers.values(), key=lambda t: t.volume_24h, reverse=True)[:limit]
        ois = await asyncio.gather(*(self.open_interest(t.symbol) for t in top), return_exceptions=True)
        rows = []
        for ticker, oi in zip(top, ois, strict=True):
            premium = premiums.get(ticker.symbol)
            contracts = None if isinstance(oi, BaseException) else oi
            rows.append(PerpRow(
                symbol=ticker.symbol, base=ticker.symbol[:-4], last_price=ticker.last_price,
                change_24h=ticker.change_24h, volume_24h=ticker.volume_24h,
                mark_price=premium.mark_price if premium else None,
                index_price=premium.index_price if premium else None,
                funding_rate=premium.funding_rate if premium else None,
                funding_annualized=premium.funding_annualized if premium else None,
                next_funding_time=premium.next_funding_time if premium else None,
                open_interest=contracts,
                open_interest_value=contracts * premium.mark_price if contracts is not None and premium else None,
            ))
        return rows

    async def quarterly(self) -> list[QuarterlyRow]:
        symbols = [s for s in await self.symbols()
                   if s.get("contractType") in QUARTER_TYPES and s.get("status") == "TRADING"]
        premiums = await asyncio.gather(*(self.premium(s["symbol"]) for s in symbols), return_exceptions=True)
        by_symbol = {p.symbol: p for p in premiums if isinstance(p, PremiumIndex)}
        return parse_quarterly(symbols, by_symbol, int(utc_now().timestamp() * 1000))


_service: BinanceFuturesService | None = None


def get_futures() -> BinanceFuturesService:
    global _service
    if _service is None:
        from app.config import get_settings

        _service = BinanceFuturesService(get_settings().binance_futures_url)
    return _service
