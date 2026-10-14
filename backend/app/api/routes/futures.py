from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import FuturesDep
from app.api.schemas.market import OhlcvOut
from app.services.futures import (
    PERIODS,
    TIMEFRAMES,
    FundingPoint,
    FuturesOverview,
    OpenInterestPoint,
    PerpRow,
    QuarterlyRow,
    RatiosOut,
)
from app.services.http import UpstreamError

router = APIRouter()

SymbolQuery = Query("BTCUSDT", pattern=r"^[A-Z0-9]{5,20}(_\d{6})?$", examples=["BTCUSDT"])
PeriodQuery = Query("1h", pattern="^(" + "|".join(PERIODS) + ")$")


def _upstream(error: UpstreamError) -> HTTPException:
    return HTTPException(502, str(error))


@router.get("/overview", response_model=FuturesOverview)
async def overview(futures: FuturesDep, symbol: str = SymbolQuery):
    """Mark/index price, funding, open interest and positioning for one perpetual."""
    try:
        return await futures.overview(symbol)
    except UpstreamError as error:
        raise _upstream(error) from error


@router.get("/top", response_model=list[PerpRow])
async def top(futures: FuturesDep, limit: int = Query(15, ge=5, le=50)):
    try:
        return await futures.top_perps(limit)
    except UpstreamError as error:
        raise _upstream(error) from error


@router.get("/funding", response_model=list[FundingPoint])
async def funding(futures: FuturesDep, symbol: str = SymbolQuery, limit: int = Query(30, ge=3, le=1000)):
    try:
        return await futures.funding(symbol, limit)
    except UpstreamError as error:
        raise _upstream(error) from error


@router.get("/open-interest", response_model=list[OpenInterestPoint])
async def open_interest(futures: FuturesDep, symbol: str = SymbolQuery, period: str = PeriodQuery,
                        limit: int = Query(168, ge=10, le=500)):
    try:
        return await futures.open_interest_history(symbol, period, limit)
    except UpstreamError as error:
        raise _upstream(error) from error


@router.get("/ratios", response_model=RatiosOut)
async def ratios(futures: FuturesDep, symbol: str = SymbolQuery, period: str = PeriodQuery,
                 limit: int = Query(48, ge=5, le=500)):
    out = RatiosOut()
    try:
        out.long_short = await futures.long_short(symbol, period, limit)
        out.top_traders = await futures.top_traders(symbol, period, limit)
        out.taker = await futures.taker(symbol, period, limit)
    except UpstreamError as error:
        raise _upstream(error) from error
    return out


@router.get("/ohlcv", response_model=OhlcvOut)
async def ohlcv(futures: FuturesDep, symbol: str = SymbolQuery, timeframe: str = "1h",
                limit: int = Query(200, ge=10, le=1000)):
    if timeframe not in TIMEFRAMES:
        raise HTTPException(422, f"timeframe must be one of {', '.join(TIMEFRAMES)}")
    try:
        candles = await futures.klines(symbol, timeframe, limit)
    except UpstreamError as error:
        raise _upstream(error) from error
    return OhlcvOut(symbol=symbol, timeframe=timeframe, candles=[asdict(c) for c in candles])


@router.get("/quarterly", response_model=list[QuarterlyRow])
async def quarterly(futures: FuturesDep):
    try:
        return await futures.quarterly()
    except UpstreamError as error:
        raise _upstream(error) from error
