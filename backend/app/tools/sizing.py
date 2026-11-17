"""Position size from the most you are willing to lose.

If the stop is `risk` away per unit and you accept losing `max_loss` when it
fills, you hold max_loss / risk units, never more than the cash cap allows.
Ported from the budget manager in Jake Schincariol's day-trader-skill (MIT,
see THIRD_PARTY_NOTICES.md).
"""

from __future__ import annotations


def units_for_risk(max_loss: float, risk_per_unit: float, price: float, budget_cap: float,
                   leverage: float = 1.0) -> float:
    """Units to hold so a fill at the stop loses about `max_loss`.

    `budget_cap` is the most cash the position may lock: the cost on spot,
    the margin on perps (notional / leverage). Whichever is smaller wins, so
    a tight stop never sizes past the cash you set aside. 0 when any input
    can't size a position."""
    if max_loss <= 0 or risk_per_unit <= 0 or price <= 0 or budget_cap <= 0 or leverage <= 0:
        return 0.0
    by_risk = max_loss / risk_per_unit
    by_cash = budget_cap * leverage / price
    return min(by_risk, by_cash)
