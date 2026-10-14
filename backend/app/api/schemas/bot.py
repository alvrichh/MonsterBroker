from pydantic import BaseModel, Field

from app.agent.state import AgentConfig, Benchmark, Decision, Market, Portfolio, Side, Trade


class PerpPositionOut(BaseModel):
    """A perp position valued at the last mark price. Not a subclass of
    PerpPosition: the computed fields would shadow its methods."""

    symbol: str
    side: Side
    size: float
    entry_price: float
    leverage: float
    margin: float
    liquidation_price: float
    opened_at: str
    funding_paid: float
    mark_price: float
    unrealized_pnl: float
    roe: float  # return on the margin, percent
    equity: float


class StatusOut(BaseModel):
    mode: str
    market: Market
    config: AgentConfig
    portfolio: Portfolio
    equity: float
    last_prices: dict[str, float]
    last_tick: str | None
    ticks: int
    llm_review_available: bool
    recent_decisions: list[Decision]
    perp_positions: dict[str, PerpPositionOut] = Field(default_factory=dict)
    benchmark: Benchmark | None = None


class ConfigIn(BaseModel):
    symbols: list[str] | None = None
    strategy: str | None = None
    timeframe: str | None = None
    trade_fraction: float | None = Field(None, gt=0.0, le=1.0)
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    use_llm_review: bool | None = None
    market: Market | None = None
    leverage: float | None = Field(None, ge=1.0, le=20.0)
    allow_shorts: bool | None = None


class StrategyOut(BaseModel):
    name: str
    description: str
    min_candles: int


class TradesOut(BaseModel):
    trades: list[Trade]
    total: int
