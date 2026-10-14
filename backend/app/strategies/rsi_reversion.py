"""Mean reversion on RSI: buy oversold, sell overbought."""

from __future__ import annotations

from app.tools.indicators import latest, rsi

from .base import Action, Signal, Strategy


class RsiReversion(Strategy):
    name = "rsi_reversion"
    description = "Compra con RSI(14) por debajo de 30 (sobreventa) y vende por encima de 70 (sobrecompra)."

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0) -> None:
        self.period, self.oversold, self.overbought = period, oversold, overbought
        self.min_candles = period + 1

    def evaluate(self, symbol: str, closes: list[float]) -> Signal:
        value = latest(rsi(closes, self.period)) if len(closes) >= self.min_candles else None
        if value is None:
            return self.hold(symbol, f"faltan velas: {len(closes)}/{self.min_candles}")

        indicators = {f"rsi_{self.period}": value}
        if value < self.oversold:
            confidence = min(1.0, (self.oversold - value) / self.oversold)
            return Signal(strategy=self.name, symbol=symbol, action=Action.BUY, confidence=confidence,
                          reason=f"RSI {value:.1f} en sobreventa", indicators=indicators)
        if value > self.overbought:
            confidence = min(1.0, (value - self.overbought) / (100 - self.overbought))
            return Signal(strategy=self.name, symbol=symbol, action=Action.SELL, confidence=confidence,
                          reason=f"RSI {value:.1f} en sobrecompra", indicators=indicators)
        return self.hold(symbol, f"RSI {value:.1f} en zona neutra", **indicators)
