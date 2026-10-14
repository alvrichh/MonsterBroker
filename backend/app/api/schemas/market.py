from pydantic import BaseModel


class TickerOut(BaseModel):
    symbol: str
    price: float
    change_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float


class CandleOut(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class OhlcvOut(BaseModel):
    symbol: str
    timeframe: str
    candles: list[CandleOut]


class IndicatorsOut(BaseModel):
    symbol: str
    timeframe: str
    candles: int
    values: dict[str, float | None]
