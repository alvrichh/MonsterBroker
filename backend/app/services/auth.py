"""Users in the database, bcrypt passwords, JWTs for sessions and for the
one-shot links (email verification, password reset)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ROLE_ADMIN, ROLE_USER, User
from app.utils.helpers import utc_now

PURPOSE_ACCESS = "access"
PURPOSE_VERIFY = "verify"
PURPOSE_RESET = "reset"
MIN_PASSWORD = 8


class AuthError(Exception):
    def __init__(self, message: str, code: str = "auth_error", status: int = 400) -> None:
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:  # SQLite hands back naive datetimes; they were stored as UTC
        value = value.replace(tzinfo=UTC)
    return value.replace(microsecond=0).isoformat()


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login_at: str | None = None

    @classmethod
    def from_user(cls, user: User) -> UserOut:
        return cls(
            id=user.id, email=user.email, name=user.name, role=user.role, is_active=user.is_active,
            is_verified=user.is_verified, created_at=_iso(user.created_at) or "",
            last_login_at=_iso(user.last_login_at),
        )


class AuthService:
    def __init__(self, secret: str, access_minutes: int, verify_hours: int, reset_minutes: int,
                 admin_emails: list[str]) -> None:
        self._secret = secret
        self._access = timedelta(minutes=access_minutes)
        self._verify = timedelta(hours=verify_hours)
        self._reset = timedelta(minutes=reset_minutes)
        self._admin_emails = {e.strip().lower() for e in admin_emails if e.strip()}

    # ---------------------------------------------------------------- users

    async def by_email(self, session: AsyncSession, email: str) -> User | None:
        return await session.scalar(select(User).where(User.email == email.strip().lower()))

    async def by_id(self, session: AsyncSession, user_id: str) -> User | None:
        return await session.get(User, user_id)

    async def register(self, session: AsyncSession, email: str, password: str, name: str) -> User:
        email = email.strip().lower()
        if len(password) < MIN_PASSWORD:
            raise AuthError(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", "weak_password")
        if await self.by_email(session, email):
            raise AuthError("Ya existe una cuenta con ese email.", "email_taken", 409)
        user = User(
            id=uuid4().hex[:12], email=email, name=name.strip() or email.split("@")[0],
            password_hash=self.hash_password(password),
            role=ROLE_ADMIN if email in self._admin_emails else ROLE_USER,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def authenticate(self, session: AsyncSession, email: str, password: str) -> User:
        user = await self.by_email(session, email)
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            raise AuthError("Email o contraseña incorrectos.", "bad_credentials", 401)
        if not user.is_active:
            raise AuthError("Esta cuenta está desactivada.", "inactive", 403)
        user.last_login_at = utc_now()
        await session.commit()
        return user

    async def mark_verified(self, session: AsyncSession, user: User) -> None:
        if not user.is_verified:
            user.is_verified = True
            user.verified_at = utc_now()
            await session.commit()

    async def set_password(self, session: AsyncSession, user: User, password: str) -> None:
        if len(password) < MIN_PASSWORD:
            raise AuthError(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.", "weak_password")
        user.password_hash = self.hash_password(password)
        await session.commit()

    async def search(self, session: AsyncSession, query: str = "", page: int = 1,
                     size: int = 50) -> tuple[list[User], int]:
        stmt = select(User)
        if query:
            needle = f"%{query.strip().lower()}%"
            stmt = stmt.where(or_(User.email.ilike(needle), User.name.ilike(needle)))
        total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await session.scalars(stmt.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size))
        return list(rows), total

    async def stats(self, session: AsyncSession) -> dict[str, int]:
        week_ago = utc_now() - timedelta(days=7)
        count = select(func.count()).select_from(User)
        return {
            "total": await session.scalar(count) or 0,
            "verified": await session.scalar(count.where(User.is_verified.is_(True))) or 0,
            "active": await session.scalar(count.where(User.is_active.is_(True))) or 0,
            "admins": await session.scalar(count.where(User.role == ROLE_ADMIN)) or 0,
            "new_7d": await session.scalar(count.where(User.created_at >= week_ago)) or 0,
        }

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # --------------------------------------------------------------- tokens

    def _token(self, user: User, purpose: str, lifetime: timedelta) -> str:
        now = utc_now()
        payload = {"sub": user.id, "email": user.email, "purpose": purpose, "iat": now, "exp": now + lifetime}
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def access_token(self, user: User) -> str:
        return self._token(user, PURPOSE_ACCESS, self._access)

    def verification_token(self, user: User) -> str:
        return self._token(user, PURPOSE_VERIFY, self._verify)

    def reset_token(self, user: User) -> str:
        return self._token(user, PURPOSE_RESET, self._reset)

    def decode(self, token: str, purpose: str) -> dict | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None
        return payload if payload.get("purpose") == purpose else None

    async def user_from_token(self, session: AsyncSession, token: str, purpose: str = PURPOSE_ACCESS) -> User | None:
        payload = self.decode(token, purpose)
        if not payload:
            return None
        user = await self.by_id(session, str(payload.get("sub", "")))
        return user if user and user.is_active else None
