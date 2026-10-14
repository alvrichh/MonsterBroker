"""What the agent knows about itself: its configuration, its paper portfolio
and the decisions it took. All of it is plain pydantic so it round-trips
through JSON."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.strategies.base import Action


class Position(BaseModel):
    symbol: str
    amount: float = 0.0
    avg_price: float = 0.0


class Trade(BaseModel):
    id: str
    time: str
    symbol: str
    side: Action
    amount: float
    price: float
    value: float
    strategy: str
    reason: str = ""


class Decision(BaseModel):
    time: str
    symbol: str
    action: Action
    confidence: float
    reason: str
    strategy: str
    price: float
    executed: bool = False
    review: str | None = None  # what Claude said, when asked


class Portfolio(BaseModel):
    cash: float
    positions: dict[str, Position] = Field(default_factory=dict)
    trades: list[Trade] = Field(default_factory=list)

    def equity(self, prices: dict[str, float]) -> float:
        held = sum(p.amount * prices.get(p.symbol, p.avg_price) for p in self.positions.values())
        return self.cash + held


class AgentConfig(BaseModel):
    symbols: list[str]
    strategy: str = "sma_cross"
    timeframe: str = "1h"
    trade_fraction: float = Field(0.25, gt=0.0, le=1.0)  # share of cash per buy
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)  # 0 = act on every signal
    use_llm_review: bool = True


class AgentState(BaseModel):
    mode: str = "paper"
    config: AgentConfig
    portfolio: Portfolio
    decisions: list[Decision] = Field(default_factory=list)
    last_tick: str | None = None
    ticks: int = 0
    last_prices: dict[str, float] = Field(default_factory=dict)
