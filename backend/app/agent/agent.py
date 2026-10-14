"""The trading agent's loop.

One tick: for every configured symbol, fetch candles, ask the strategy for
a signal, optionally let Claude veto it, execute, remember. Ticks run on
demand (POST /api/bot/tick); nothing runs unattended by default.

Two markets. Spot: BUY opens a holding, SELL closes it. Perpetuals: BUY
opens a long, SELL opens a short (or closes a long); an opposite signal
flips the position; funding accrues between ticks and a candle through the
liquidation price wipes the margin.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from app.services.exchange import Candle, MarketDataError, MarketDataService
from app.services.futures import BinanceFuturesService
from app.services.http import UpstreamError
from app.strategies import get_strategy
from app.strategies.base import Action, Signal
from app.utils.helpers import now_iso, to_exchange_symbol, utc_now
from app.utils.logger import get_logger

from .executor import Executor, PerpExecutor
from .memory import Memory
from .state import AgentConfig, AgentState, Benchmark, Decision, Market, Portfolio, Side, Trade

log = get_logger(__name__)

CANDLES_PER_TICK = 120
BENCHMARK_SYMBOL = "BTC/USDT"  # the "just buy bitcoin and hold" yardstick
MAX_FUNDING_HOURS = 24 * 7  # a bot left alone for a month doesn't get a month of funding in one tick


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
                 reviewer: Reviewer | None = None, futures: BinanceFuturesService | None = None,
                 perp_executor: PerpExecutor | None = None) -> None:
        self.market = market
        self.memory = memory
        self.executor = executor
        self.reviewer = reviewer
        self.futures = futures
        self.perp_executor = perp_executor or PerpExecutor()

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
        equity_before = state.portfolio.equity(state.last_prices)
        perp = state.config.market == Market.PERP
        hours = self._hours_since(state.last_tick)

        for symbol in state.config.symbols:
            try:
                if perp:
                    candles, mark, funding = await self._perp_data(symbol, state.config.timeframe)
                else:
                    candles, mark, funding = await self.market.ohlcv(symbol, state.config.timeframe,
                                                                     limit=CANDLES_PER_TICK), None, 0.0
            except (MarketDataError, UpstreamError) as error:
                result.errors.append(f"{symbol}: {error}")
                continue
            if not candles:
                result.errors.append(f"{symbol}: no candles")
                continue

            closes = [c.close for c in candles]
            price = mark or closes[-1]
            state.last_prices[symbol] = price
            if perp:
                self._settle_perp(state, symbol, candles[-1], price, funding, hours, result)

            signal = strategy.evaluate(symbol, closes)
            decision = Decision(time=result.time, symbol=symbol, action=signal.action,
                                confidence=signal.confidence, reason=signal.reason,
                                strategy=signal.strategy, price=price)

            actionable = self._perp_actionable(state, signal, decision) if perp \
                else self._actionable(state, signal, decision)
            if actionable and await self._approved(state, signal, closes, decision):
                trades = self._execute_perp(state, signal, price, result.time) if perp \
                    else self._execute_spot(state, signal, price)
                if trades:
                    decision.executed = True
                    result.trades.extend(trades)
                    for trade in trades:
                        log.info("%s %s %s %.6f @ %.2f (%s)", trade.action, trade.side, symbol, trade.amount,
                                 trade.price, trade.reason)

            self.memory.remember(state, decision)
            result.decisions.append(decision)

        state.last_tick = result.time
        state.ticks += 1
        result.equity = state.portfolio.equity(state.last_prices)
        if state.benchmark is None:
            await self._start_benchmark(state, result, equity_before)
        self.memory.save(state)
        return result

    # ----------------------------------------------------------------- spot

    def _execute_spot(self, state: AgentState, signal: Signal, price: float) -> list[Trade]:
        trade = self.executor.execute(state.portfolio, signal, price, state.config.trade_fraction)
        return [trade] if trade else []

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

    # ----------------------------------------------------------------- perp

    async def _perp_data(self, symbol: str, timeframe: str) -> tuple[list[Candle], float | None, float]:
        if not self.futures:
            raise MarketDataError("futures data not configured")
        pair = to_exchange_symbol(symbol)
        candles = await self.futures.klines(pair, timeframe, CANDLES_PER_TICK)
        mark, funding = None, 0.0
        try:
            premium = await self.futures.premium(pair)
            mark, funding = premium.mark_price, premium.funding_rate
        except UpstreamError as error:  # candles are enough to trade; mark/funding are refinements
            log.warning("premium index for %s unavailable: %s", pair, error)
        return candles, mark, funding

    def _settle_perp(self, state: AgentState, symbol: str, candle: Candle, mark: float, funding: float,
                     hours: float, result: TickResult) -> None:
        """Before looking at a new signal: charge funding and liquidate if the
        last candle traded through the liquidation price."""
        position = state.portfolio.perp_positions.get(symbol)
        if not position:
            return
        self.perp_executor.accrue_funding(state.portfolio, symbol, funding, hours, mark)
        if not self.perp_executor.is_liquidated(position, candle.low, candle.high):
            return
        trade = self.perp_executor.close(state.portfolio, symbol, mark, result.time, state.config.strategy,
                                         "liquidación: el precio cruzó el nivel de liquidación", liquidated=True)
        if trade:
            result.trades.append(trade)
            self.memory.remember(state, Decision(
                time=result.time, symbol=symbol, action=trade.side, confidence=1.0,
                reason=f"liquidación de la posición {position.side} a {position.liquidation_price:.2f}",
                strategy=state.config.strategy, price=position.liquidation_price, executed=True,
            ))
            log.warning("liquidated %s %s: margin %.2f lost", position.side, symbol, position.margin)

    @staticmethod
    def _perp_actionable(state: AgentState, signal: Signal, decision: Decision) -> bool:
        if signal.action == Action.HOLD:
            return False
        if signal.confidence < state.config.min_confidence:
            decision.reason += " · confianza insuficiente"
            return False
        position = state.portfolio.perp_positions.get(signal.symbol)
        if signal.action == Action.BUY and position and position.side == Side.LONG:
            decision.reason += " · ya en largo"
            return False
        if signal.action == Action.SELL and position and position.side == Side.SHORT:
            decision.reason += " · ya en corto"
            return False
        if signal.action == Action.SELL and not position and not state.config.allow_shorts:
            decision.reason += " · cortos desactivados"
            return False
        return True

    def _execute_perp(self, state: AgentState, signal: Signal, price: float, now: str) -> list[Trade]:
        trades: list[Trade] = []
        portfolio, config = state.portfolio, state.config
        if signal.symbol in portfolio.perp_positions:  # the opposite side is open: flip
            closed = self.perp_executor.close(portfolio, signal.symbol, price, now, signal.strategy,
                                              f"cierre por señal contraria: {signal.reason}")
            if closed:
                trades.append(closed)
            if signal.action == Action.SELL and not config.allow_shorts:
                return trades  # closed the long; shorts are off, so stop there
        opened = self.perp_executor.open(portfolio, signal, price, config.trade_fraction, config.leverage, now)
        if opened:
            trades.append(opened)
        return trades

    @staticmethod
    def _hours_since(iso: str | None) -> float:
        if not iso:
            return 0.0
        try:
            elapsed = (utc_now() - datetime.fromisoformat(iso)).total_seconds() / 3600
        except ValueError:
            return 0.0
        return min(max(elapsed, 0.0), MAX_FUNDING_HOURS)

    # ------------------------------------------------------------ benchmark

    async def _start_benchmark(self, state: AgentState, result: TickResult, equity: float) -> None:
        price = state.last_prices.get(BENCHMARK_SYMBOL)
        if price is None:
            try:
                candles = await self.market.ohlcv(BENCHMARK_SYMBOL, state.config.timeframe, limit=1)
            except MarketDataError as error:
                result.errors.append(f"{BENCHMARK_SYMBOL} (benchmark): {error}")
                return
            if not candles:
                return
            price = candles[-1].close
        state.benchmark = Benchmark(symbol=BENCHMARK_SYMBOL, started_at=result.time,
                                    start_price=price, starting_equity=equity)

    # --------------------------------------------------------------- review

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
