from pydantic import BaseModel, Field

from app.agent.state import AgentConfig, Decision, Portfolio, Trade


class StatusOut(BaseModel):
    mode: str
    config: AgentConfig
    portfolio: Portfolio
    equity: float
    last_prices: dict[str, float]
    last_tick: str | None
    ticks: int
    llm_review_available: bool
    recent_decisions: list[Decision]


class ConfigIn(BaseModel):
    symbols: list[str] | None = None
    strategy: str | None = None
    timeframe: str | None = None
    trade_fraction: float | None = Field(None, gt=0.0, le=1.0)
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    use_llm_review: bool | None = None


class StrategyOut(BaseModel):
    name: str
    description: str
    min_candles: int


class TradesOut(BaseModel):
    trades: list[Trade]
    total: int
