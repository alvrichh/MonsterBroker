"""A strategy turns a list of closes into a signal. Pure and synchronous, so
it can be tested with made-up series."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel, Field


class Action(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Signal(BaseModel):
    strategy: str
    symbol: str
    action: Action
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reason: str = ""
    indicators: dict[str, float | None] = Field(default_factory=dict)


class Strategy(ABC):
    name: str = "base"
    description: str = ""
    min_candles: int = 2

    @abstractmethod
    def evaluate(self, symbol: str, closes: list[float]) -> Signal: ...

    def hold(self, symbol: str, reason: str, **indicators: float | None) -> Signal:
        return Signal(strategy=self.name, symbol=symbol, action=Action.HOLD, reason=reason, indicators=indicators)

    def describe(self) -> dict[str, object]:
        return {"name": self.name, "description": self.description, "min_candles": self.min_candles}
