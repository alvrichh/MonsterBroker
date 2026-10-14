"""MonsterCoin and Monster Badges: what is deployed, what a signed-in user
holds, and the learn-to-earn claims."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, QuestsDep, TokenDep
from app.onchain.token import TokenError, TokenInfo
from app.services.membership import PRO_DAYS_FOR_QUESTS
from app.services.quests import CLIENT_EVENTS, QUESTS, ClaimOut, QuestError
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter()


class QuestOut(BaseModel):
    id: str
    mbk: int
    badge: bool
    event: str | None  # what completes it; None = having a wallet
    eligible: bool | None = None  # only for a signed-in user
    claim: ClaimOut | None = None


class InfoOut(TokenInfo):
    minter_address: str | None = None
    quests: list[QuestOut]


class MeOut(BaseModel):
    wallet_address: str | None
    balance_mbk: float | None = None  # None until the contracts are deployed
    badges: int | None = None
    chain_error: str | None = None
    events: list[str]
    quests: list[QuestOut]


class ClaimIn(BaseModel):
    quest: str = Field(pattern=r"^[a-z_]{1,32}$")


class ClaimCreated(ClaimOut):
    pro_days_granted: int | None = None  # set when this claim completed every quest


class EventIn(BaseModel):
    event: str = Field(pattern=r"^[a-z_]{1,32}$")


class EventsOut(BaseModel):
    events: list[str]


def _catalogue() -> list[QuestOut]:
    return [QuestOut(id=q.id, mbk=q.mbk, badge=q.badge, event=q.event) for q in QUESTS.values()]


@router.get("/info", response_model=InfoOut)
async def info(token: TokenDep, quests: QuestsDep):
    base = await token.info()
    return InfoOut(**base.model_dump(), minter_address=quests.minter_address, quests=_catalogue())


@router.get("/metadata/{quest_id}")
def metadata(quest_id: str, quests: QuestsDep) -> dict:
    """ERC-721 metadata the badge contract points at (tokenURI)."""
    if quest_id not in QUESTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown badge")
    return quests.metadata(quest_id)


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser, session: DbSession, token: TokenDep, quests: QuestsDep):
    events = await quests.events_for(session, user.id)
    claims = await quests.claims_for(session, user.id)
    out = MeOut(wallet_address=user.wallet_address, events=sorted(events), quests=[
        QuestOut(id=q.id, mbk=q.mbk, badge=q.badge, event=q.event, eligible=quests.eligible(q, user, events),
                 claim=ClaimOut.from_claim(claims[q.id]) if q.id in claims else None)
        for q in QUESTS.values()
    ])
    if token.configured and user.wallet_address:
        try:
            out.balance_mbk = await token.balance_of(user.wallet_address)
            out.badges = await token.badges_of(user.wallet_address)
        except TokenError as error:
            out.chain_error = str(error)
    return out


@router.post("/events", response_model=EventsOut)
async def report_event(body: EventIn, user: CurrentUser, session: DbSession, quests: QuestsDep):
    """The client reports something only it can see (a glossary opened)."""
    if body.event not in CLIENT_EVENTS:
        detail = {"code": "not_client_event", "message": "Ese evento no se puede declarar."}
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail)
    user_id = user.id  # a rolled-back race would expire the instance
    await quests.record_event(session, user_id, body.event)
    return EventsOut(events=sorted(await quests.events_for(session, user_id)))


@router.post("/claim", response_model=ClaimCreated, status_code=status.HTTP_201_CREATED)
async def claim(body: ClaimIn, user: CurrentUser, session: DbSession, quests: QuestsDep, background: BackgroundTasks):
    try:
        created, completed_all = await quests.claim(session, user, body.quest)
    except QuestError as error:
        raise HTTPException(error.status, {"code": error.code, "message": error.message}) from error
    # Minting takes a few seconds on-chain: answer now, settle after the response.
    background.add_task(quests.settle_by_id, created.id)
    out = ClaimCreated(**ClaimOut.from_claim(created).model_dump())
    if completed_all:
        out.pro_days_granted = PRO_DAYS_FOR_QUESTS
    return out
