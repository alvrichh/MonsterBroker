"""The trading agent's loop.

One tick: for every configured symbol, fetch candles, ask the strategy for
a signal, optionally let Claude veto it, execute, remember. Ticks run on
demand (POST /api/bot/tick); nothing runs unattended by default.

Two markets. Spot: BUY opens a holding, SELL closes it. Perpetuals: BUY
opens a long, SELL opens a short (or closes a long); an opposite signal
flips the position; funding accrues between ticks and a candle through the
liquidation price wipes the margin.

Exits and risk, when config.stop_atr > 0: every entry gets a stop and a
target and is sized to lose risk_per_trade of the equity at the stop; each
tick first closes what hit its stop or target, and every new entry is checked
against the limits (app/tools/risk.py) before Claude is even asked.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from app.services.exchange import Candle, MarketDataError, MarketDataService, ResilientMarket
from app.services.futures import BinanceFuturesService
from app.services.http import UpstreamError
from app.strategies import get_strategy
from app.strategies.base import Action, Signal
from app.tools.exits import ExitPlan, atr, exit_hit, plan_exit
from app.tools.risk import EntryCheck, check_entry
from app.tools.sizing import units_for_risk
from app.utils.helpers import now_iso, to_exchange_symbol, utc_now
from app.utils.logger import get_logger

from .executor import Executor, PerpExecutor, liquidation_price
from .memory import Memory
from .state import AgentConfig, AgentState, Benchmark, DayMark, Decision, Market, Portfolio, Side, Trade

log = get_logger(__name__)

CANDLES_PER_TICK = 120
BENCHMARK_SYMBOL = "BTC/USDT"  # the "just buy bitcoin and hold" yardstick
MAX_FUNDING_HOURS = 24 * 7  # a bot left alone for a month doesn't get a month of funding in one tick
ATR_PERIOD = 14


class EntryPlan(BaseModel):
    """What an opening needs beyond the signal: where its exits go and how much
    cash it may lock. Empty when stops are off."""

    stop: float | None = None
    target: float | None = None
    budget: float | None = None  # spot: cost; perps: margin
    entry_bar: int | None = None
    blocked: list[str] = Field(default_factory=list)


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
    def __init__(self, market: MarketDataService | ResilientMarket, memory: Memory, executor: Executor,
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
        today = result.time[:10]
        if state.day_start is None or state.day_start.date != today:
            state.day_start = DayMark(date=today, equity=equity_before)

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
            else:
                self._settle_spot(state, symbol, candles[-1], price, result)

            signal = strategy.evaluate(symbol, closes)
            decision = Decision(time=result.time, symbol=symbol, action=signal.action,
                                confidence=signal.confidence, reason=signal.reason,
                                strategy=signal.strategy, price=price)

            actionable = self._perp_actionable(state, signal, decision) if perp \
                else self._actionable(state, signal, decision)
            plan = None
            if actionable and self._opens(state, signal):
                plan = self._entry_plan(state, signal, candles, price, today)
                if plan.blocked:
                    decision.reason += " · bloqueada: " + "; ".join(plan.blocked)
                    # A blocked opening can still close the opposite perp side.
                    actionable = perp and signal.symbol in state.portfolio.perp_positions
            if actionable and await self._approved(state, signal, closes, decision):
                trades = self._execute_perp(state, signal, price, result.time, plan) if perp \
                    else self._execute_spot(state, signal, price, plan)
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

    def _execute_spot(self, state: AgentState, signal: Signal, price: float,
                      plan: EntryPlan | None = None) -> list[Trade]:
        budget = plan.budget if plan else None
        trade = self.executor.execute(state.portfolio, signal, price, state.config.trade_fraction, budget)
        position = state.portfolio.positions.get(signal.symbol)
        if trade and signal.action == Action.BUY and position and plan:
            position.stop, position.target, position.entry_bar = plan.stop, plan.target, plan.entry_bar
        return [trade] if trade else []

    def _settle_spot(self, state: AgentState, symbol: str, candle: Candle, price: float,
                     result: TickResult) -> None:
        """Sell a holding whose stop or target the last candle reached."""
        position = state.portfolio.positions.get(symbol)
        if not position:
            return
        hit = self._exit_on(position.stop, position.target, position.entry_bar, True, candle, price)
        if not hit:
            return
        kind, fill = hit
        reason = self._exit_reason(kind, fill)
        sell = Signal(strategy=state.config.strategy, symbol=symbol, action=Action.SELL, confidence=1.0,
                      reason=reason)
        trade = self.executor.execute(state.portfolio, sell, fill, state.config.trade_fraction)
        if trade:
            result.trades.append(trade)
            self.memory.remember(state, Decision(time=result.time, symbol=symbol, action=Action.SELL,
                                                 confidence=1.0, reason=reason, strategy=state.config.strategy,
                                                 price=fill, executed=True))

    # ------------------------------------------------------- exits and risk

    @staticmethod
    def _exit_on(stop: float | None, target: float | None, entry_bar: int | None, long: bool, candle: Candle,
                 price: float) -> tuple[str, float] | None:
        """(stop|target, fill price) when the candle reached one. On the candle
        the position filled on, only the price since then counts: its earlier
        low or high happened before the entry."""
        if stop is None and target is None:
            return None
        low, high = (price, price) if candle.time == entry_bar else (candle.low, candle.high)
        kind = exit_hit(long, low, high, stop, target)
        if kind is None:
            return None
        return kind, stop if kind == "stop" else target

    @staticmethod
    def _exit_reason(kind: str, fill: float) -> str:
        return f"stop alcanzado a {fill:.2f}" if kind == "stop" else f"objetivo alcanzado a {fill:.2f}"

    @staticmethod
    def _opens(state: AgentState, signal: Signal) -> bool:
        """Whether this signal opens a position (and so is subject to the limits)."""
        if state.config.market == Market.SPOT:
            return signal.action == Action.BUY
        return not (signal.action == Action.SELL and not state.config.allow_shorts)

    def _entry_plan(self, state: AgentState, signal: Signal, candles: list[Candle], price: float,
                    today: str) -> EntryPlan:
        config, portfolio = state.config, state.portfolio
        perp = config.market == Market.PERP
        long = signal.action == Action.BUY
        equity = portfolio.equity(state.last_prices)
        entries_today = sum(1 for t in portfolio.trades if t.time.startswith(today) and (
            t.action == "open" if t.market == Market.PERP else t.side == Action.BUY))
        plan = EntryPlan(entry_bar=candles[-1].time)
        check = EntryCheck(equity=equity, loss_at_stop=None, max_loss=None,
                           day_start_equity=state.day_start.equity if state.day_start else None,
                           daily_loss_limit=config.daily_loss_limit, entries_today=entries_today,
                           max_entries_per_day=config.max_entries_per_day, long=long)

        exits: ExitPlan | None = None
        if config.stop_atr > 0:
            value = atr([c.high for c in candles], [c.low for c in candles], [c.close for c in candles], ATR_PERIOD)
            exits = plan_exit(long, price, value or 0.0, config.stop_atr, config.target_r)
            if exits is None:
                plan.blocked.append("sin ATR suficiente para fijar el stop")
                return plan
            leverage = config.leverage if perp else 1.0
            # On a flip, the opposite side's margin comes back before this opens.
            cash = portfolio.cash + (self._perp_refund(state, signal.symbol, price) if perp else 0.0)
            max_loss = equity * config.risk_per_trade
            units = units_for_risk(max_loss, exits.risk, price, cash * config.trade_fraction, leverage)
            plan.stop, plan.target = exits.stop, exits.target
            plan.budget = units * price / leverage
            liquidation = liquidation_price(Side.LONG if long else Side.SHORT, price, leverage) if perp else None
            check = replace(check, loss_at_stop=units * exits.risk, max_loss=max_loss, stop=exits.stop,
                            liquidation=liquidation)
        plan.blocked = check_entry(check)
        return plan

    @staticmethod
    def _perp_refund(state: AgentState, symbol: str, price: float) -> float:
        position = state.portfolio.perp_positions.get(symbol)
        return position.equity(price) if position else 0.0

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
        long = position.side == Side.LONG
        hit = self._exit_on(position.stop, position.target, position.entry_bar, long, candle, mark)
        stop_first = hit and (hit[0] == "target" or (
            hit[1] > position.liquidation_price if long else hit[1] < position.liquidation_price))
        if hit and stop_first and position.margin > 0:  # a stop inside liquidation fills before it
            kind, fill = hit
            reason = self._exit_reason(kind, fill)
            trade = self.perp_executor.close(state.portfolio, symbol, fill, result.time, state.config.strategy, reason)
            if trade:
                result.trades.append(trade)
                self.memory.remember(state, Decision(
                    time=result.time, symbol=symbol, action=trade.side, confidence=1.0, reason=reason,
                    strategy=state.config.strategy, price=fill, executed=True,
                ))
            return
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

    def _execute_perp(self, state: AgentState, signal: Signal, price: float, now: str,
                      plan: EntryPlan | None = None) -> list[Trade]:
        trades: list[Trade] = []
        portfolio, config = state.portfolio, state.config
        if signal.symbol in portfolio.perp_positions:  # the opposite side is open: flip
            closed = self.perp_executor.close(portfolio, signal.symbol, price, now, signal.strategy,
                                              f"cierre por señal contraria: {signal.reason}")
            if closed:
                trades.append(closed)
            if signal.action == Action.SELL and not config.allow_shorts:
                return trades  # closed the long; shorts are off, so stop there
        if plan and plan.blocked:
            return trades  # the limits stop the new side; the close above stands
        opened = self.perp_executor.open(portfolio, signal, price, config.trade_fraction, config.leverage, now,
                                         margin=plan.budget if plan else None)
        if opened:
            trades.append(opened)
            position = portfolio.perp_positions[signal.symbol]
            if plan:
                position.stop, position.target, position.entry_bar = plan.stop, plan.target, plan.entry_bar
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
