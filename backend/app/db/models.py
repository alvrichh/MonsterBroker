from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.helpers import utc_now

from .database import Base

ROLE_USER = "user"
ROLE_ADMIN = "admin"

PROVIDER_PASSWORD = "password"
PROVIDER_WALLET = "wallet"

PLAN_FREE = "free"
PLAN_PRO = "pro"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(16), default=ROLE_USER)
    # How the account was created: password | google | github | microsoft | wallet
    provider: Mapped[str] = mapped_column(String(16), default=PROVIDER_PASSWORD)
    wallet_address: Mapped[str | None] = mapped_column(String(42), unique=True, index=True, nullable=True)
    # Membership: free | pro. plan_until None = no expiry; plan_source = admin | quests | stripe
    plan: Mapped[str] = mapped_column(String(16), default=PLAN_FREE)
    plan_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plan_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserEvent(Base):
    """Something a user did that a quest can check: the first row per
    (user, event) is what matters, later ones are harmless."""

    __tablename__ = "user_events"
    __table_args__ = (UniqueConstraint("user_id", "event", name="uq_user_event"),)

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(16), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


REVIEW_PENDING, REVIEW_APPROVED, REVIEW_HIDDEN = "pending", "approved", "hidden"


class Review(Base):
    """One opinion per member, shown on the home page once an admin approves it."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(16), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1..5
    text: Mapped[str] = mapped_column(String(280))
    status: Mapped[str] = mapped_column(String(16), default=REVIEW_PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Certificate(Base):
    """A course certificate. The id is the public verification code."""

    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("user_id", "course", name="uq_certificate"),)

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(16), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course: Mapped[str] = mapped_column(String(32))
    holder: Mapped[str] = mapped_column(String(80))  # the name printed on it
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    nft_tx: Mapped[str | None] = mapped_column(String(66), nullable=True)  # once minted on-chain


class QuestClaim(Base):
    """A learn-to-earn reward a user has claimed: pending until the backend
    wallet mints it, then minted (with the tx hashes) or failed (retryable)."""

    __tablename__ = "quest_claims"
    __table_args__ = (UniqueConstraint("user_id", "quest", name="uq_quest_claim"),)

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(16), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    quest: Mapped[str] = mapped_column(String(32))
    wallet_address: Mapped[str] = mapped_column(String(42))
    mbk: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    tx_token: Mapped[str | None] = mapped_column(String(66), nullable=True)
    tx_badge: Mapped[str | None] = mapped_column(String(66), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
