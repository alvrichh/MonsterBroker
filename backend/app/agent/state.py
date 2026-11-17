"""What the agent knows about itself: its configuration, its paper portfolio
and the decisions it took. All of it is plain pydantic so it round-trips
through JSON."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.strategies.base import Action


class Market(StrEnum):
    SPOT = "spot"
    PERP = "perp"  # USDT-M perpetual futures, long and short


class Side(StrEnum):
    LONG = "long"
    SHORT = "short"


class Position(BaseModel):
    """A spot holding."""

    symbol: str
    amount: float = 0.0
    avg_price: float = 0.0
    stop: float | None = None
    target: float | None = None
    entry_bar: int | None = None  # open time (ms) of the candle it filled on


class PerpPosition(BaseModel):
    """An isolated-margin perpetual position. The margin is the cash locked
    when it opened; funding moves it; the position is gone once the price
    trades through liquidation_price."""

    symbol: str
    side: Side
    size: float  # contracts, in base units
    entry_price: float
    leverage: float
    margin: float
    liquidation_price: float
    opened_at: str
    funding_paid: float = 0.0  # cumulative; positive = paid, negative = received
    stop: float | None = None
    target: float | None = None
    entry_bar: int | None = None  # open time (ms) of the candle it filled on

    def unrealized_pnl(self, price: float) -> float:
        direction = 1.0 if self.side == Side.LONG else -1.0
        return (price - self.entry_price) * self.size * direction

    def equity(self, price: float) -> float:
        return max(0.0, self.margin + self.unrealized_pnl(price))


class Trade(BaseModel):
    id: str
    time: str
    symbol: str
    side: Action  # order direction: buy or sell
    amount: float
    price: float
    value: float
    strategy: str
    reason: str = ""
    market: Market = Market.SPOT
    action: str = "fill"  # perp: open | close | liquidation
    position_side: Side | None = None
    leverage: float | None = None
    pnl: float | None = None  # realised, net of fees, on perp closes
    fee: float = 0.0


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
    perp_positions: dict[str, PerpPosition] = Field(default_factory=dict)
    trades: list[Trade] = Field(default_factory=list)

    def equity(self, prices: dict[str, float]) -> float:
        held = sum(p.amount * prices.get(p.symbol, p.avg_price) for p in self.positions.values())
        perp = sum(p.equity(prices.get(p.symbol, p.entry_price)) for p in self.perp_positions.values())
        return self.cash + held + perp


class Benchmark(BaseModel):
    """The yardstick: what buying the benchmark and holding it would have
    done since the bot started. Snapshotted on the first tick after a
    reset, so the comparison starts from the same moment for both."""

    symbol: str
    started_at: str
    start_price: float
    starting_equity: float


class AgentConfig(BaseModel):
    symbols: list[str]
    strategy: str = "sma_cross"
    timeframe: str = "1h"
    trade_fraction: float = Field(0.25, gt=0.0, le=1.0)  # share of cash per entry (margin, on perps)
    min_confidence: float = Field(0.0, ge=0.0, le=1.0)  # 0 = act on every signal
    use_llm_review: bool = True
    market: Market = Market.SPOT
    leverage: float = Field(3.0, ge=1.0, le=20.0)  # perps only
    allow_shorts: bool = True  # perps only: a SELL with no position opens a short
    # Exits and risk (see app/tools/exits.py, sizing.py, risk.py). With
    # stop_atr = 0 there are no stops and entries are sized by trade_fraction
    # alone; above 0, every entry gets a stop that many ATRs away, a target at
    # target_r times that risk, and a size that loses risk_per_trade of the
    # equity if the stop fills (never more cash than trade_fraction).
    stop_atr: float = Field(2.0, ge=0.0, le=10.0)
    target_r: float = Field(2.0, ge=0.5, le=10.0)
    risk_per_trade: float = Field(0.01, ge=0.001, le=0.1)
    daily_loss_limit: float = Field(0.0, ge=0.0, le=0.5)  # 0 = off; no new entries past this drawdown in a UTC day
    max_entries_per_day: int = Field(0, ge=0, le=100)  # 0 = off


class DayMark(BaseModel):
    """The equity at the first tick of a UTC day, for the daily loss limit."""

    date: str
    equity: float


class AgentState(BaseModel):
    mode: str = "paper"
    config: AgentConfig
    portfolio: Portfolio
    decisions: list[Decision] = Field(default_factory=list)
    last_tick: str | None = None
    ticks: int = 0
    last_prices: dict[str, float] = Field(default_factory=dict)
    benchmark: Benchmark | None = None
    day_start: DayMark | None = None
