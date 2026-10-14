from fastapi import APIRouter, HTTPException, Query

from app.api.deps import MarketDep, SettingsDep
from app.api.schemas.market import IndicatorsOut, OhlcvOut, TickerOut
from app.services.exchange import MarketDataError
from app.tools.indicators import snapshot

router = APIRouter()

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
    return OhlcvOut(symbol=symbol.upper(), timeframe=timeframe, candles=candles)


@router.get("/indicators", response_model=IndicatorsOut)
async def indicators(market: MarketDep, symbol: str = SymbolQuery, timeframe: str = "1h",
                     limit: int = Query(120, ge=30, le=500)):
    try:
        candles = await market.ohlcv(symbol.upper(), timeframe, limit)
    except MarketDataError as error:
        raise HTTPException(502, str(error)) from error
    closes = [c.close for c in candles]
    return IndicatorsOut(symbol=symbol.upper(), timeframe=timeframe, candles=len(closes), values=snapshot(closes))
