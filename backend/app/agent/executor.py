"""Turns an approved signal into a trade.

PaperExecutor fills spot orders instantly at the last price. PerpExecutor
runs paper perpetuals: isolated margin, taker fee on open and close,
funding accrued per tick, liquidation when the candle trades through the
liquidation price. LiveExecutor exists so the shape is there, and refuses
to run.
"""

from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from app.strategies.base import Action, Signal
from app.utils.helpers import now_iso

from .state import Market, PerpPosition, Portfolio, Position, Side, Trade

TAKER_FEE = 0.0004  # Binance USDT-M taker: 0.04% of the notional
MAINTENANCE_MARGIN = 0.005  # flat 0.5%; Binance tiers it by size, this is the small-position tier
MIN_MARGIN = 10.0
FUNDING_INTERVAL_HOURS = 8.0


class Executor(Protocol):
    def execute(self, portfolio: Portfolio, signal: Signal, price: float, fraction: float) -> Trade | None: ...


def liquidation_price(side: Side, entry: float, leverage: float, mmr: float = MAINTENANCE_MARGIN) -> float:
    """Where an isolated position has lost its margin minus the maintenance
    buffer: 1/leverage away from the entry, less the buffer."""
    if side == Side.LONG:
        return entry * (1 - 1 / leverage + mmr)
    return entry * (1 + 1 / leverage - mmr)


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


class PerpExecutor:
    """Paper perpetuals. Fills at the mark price; one position per symbol."""

    def open(self, portfolio: Portfolio, signal: Signal, price: float, fraction: float, leverage: float,
             now: str) -> Trade | None:
        if price <= 0 or signal.action == Action.HOLD or signal.symbol in portfolio.perp_positions:
            return None
        side = Side.LONG if signal.action == Action.BUY else Side.SHORT
        margin = portfolio.cash * fraction
        notional = margin * leverage
        fee = notional * TAKER_FEE
        if margin < MIN_MARGIN or margin + fee > portfolio.cash:
            return None
        size = notional / price
        portfolio.cash -= margin + fee
        portfolio.perp_positions[signal.symbol] = PerpPosition(
            symbol=signal.symbol, side=side, size=size, entry_price=price, leverage=leverage, margin=margin,
            liquidation_price=liquidation_price(side, price, leverage), opened_at=now,
        )
        trade = Trade(
            id=uuid4().hex[:12], time=now, symbol=signal.symbol, side=signal.action, amount=size, price=price,
            value=notional, strategy=signal.strategy, reason=signal.reason, market=Market.PERP, action="open",
            position_side=side, leverage=leverage, fee=fee,
        )
        portfolio.trades.append(trade)
        return trade

    def close(self, portfolio: Portfolio, symbol: str, price: float, now: str, strategy: str, reason: str,
              liquidated: bool = False) -> Trade | None:
        position = portfolio.perp_positions.pop(symbol, None)
        if not position:
            return None
        if liquidated:
            # The margin is gone; the fill is the liquidation level itself.
            fill, fee, pnl, returned = position.liquidation_price, 0.0, -position.margin, 0.0
        else:
            fill = price
            fee = position.size * price * TAKER_FEE
            pnl = position.unrealized_pnl(price) - fee
            returned = max(0.0, position.margin + pnl)
        portfolio.cash += returned
        trade = Trade(
            id=uuid4().hex[:12], time=now, symbol=symbol,
            side=Action.SELL if position.side == Side.LONG else Action.BUY,
            amount=position.size, price=fill, value=position.size * fill, strategy=strategy, reason=reason,
            market=Market.PERP, action="liquidation" if liquidated else "close", position_side=position.side,
            leverage=position.leverage, pnl=pnl, fee=fee,
        )
        portfolio.trades.append(trade)
        return trade

    @staticmethod
    def accrue_funding(portfolio: Portfolio, symbol: str, rate: float, hours: float, mark: float) -> float:
        """Funding settles every 8h; between ticks it is accrued pro rata on the
        notional. Longs pay when the rate is positive, shorts receive."""
        position = portfolio.perp_positions.get(symbol)
        if not position or hours <= 0 or not rate:
            return 0.0
        cost = rate * position.size * mark * (hours / FUNDING_INTERVAL_HOURS)
        signed = cost if position.side == Side.LONG else -cost
        position.margin -= signed
        position.funding_paid += signed
        return signed

    @staticmethod
    def is_liquidated(position: PerpPosition, low: float, high: float) -> bool:
        if position.margin <= 0:
            return True
        if position.side == Side.LONG:
            return low <= position.liquidation_price
        return high >= position.liquidation_price


class LiveExecutor:
    """Deliberately not implemented. Real orders need exchange keys, order
    types, error handling and a human saying yes; none of that is here."""

    def execute(self, portfolio: Portfolio, signal: Signal, price: float, fraction: float) -> Trade | None:
        raise NotImplementedError("Live trading is not wired. Keep PAPER_TRADING=true.")
