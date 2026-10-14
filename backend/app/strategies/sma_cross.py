"""Moving-average crossover: buy when the fast SMA crosses above the slow
one, sell when it crosses below.

The cross is looked for in the last few candles, not only the latest one:
the agent ticks on demand, so a cross on the exact candle would almost
always be missed. Repeats are harmless, the agent holds one position per
symbol.
"""

from __future__ import annotations

from itertools import pairwise

from app.tools.indicators import sma

from .base import Action, Signal, Strategy


class SmaCross(Strategy):
    name = "sma_cross"
    description = (
        "Compra cuando la media rápida (9) cruza por encima de la lenta (21) en las últimas 3 velas; "
        "vende en el cruce contrario."
    )

    def __init__(self, fast: int = 9, slow: int = 21, lookback: int = 3) -> None:
        self.fast, self.slow, self.lookback = fast, slow, lookback
        self.min_candles = slow + lookback

    def evaluate(self, symbol: str, closes: list[float]) -> Signal:
        if len(closes) < self.min_candles:
            return self.hold(symbol, f"faltan velas: {len(closes)}/{self.min_candles}")

        fast_s, slow_s = sma(closes, self.fast), sma(closes, self.slow)
        # Fast minus slow over the window; a sign change inside it is a cross.
        diffs = [fast_s[i] - slow_s[i] for i in range(-self.lookback - 1, 0)]  # type: ignore[operator]
        indicators = {f"sma_{self.fast}": fast_s[-1], f"sma_{self.slow}": slow_s[-1]}
        # Spread as a share of price: 0.25% apart reads as full confidence.
        confidence = min(1.0, abs(diffs[-1]) / closes[-1] * 400)

        cross = Action.HOLD
        for prev, now in pairwise(diffs):
            if prev <= 0 < now:
                cross = Action.BUY
            elif prev >= 0 > now:
                cross = Action.SELL
        # Only count it if the latest candle still sits on the same side.
        if cross == Action.BUY and diffs[-1] > 0:
            return Signal(strategy=self.name, symbol=symbol, action=cross, confidence=confidence,
                          reason=f"SMA{self.fast} cruza por encima de SMA{self.slow}", indicators=indicators)
        if cross == Action.SELL and diffs[-1] < 0:
            return Signal(strategy=self.name, symbol=symbol, action=cross, confidence=confidence,
                          reason=f"SMA{self.fast} cruza por debajo de SMA{self.slow}", indicators=indicators)
        trend = "alcista" if diffs[-1] > 0 else "bajista"
        return self.hold(symbol, f"sin cruce reciente, tendencia {trend}", **indicators)
