from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import AdminUser, AuthDep, DbSession
from app.api.schemas.auth import StatsOut, UserPatch, UsersOut
from app.db.models import PLAN_PRO, ROLE_USER
from app.services.auth import UserOut
from app.services.membership import SOURCE_ADMIN, grant_pro, revoke_pro
from app.services.reviews import ReviewOut, ReviewService
from app.utils.helpers import utc_now

router = APIRouter()


class ReviewPatch(BaseModel):
    status: str = Field(pattern="^(pending|approved|hidden)$")


@router.get("/reviews", response_model=list[ReviewOut])
async def reviews(session: DbSession, admin: AdminUser, status_: str | None = Query(None, alias="status")):
    return await ReviewService.list_for_admin(session, status_)


@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def patch_review(review_id: str, body: ReviewPatch, session: DbSession, admin: AdminUser):
    updated = await ReviewService.set_status(session, review_id, body.status)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Opinión no encontrada.")
    return updated


@router.get("/users", response_model=UsersOut)
async def users(session: DbSession, auth: AuthDep, admin: AdminUser, q: str = Query("", max_length=80),
                page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200)):
    rows, total = await auth.search(session, q, page, size)
    return UsersOut(items=[UserOut.from_user(u) for u in rows], total=total, page=page, size=size)


@router.patch("/users/{user_id}", response_model=UserOut)
async def patch_user(user_id: str, body: UserPatch, session: DbSession, auth: AuthDep, admin: AdminUser):
    user = await auth.by_id(session, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    if user.id == admin.id and (body.role == ROLE_USER or body.is_active is False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes quitarte el acceso a ti mismo.")
    if body.name is not None:
        user.name = body.name.strip() or user.name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_verified is not None:
        user.is_verified = body.is_verified
        user.verified_at = utc_now() if body.is_verified else None
    if body.plan == PLAN_PRO:
        grant_pro(user, body.plan_days, SOURCE_ADMIN)
    elif body.plan is not None:
        revoke_pro(user)
    await session.commit()
    await session.refresh(user)
    return UserOut.from_user(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, session: DbSession, auth: AuthDep, admin: AdminUser):
    user = await auth.by_id(session, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes borrar tu propia cuenta desde aquí.")
    await session.delete(user)
    await session.commit()


@router.get("/stats", response_model=StatsOut)
async def stats(session: DbSession, auth: AuthDep, admin: AdminUser):
    return StatsOut(**await auth.stats(session))
