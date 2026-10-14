"""Users in a JSON file, bcrypt passwords, JWT sessions. Enough for a
learning project; swap the store for a database when it grows."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import bcrypt
import jwt
from pydantic import BaseModel, EmailStr

from app.utils.helpers import now_iso, read_json, utc_now, write_json


class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: str


class StoredUser(User):
    password_hash: str


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, users_path: Path, secret: str, expire_minutes: int) -> None:
        self._path = users_path
        self._secret = secret
        self._expire = timedelta(minutes=expire_minutes)

    # ---------------------------------------------------------------- store

    def _load(self) -> dict[str, StoredUser]:
        raw = read_json(self._path, {})
        return {key: StoredUser.model_validate(value) for key, value in raw.items()}

    def _save(self, users: dict[str, StoredUser]) -> None:
        write_json(self._path, {key: user.model_dump(mode="json") for key, user in users.items()})

    # ---------------------------------------------------------------- users

    def register(self, email: str, password: str, name: str) -> User:
        email = email.strip().lower()
        if len(password) < 8:
            raise AuthError("La contraseña debe tener al menos 8 caracteres.")
        users = self._load()
        if email in users:
            raise AuthError("Ya existe una cuenta con ese email.")
        stored = StoredUser(
            id=uuid4().hex[:12],
            email=email,
            name=name.strip() or email.split("@")[0],
            created_at=now_iso(),
            password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        )
        users[email] = stored
        self._save(users)
        return User.model_validate(stored.model_dump())

    def authenticate(self, email: str, password: str) -> User | None:
        stored = self._load().get(email.strip().lower())
        if not stored or not bcrypt.checkpw(password.encode(), stored.password_hash.encode()):
            return None
        return User.model_validate(stored.model_dump())

    def get(self, user_id: str) -> User | None:
        for stored in self._load().values():
            if stored.id == user_id:
                return User.model_validate(stored.model_dump())
        return None

    # --------------------------------------------------------------- tokens

    def create_token(self, user: User) -> str:
        payload = {"sub": user.id, "email": user.email, "exp": utc_now() + self._expire}
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def user_from_token(self, token: str) -> User | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None
        return self.get(str(payload.get("sub", "")))
