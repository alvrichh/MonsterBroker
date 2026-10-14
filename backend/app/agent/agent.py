"""The trading agent's loop.

One tick: for every configured symbol, fetch candles, ask the strategy for
a signal, optionally let Claude veto it, execute, remember. Ticks run on
demand (POST /api/bot/tick); nothing runs unattended by default.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from app.services.exchange import MarketDataError, MarketDataService
from app.strategies import get_strategy
from app.strategies.base import Action, Signal
from app.utils.helpers import now_iso
from app.utils.logger import get_logger

from .executor import Executor
from .memory import Memory
from .state import AgentConfig, AgentState, Decision, Portfolio, Trade

log = get_logger(__name__)

CANDLES_PER_TICK = 120


class Review(BaseModel):
    approve: bool
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    rationale: str = ""


class Reviewer(Protocol):
    async def review(self, signal: Signal, closes: list[float], portfolio: Portfolio) -> Review: ...


class TickResult(BaseModel):
    time: str
    decisions: list[Decision]
    trades: list[Trade]
    equity: float
    errors: list[str] = Field(default_factory=list)


class TradingAgent:
    def __init__(self, market: MarketDataService, memory: Memory, executor: Executor,
                 reviewer: Reviewer | None = None) -> None:
        self.market = market
        self.memory = memory
        self.executor = executor
        self.reviewer = reviewer

    # ---------------------------------------------------------------- state

    def state(self) -> AgentState:
        return self.memory.load()

    def reset(self) -> AgentState:
        return self.memory.reset()

    def update_config(self, **changes: object) -> AgentState:
        state = self.memory.load()
        merged = state.config.model_dump() | {k: v for k, v in changes.items() if v is not None}
        if "strategy" in changes and changes["strategy"] is not None:
            get_strategy(str(changes["strategy"]))  # raises KeyError on an unknown name
        state.config = AgentConfig.model_validate(merged)
        self.memory.save(state)
        return state

    # ----------------------------------------------------------------- tick

    async def tick(self) -> TickResult:
        state = self.memory.load()
        strategy = get_strategy(state.config.strategy)
        result = TickResult(time=now_iso(), decisions=[], trades=[], equity=0.0)

        for symbol in state.config.symbols:
            try:
                candles = await self.market.ohlcv(symbol, state.config.timeframe, limit=CANDLES_PER_TICK)
            except MarketDataError as error:
                result.errors.append(f"{symbol}: {error}")
                continue
            if not candles:
                result.errors.append(f"{symbol}: no candles")
                continue

            closes = [c.close for c in candles]
            price = closes[-1]
            state.last_prices[symbol] = price

            signal = strategy.evaluate(symbol, closes)
            decision = Decision(time=result.time, symbol=symbol, action=signal.action,
                                confidence=signal.confidence, reason=signal.reason,
                                strategy=signal.strategy, price=price)

            if self._actionable(state, signal, decision):
                approved = await self._approved(state, signal, closes, decision)
                if approved:
                    trade = self.executor.execute(state.portfolio, signal, price, state.config.trade_fraction)
                    if trade:
                        decision.executed = True
                        result.trades.append(trade)
                        log.info("%s %s %.6f @ %.2f (%s)", trade.side, symbol, trade.amount, price,
                                 signal.reason)

            self.memory.remember(state, decision)
            result.decisions.append(decision)

        state.last_tick = result.time
        state.ticks += 1
        result.equity = state.portfolio.equity(state.last_prices)
        self.memory.save(state)
        return result

    @staticmethod
    def _actionable(state: AgentState, signal: Signal, decision: Decision) -> bool:
        """One position per symbol: a repeated buy, or a sell with nothing to
        sell, is recorded but not executed."""
        if signal.action == Action.HOLD:
            return False
        if signal.confidence < state.config.min_confidence:
            decision.reason += " · confianza insuficiente"
            return False
        holding = signal.symbol in state.portfolio.positions
        if signal.action == Action.BUY and holding:
            decision.reason += " · ya en posición"
            return False
        if signal.action == Action.SELL and not holding:
            decision.reason += " · sin posición"
            return False
        return True

    async def _approved(self, state: AgentState, signal: Signal, closes: list[float], decision: Decision) -> bool:
        if not (self.reviewer and state.config.use_llm_review):
            return True
        try:
            review = await self.reviewer.review(signal, closes, state.portfolio)
        except Exception as error:  # the reviewer is a nice-to-have, never a blocker
            log.warning("review failed for %s: %s", signal.symbol, error)
            decision.review = f"revisión no disponible: {error}"
            return True
        verdict = "aprueba" if review.approve else "veta"
        decision.review = f"Claude {verdict} ({review.confidence:.0%}): {review.rationale}"
        return review.approve
