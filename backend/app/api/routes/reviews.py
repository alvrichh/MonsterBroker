"""Member reviews: the public list with real usage numbers, and each
member's own review."""

from fastapi import APIRouter

from app.api.deps import AgentDep, CurrentUser, DbSession
from app.services.reviews import ReviewIn, ReviewOut, ReviewService, ReviewsOut

router = APIRouter()


@router.get("", response_model=ReviewsOut)
async def public(session: DbSession, agent: AgentDep):
    return await ReviewService.public(session, ticks=agent.state().ticks)


@router.get("/mine", response_model=ReviewOut | None)
async def mine(session: DbSession, user: CurrentUser):
    return await ReviewService.mine(session, user)


@router.post("", response_model=ReviewOut, status_code=201)
async def submit(body: ReviewIn, session: DbSession, user: CurrentUser):
    return await ReviewService.upsert(session, user, body)
