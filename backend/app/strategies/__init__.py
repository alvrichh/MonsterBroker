"""Every strategy the agent can run, by name."""

from .base import Action, Signal, Strategy
from .rsi_reversion import RsiReversion
from .sma_cross import SmaCross

STRATEGIES: dict[str, Strategy] = {s.name: s for s in (SmaCross(), RsiReversion())}


def get_strategy(name: str) -> Strategy:
    try:
        return STRATEGIES[name]
    except KeyError as error:
        raise KeyError(f"unknown strategy {name!r}; available: {', '.join(STRATEGIES)}") from error


__all__ = ["STRATEGIES", "Action", "Signal", "Strategy", "get_strategy"]
