"""Member levels: Bronze, Silver, Gold, Platinum. Points come from things
the account has actually done, recomputed from the database every time, so
there is nothing to keep in sync."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import REVIEW_APPROVED, Certificate, QuestClaim, Review, User, UserEvent


@dataclass(frozen=True, slots=True)
class Level:
    id: str
    min_points: int


LEVELS: tuple[Level, ...] = (
    Level("bronze", 0),
    Level("silver", 30),
    Level("gold", 80),
    Level("platinum", 140),
)
RANK = {level.id: index for index, level in enumerate(LEVELS)}

# Points per thing done. Each event type counts once (the table enforces it).
POINTS = {"event": 10, "claim": 15, "certificate": 25, "review": 20, "wallet": 10}


def level_for(points: int) -> Level:
    current = LEVELS[0]
    for level in LEVELS:
        if points >= level.min_points:
            current = level
    return current


def next_level(level: Level) -> Level | None:
    index = RANK[level.id] + 1
    return LEVELS[index] if index < len(LEVELS) else None


def outranks(a: str, b: str) -> bool:
    return RANK.get(a, 0) > RANK.get(b, 0)


class LevelOut(BaseModel):
    id: str
    min_points: int


class LadderOut(BaseModel):
    levels: list[LevelOut]
    points: dict[str, int]


class ScoreOut(BaseModel):
    points: int
    level: str
    next_level: str | None = None
    next_at: int | None = None
    progress: float  # 0..1 towards the next level (1 at the top)
    counts: dict[str, int]
    breakdown: dict[str, int]


def ladder() -> LadderOut:
    return LadderOut(levels=[LevelOut(id=lv.id, min_points=lv.min_points) for lv in LEVELS], points=POINTS)


async def score(session: AsyncSession, user: User) -> ScoreOut:
    async def count(model) -> int:
        return await session.scalar(select(func.count()).select_from(model).where(model.user_id == user.id)) or 0

    review = await session.scalar(
        select(func.count()).select_from(Review).where(Review.user_id == user.id, Review.status == REVIEW_APPROVED)
    )
    counts = {
        "event": await count(UserEvent), "claim": await count(QuestClaim), "certificate": await count(Certificate),
        "review": 1 if review else 0, "wallet": 1 if user.wallet_address else 0,
    }
    breakdown = {key: counts[key] * POINTS[key] for key in POINTS}
    points = sum(breakdown.values())
    level = level_for(points)
    following = next_level(level)
    if following:
        span = following.min_points - level.min_points
        progress = (points - level.min_points) / span if span else 1.0
    else:
        progress = 1.0
    return ScoreOut(points=points, level=level.id, next_level=following.id if following else None,
                    next_at=following.min_points if following else None, progress=round(min(progress, 1.0), 3),
                    counts=counts, breakdown=breakdown)
