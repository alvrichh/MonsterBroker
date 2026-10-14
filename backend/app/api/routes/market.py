import asyncio
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import GeckoDep, MarketDep, SentimentDep, SettingsDep
from app.api.schemas.market import IndicatorsOut, OhlcvOut, OverviewOut, TickerOut
from app.services.coingecko import CoinRow, sane_volume
from app.services.exchange import MarketDataError
from app.services.http import UpstreamError
from app.tools.indicators import snapshot

router = APIRouter()


@router.get("/overview", response_model=OverviewOut)
async def overview(gecko: GeckoDep, sentiment: SentimentDep):
    """Global market cap, dominance and the Fear & Greed index."""
    metrics, fng, coins = await asyncio.gather(
        gecko.global_metrics(), sentiment.fear_greed(), gecko.top_coins(100), return_exceptions=True,
    )
    out = OverviewOut()
    if isinstance(metrics, BaseException):
        out.errors.append(f"coingecko: {metrics}")
    else:
        # /global's total_volume is unreliable (it has returned 10^14); the
        # sum over the top 100 coins, glitches excluded, is what people mean
        # by "24h volume".
        if not isinstance(coins, BaseException) and coins:
            metrics = metrics.model_copy(update={"total_volume": sane_volume(coins), "volume_scope": "top100"})
        out.metrics = metrics
    if isinstance(fng, BaseException):
        out.errors.append(f"fear&greed: {fng}")
    else:
        out.fear_greed = fng
    return out


@router.get("/top", response_model=list[CoinRow])
async def top(gecko: GeckoDep, limit: int = Query(20, ge=5, le=100)):
    """Top coins by market cap, with 7-day sparklines (CoinGecko)."""
    try:
        return await gecko.top_coins(limit)
    except UpstreamError as error:
        raise HTTPException(502, str(error)) from error

SymbolQuery = Query(pattern=r"^[A-Za-z0-9]+/[A-Za-z0-9]+$", examples=["BTC/USDT"])


def _split_symbols(raw: str | None, default: list[str]) -> list[str]:
    if not raw:
        return default
    return [s.strip().upper() for s in raw.split(",") if s.strip()][:20]


@router.get("/tickers", response_model=list[TickerOut])
async def tickers(market: MarketDep, settings: SettingsDep,
                  symbols: str | None = Query(None, description="Comma-separated, e.g. BTC/USDT,ETH/USDT")):
    wanted = _split_symbols(symbols, settings.default_symbols)
    result = await market.tickers(wanted)
    if not result:
        raise HTTPException(502, "El exchange no respondió para ninguno de los símbolos.")
    return result


@router.get("/ohlcv", response_model=OhlcvOut)
async def ohlcv(market: MarketDep, symbol: str = SymbolQuery, timeframe: str = "1h",
                limit: int = Query(100, ge=10, le=500)):
    try:
        candles = await market.ohlcv(symbol.upper(), timeframe, limit)
    except MarketDataError as error:
        raise HTTPException(502, str(error)) from error
    # Candle is a dataclass; pydantic wants dicts (or CandleOut) inside the model.
    return OhlcvOut(symbol=symbol.upper(), timeframe=timeframe, candles=[asdict(c) for c in candles])


@router.get("/indicators", response_model=IndicatorsOut)
async def indicators(market: MarketDep, symbol: str = SymbolQuery, timeframe: str = "1h",
                     limit: int = Query(120, ge=30, le=500)):
    try:
        candles = await market.ohlcv(symbol.upper(), timeframe, limit)
    except MarketDataError as error:
        raise HTTPException(502, str(error)) from error
    closes = [c.close for c in candles]
    return IndicatorsOut(symbol=symbol.upper(), timeframe=timeframe, candles=len(closes), values=snapshot(closes))
