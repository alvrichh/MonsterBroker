from pydantic import BaseModel, Field

from app.services.coingecko import GlobalMetrics
from app.services.sentiment import FearGreed


class OverviewOut(BaseModel):
    """Global metrics and sentiment. Either half may be missing when its
    upstream is down; the other still renders."""

    metrics: GlobalMetrics | None = None
    fear_greed: FearGreed | None = None
    errors: list[str] = Field(default_factory=list)


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
