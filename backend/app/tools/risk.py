"""Pre-trade checks: every new position against the limits, PASS or BLOCK
with the reason. Only openings are checked; closing a position never adds
risk, so it is never blocked.

Ported from the risk manager in Jake Schincariol's day-trader-skill (MIT, see
THIRD_PARTY_NOTICES.md), trimmed to what a 24/7 crypto paper bot needs: the
loss at the stop, the day's loss limit, trades per day and a stop that
liquidation would beat.
"""

from __future__ import annotations

from dataclasses import dataclass

TOLERANCE = 1.02  # rounding slack on the loss at the stop


@dataclass(slots=True, frozen=True)
class EntryCheck:
    equity: float
    loss_at_stop: float | None  # quote lost if the stop fills; None when the trade has no stop
    max_loss: float | None  # the per-trade limit, quote; None = no limit
    day_start_equity: float | None = None
    daily_loss_limit: float = 0.0  # fraction of the day's starting equity; 0 = off
    entries_today: int = 0
    max_entries_per_day: int = 0  # 0 = off
    stop: float | None = None
    liquidation: float | None = None  # perps only
    long: bool = True


def check_entry(c: EntryCheck) -> list[str]:
    """Why this opening is blocked, one line per broken limit. Empty = PASS."""
    reasons: list[str] = []
    if c.max_loss is not None and c.loss_at_stop is not None and c.loss_at_stop > c.max_loss * TOLERANCE:
        reasons.append(f"pérdida en el stop {c.loss_at_stop:.2f} > límite por trade {c.max_loss:.2f}")
    if c.daily_loss_limit > 0 and c.day_start_equity:
        floor = c.day_start_equity * (1 - c.daily_loss_limit)
        if c.equity <= floor:
            reasons.append(f"límite de pérdida diaria alcanzado ({c.daily_loss_limit:.0%})")
    if c.max_entries_per_day > 0 and c.entries_today >= c.max_entries_per_day:
        reasons.append(f"máximo de {c.max_entries_per_day} entradas por día")
    if c.stop is not None and c.liquidation is not None:
        beyond = c.stop <= c.liquidation if c.long else c.stop >= c.liquidation
        if beyond:
            reasons.append("el stop queda más allá de la liquidación: baja el apalancamiento")
    return reasons
