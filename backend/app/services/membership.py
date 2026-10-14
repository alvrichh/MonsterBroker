"""Membership: free or Pro. Pro is granted by an admin, earned by finishing
every quest (a month), or, later, bought. Admins are Pro by definition."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from app.db.models import PLAN_FREE, PLAN_PRO, ROLE_ADMIN, User
from app.utils.helpers import utc_now

SOURCE_ADMIN, SOURCE_QUESTS, SOURCE_STRIPE = "admin", "quests", "stripe"
PRO_DAYS_FOR_QUESTS = 30

# What Pro gets today. The UI names them; the code checks `is_pro` where each applies.
PERKS = ["badge", "clean_certificates", "ai_review", "nft_certificates"]


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite hands naive datetimes back; treat them as UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def is_pro(user: User) -> bool:
    if user.role == ROLE_ADMIN:
        return True
    if user.plan != PLAN_PRO:
        return False
    until = as_utc(user.plan_until)
    return until is None or until > utc_now()


def grant_pro(user: User, days: int | None, source: str) -> None:
    """Start or extend Pro. `days=None` means no expiry; an open-ended plan
    is never shortened by a later, dated grant."""
    if user.plan == PLAN_PRO and user.plan_until is None and days is not None:
        return
    now = utc_now()
    current = as_utc(user.plan_until)
    base = current if (is_pro(user) and current and current > now) else now
    user.plan = PLAN_PRO
    user.plan_source = source
    user.plan_until = None if days is None else base + timedelta(days=days)


def revoke_pro(user: User) -> None:
    user.plan, user.plan_until, user.plan_source = PLAN_FREE, None, None


class PlanOut(BaseModel):
    plan: str
    is_pro: bool
    plan_until: str | None = None
    plan_source: str | None = None
    perks: list[str] = PERKS
    quests_days: int = PRO_DAYS_FOR_QUESTS

    @classmethod
    def from_user(cls, user: User) -> PlanOut:
        until = as_utc(user.plan_until)
        return cls(plan=user.plan, is_pro=is_pro(user), plan_until=until.isoformat() if until else None,
                   plan_source=user.plan_source)
