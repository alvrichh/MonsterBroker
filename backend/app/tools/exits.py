"""Exit plans: where the stop and the target go before a trade opens.

The stop sits k ATRs from the entry (the market's own recent range, so a
quiet coin gets a tight stop and a wild one a wide one); the target sits R
times that risk on the other side. Ported to crypto from the exit planner in
Jake Schincariol's day-trader-skill (MIT, see THIRD_PARTY_NOTICES.md): there
the stop came from the stock's opening range, here from ATR, since crypto
has no opening bell.
"""

from __future__ import annotations

from dataclasses import dataclass


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    """Average true range over the last `period` bars, Wilder's smoothing.
    None when there aren't period + 1 bars."""
    n = len(closes)
    if period < 1 or n < period + 1 or len(highs) != n or len(lows) != n:
        return None
    ranges = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
              for i in range(1, n)]
    value = sum(ranges[:period]) / period
    for r in ranges[period:]:
        value = (value * (period - 1) + r) / period
    return value


@dataclass(slots=True, frozen=True)
class ExitPlan:
    long: bool
    entry: float
    stop: float
    target: float

    @property
    def risk(self) -> float:
        """Price distance to the stop, per unit."""
        return abs(self.entry - self.stop)

    @property
    def r_target(self) -> float:
        return abs(self.target - self.entry) / self.risk if self.risk else 0.0


def plan_exit(long: bool, entry: float, atr_value: float, stop_atr: float, target_r: float) -> ExitPlan | None:
    """Stop `stop_atr` ATRs away, target `target_r` times that risk the other
    way. None when the inputs can't make a plan (no ATR, a stop at or past
    zero)."""
    if entry <= 0 or atr_value <= 0 or stop_atr <= 0 or target_r <= 0:
        return None
    risk = stop_atr * atr_value
    if long:
        stop, target = entry - risk, entry + target_r * risk
    else:
        stop, target = entry + risk, entry - target_r * risk
    if stop <= 0 or target <= 0:
        return None
    return ExitPlan(long=long, entry=entry, stop=stop, target=target)


def exit_hit(long: bool, low: float, high: float, stop: float | None, target: float | None) -> str | None:
    """'stop', 'target' or None for one bar. A bar that touches both counts
    as the stop: bars don't say which came first, so assume the worse."""
    if long:
        if stop is not None and low <= stop:
            return "stop"
        if target is not None and high >= target:
            return "target"
    else:
        if stop is not None and high >= stop:
            return "stop"
        if target is not None and low <= target:
            return "target"
    return None
