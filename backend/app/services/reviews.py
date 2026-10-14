"""Member reviews for the home page. Real ones only: each comes from a
signed-in account, is moderated by an admin, and shows the name the member
chose. Sample cards in the UI are labelled as samples, never mixed in."""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    REVIEW_APPROVED,
    REVIEW_HIDDEN,
    REVIEW_PENDING,
    ROLE_ADMIN,
    Certificate,
    QuestClaim,
    Review,
    User,
)
from app.services.membership import as_utc, is_pro
from app.utils.helpers import utc_now

STATUSES = (REVIEW_PENDING, REVIEW_APPROVED, REVIEW_HIDDEN)
PUBLIC_LIMIT = 6


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=10, max_length=280)


class ReviewOut(BaseModel):
    id: str
    name: str
    rating: int
    text: str
    is_pro: bool = False
    status: str
    created_at: str


class ReviewStats(BaseModel):
    accounts: int
    certificates: int
    claims: int
    ticks: int = 0  # the Monster's ticks, from the agent state


class ReviewsOut(BaseModel):
    count: int
    average: float | None = None
    items: list[ReviewOut]
    stats: ReviewStats


def _out(review: Review, user: User) -> ReviewOut:
    return ReviewOut(id=review.id, name=user.name, rating=review.rating, text=review.text, is_pro=is_pro(user),
                     status=review.status, created_at=as_utc(review.created_at).isoformat())


class ReviewService:
    @staticmethod
    async def public(session: AsyncSession, ticks: int = 0) -> ReviewsOut:
        approved = select(Review, User).join(User, User.id == Review.user_id).where(Review.status == REVIEW_APPROVED)
        rows = (await session.execute(approved.order_by(Review.created_at.desc()).limit(PUBLIC_LIMIT))).all()
        count = await session.scalar(select(func.count()).select_from(Review).where(Review.status == REVIEW_APPROVED))
        average = await session.scalar(select(func.avg(Review.rating)).where(Review.status == REVIEW_APPROVED))
        stats = ReviewStats(
            accounts=await session.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0,
            certificates=await session.scalar(select(func.count()).select_from(Certificate)) or 0,
            claims=await session.scalar(select(func.count()).select_from(QuestClaim)) or 0,
            ticks=ticks,
        )
        return ReviewsOut(count=count or 0, average=round(float(average), 1) if average is not None else None,
                          items=[_out(review, user) for review, user in rows], stats=stats)

    @staticmethod
    async def mine(session: AsyncSession, user: User) -> ReviewOut | None:
        review = await session.scalar(select(Review).where(Review.user_id == user.id))
        return _out(review, user) if review else None

    @staticmethod
    async def upsert(session: AsyncSession, user: User, body: ReviewIn) -> ReviewOut:
        """Create or update the member's single review. Edits go back to
        pending (an admin's own review is approved straight away)."""
        review = await session.scalar(select(Review).where(Review.user_id == user.id))
        if review is None:
            review = Review(id=uuid4().hex[:12], user_id=user.id, created_at=utc_now())
            session.add(review)
        review.rating, review.text = body.rating, body.text.strip()
        review.status = REVIEW_APPROVED if user.role == ROLE_ADMIN else REVIEW_PENDING
        review.updated_at = utc_now()
        await session.commit()
        await session.refresh(review)
        return _out(review, user)

    # ------------------------------------------------------------------ admin

    @staticmethod
    async def list_for_admin(session: AsyncSession, status: str | None) -> list[ReviewOut]:
        query = select(Review, User).join(User, User.id == Review.user_id).order_by(Review.updated_at.desc())
        if status:
            query = query.where(Review.status == status)
        return [_out(review, user) for review, user in (await session.execute(query)).all()]

    @staticmethod
    async def set_status(session: AsyncSession, review_id: str, status: str) -> ReviewOut | None:
        row = (await session.execute(
            select(Review, User).join(User, User.id == Review.user_id).where(Review.id == review_id)
        )).first()
        if row is None:
            return None
        review, user = row
        review.status, review.updated_at = status, utc_now()
        await session.commit()
        return _out(review, user)
