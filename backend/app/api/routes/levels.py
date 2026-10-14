"""Member levels: the ladder (public) and where the signed-in account stands."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.services.levels import LadderOut, ScoreOut, ladder, score

router = APIRouter()


@router.get("", response_model=LadderOut)
def the_ladder():
    return ladder()


@router.get("/me", response_model=ScoreOut)
async def mine(session: DbSession, user: CurrentUser):
    return await score(session, user)
