from pydantic import BaseModel, EmailStr, Field

from app.services.auth import UserOut


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field("", max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class EmailIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=2000)


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=2000)
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str | None = None  # absent while the email is unconfirmed
    token_type: str = "bearer"
    user: UserOut
    verification_required: bool = False
    verify_url: str | None = None  # console email backend + DEBUG only: the link, for local testing


class MessageOut(BaseModel):
    message: str


class UsersOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    size: int


class UserPatch(BaseModel):
    name: str | None = Field(None, max_length=80)
    role: str | None = Field(None, pattern="^(user|admin)$")
    is_active: bool | None = None
    is_verified: bool | None = None


class StatsOut(BaseModel):
    total: int
    verified: int
    active: int
    admins: int
    new_7d: int
