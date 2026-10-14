"""Turns an approved signal into a trade.

PaperExecutor fills instantly at the last price against the in-memory
portfolio. LiveExecutor exists so the shape is there, and refuses to run.
"""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from app.strategies.base import Action, Signal
from app.utils.helpers import now_iso

from .state import Portfolio, Position, Trade


class Executor(Protocol):
    def execute(self, portfolio: Portfolio, signal: Signal, price: float, fraction: float) -> Trade | None: ...


class PaperExecutor:
    MIN_NOTIONAL = 10.0  # Binance's own floor for spot orders, in quote

    def execute(self, portfolio: Portfolio, signal: Signal, price: float, fraction: float) -> Trade | None:
        if price <= 0:
            return None
        if signal.action == Action.BUY:
            return self._buy(portfolio, signal, price, fraction)
        if signal.action == Action.SELL:
            return self._sell(portfolio, signal, price)
        return None

    def _buy(self, portfolio: Portfolio, signal: Signal, price: float, fraction: float) -> Trade | None:
        budget = portfolio.cash * fraction
        if budget < self.MIN_NOTIONAL:
            return None
        amount = budget / price
        position = portfolio.positions.get(signal.symbol) or Position(symbol=signal.symbol)
        total_cost = position.amount * position.avg_price + budget
        position.amount += amount
        position.avg_price = total_cost / position.amount
        portfolio.positions[signal.symbol] = position
        portfolio.cash -= budget
        return self._record(portfolio, signal, amount, price, budget)

    def _sell(self, portfolio: Portfolio, signal: Signal, price: float) -> Trade | None:
        position = portfolio.positions.get(signal.symbol)
        if not position or position.amount * price < self.MIN_NOTIONAL:
            return None
        value = position.amount * price
        portfolio.cash += value
        del portfolio.positions[signal.symbol]
        return self._record(portfolio, signal, position.amount, price, value)

    @staticmethod
    def _record(portfolio: Portfolio, signal: Signal, amount: float, price: float, value: float) -> Trade:
        trade = Trade(
            id=uuid4().hex[:12],
            time=now_iso(),
            symbol=signal.symbol,
            side=signal.action,
            amount=amount,
            price=price,
            value=value,
            strategy=signal.strategy,
            reason=signal.reason,
        )
        portfolio.trades.append(trade)
        return trade


class LiveExecutor:
    """Deliberately not implemented. Real orders need exchange keys, order
    types, error handling and a human saying yes; none of that is here."""

    def execute(self, portfolio: Portfolio, signal: Signal, price: float, fraction: float) -> Trade | None:
        raise NotImplementedError("Live trading is not wired. Keep PAPER_TRADING=true.")
