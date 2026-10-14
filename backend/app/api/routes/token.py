"""MonsterCoin and Monster Badges: what is deployed, what a signed-in user
holds, and the learn-to-earn claims."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import AgentDep, CurrentUser, DbSession, QuestsDep, TokenDep
from app.onchain.token import TokenError, TokenInfo
from app.services.quests import QUESTS, ClaimOut, QuestError
from app.utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter()


class QuestOut(BaseModel):
    id: str
    mbk: int
    badge: bool
    check: str
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
    quests: list[QuestOut]


class ClaimIn(BaseModel):
    quest: str = Field(pattern=r"^[a-z_]{1,32}$")


def _catalogue() -> list[QuestOut]:
    return [QuestOut(id=q.id, mbk=q.mbk, badge=q.badge, check=q.check) for q in QUESTS.values()]


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
async def me(user: CurrentUser, session: DbSession, token: TokenDep, quests: QuestsDep, agent: AgentDep):
    state = agent.state()
    claims = await quests.claims_for(session, user)
    out = MeOut(wallet_address=user.wallet_address, quests=[
        QuestOut(id=q.id, mbk=q.mbk, badge=q.badge, check=q.check, eligible=quests.eligible(q, user, state),
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


@router.post("/claim", response_model=ClaimOut, status_code=status.HTTP_201_CREATED)
async def claim(body: ClaimIn, user: CurrentUser, session: DbSession, quests: QuestsDep, agent: AgentDep,
                background: BackgroundTasks):
    try:
        created = await quests.claim(session, user, body.quest, agent.state())
    except QuestError as error:
        raise HTTPException(error.status, {"code": error.code, "message": error.message}) from error
    # Minting takes a few seconds on-chain: answer now, settle after the response.
    background.add_task(quests.settle_by_id, created.id)
    return ClaimOut.from_claim(created)
