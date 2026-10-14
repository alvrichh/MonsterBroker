"""Learn-to-earn: the quests catalogue, who may claim what, and the record
of every claim. Minting goes through a Minter when one is configured;
otherwise claims wait as `pending`. Testnet rewards have no value, so
nothing is lost by waiting."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import QuestClaim, User, UserEvent
from app.onchain.rewards import Minter
from app.onchain.token import TOKEN_DECIMALS, quest_kind
from app.services.membership import PRO_DAYS_FOR_QUESTS, SOURCE_QUESTS, grant_pro
from app.utils.helpers import utc_now

STATUS_PENDING, STATUS_MINTED, STATUS_FAILED = "pending", "minted", "failed"

# Events the API records itself when the signed-in user does the thing.
EVENT_BOT_TICK = "bot_tick"
# Events the client reports (reading a page leaves no other trace). The
# rewards are testnet-only, so a self-report is an acceptable proof here.
CLIENT_EVENTS = frozenset({"glossary_read"})


@dataclass(frozen=True, slots=True)
class Quest:
    id: str
    mbk: int  # whole MBK
    badge: bool
    event: str | None  # None = "the account has a wallet"
    title: str  # English, for the on-chain metadata; the UI has its own strings
    description: str


QUESTS: dict[str, Quest] = {
    q.id: q
    for q in (
        Quest("welcome", 10, True, None, "Welcome aboard",
              "Linked a wallet to a MonsterBroker account and signed in without a password."),
        Quest("first_tick", 25, True, EVENT_BOT_TICK, "First tick",
              "Ran a paper-trading tick of the Monster on real Binance candles."),
        Quest("glossary", 15, True, "glossary_read", "Futures glossary",
              "Read the futures glossary: mark price, funding, open interest, basis, liquidation."),
    )
}


class QuestError(Exception):
    def __init__(self, message: str, code: str, status: int = 400) -> None:
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


class ClaimOut(BaseModel):
    id: str
    quest: str
    wallet_address: str
    mbk: int
    status: str
    tx_token: str | None = None
    tx_badge: str | None = None
    error: str | None = None
    created_at: str
    settled_at: str | None = None

    @classmethod
    def from_claim(cls, claim: QuestClaim) -> ClaimOut:
        return cls(
            id=claim.id, quest=claim.quest, wallet_address=claim.wallet_address, mbk=claim.mbk, status=claim.status,
            tx_token=claim.tx_token, tx_badge=claim.tx_badge, error=claim.error,
            created_at=claim.created_at.isoformat() if claim.created_at else "",
            settled_at=claim.settled_at.isoformat() if claim.settled_at else None,
        )


class QuestService:
    def __init__(self, minter: Minter | None, api_base: str, site_base: str, minter_address: str | None = None):
        self.minter = minter
        self.api_base = api_base.rstrip("/")
        self.site_base = site_base.rstrip("/")
        self.minter_address = minter.address if minter else minter_address

    # ---------------------------------------------------------------- catalogue

    def metadata_uri(self, quest_id: str) -> str:
        return f"{self.api_base}/api/token/metadata/{quest_id}"

    def metadata(self, quest_id: str) -> dict:
        """ERC-721 metadata for a badge kind (what explorers and wallets show)."""
        quest = QUESTS[quest_id]
        return {
            "name": f"Monster Badge · {quest.title}",
            "description": quest.description,
            "image": f"{self.site_base}/images/badges/{quest.id}.svg",
            "external_url": f"{self.site_base}/token",
            "attributes": [{"trait_type": "kind", "value": quest.id}, {"trait_type": "mbk", "value": quest.mbk}],
        }

    @staticmethod
    def eligible(quest: Quest, user: User, events: set[str]) -> bool:
        if quest.event is None:
            return bool(user.wallet_address)
        return quest.event in events

    # ------------------------------------------------------------------ events

    @staticmethod
    async def events_for(session: AsyncSession, user_id: str) -> set[str]:
        rows = await session.scalars(select(UserEvent.event).where(UserEvent.user_id == user_id))
        return set(rows)

    @staticmethod
    async def record_event(session: AsyncSession, user_id: str, event: str) -> bool:
        """Remember that the user did `event`. True the first time, False after."""
        query = select(UserEvent.id).where(UserEvent.user_id == user_id, UserEvent.event == event)
        if await session.scalar(query):
            return False
        session.add(UserEvent(id=uuid4().hex[:12], user_id=user_id, event=event, created_at=utc_now()))
        try:
            await session.commit()
        except IntegrityError:  # two requests raced; the other one won
            await session.rollback()
            return False
        return True

    # ------------------------------------------------------------------ claims

    @staticmethod
    async def claims_for(session: AsyncSession, user_id: str) -> dict[str, QuestClaim]:
        rows = await session.scalars(select(QuestClaim).where(QuestClaim.user_id == user_id))
        return {claim.quest: claim for claim in rows}

    async def claim(self, session: AsyncSession, user: User, quest_id: str) -> tuple[QuestClaim, bool]:
        """Record a claim. The second value is True when this claim completed
        every quest, which earns a month of Pro."""
        quest = QUESTS.get(quest_id)
        if quest is None:
            raise QuestError("Ese reto no existe.", "unknown_quest", 404)
        if not user.wallet_address:
            raise QuestError("Vincula una wallet para recibir recompensas.", "no_wallet")
        if not self.eligible(quest, user, await self.events_for(session, user.id)):
            raise QuestError("Todavía no has completado ese reto.", "not_eligible")
        claimed = await self.claims_for(session, user.id)
        if quest_id in claimed:
            raise QuestError("Ese reto ya está reclamado.", "already_claimed", 409)
        claim = QuestClaim(id=uuid4().hex[:12], user_id=user.id, quest=quest_id, wallet_address=user.wallet_address,
                           mbk=quest.mbk, status=STATUS_PENDING, created_at=utc_now())
        session.add(claim)
        completed_all = set(claimed) | {quest_id} >= set(QUESTS)
        if completed_all:
            grant_pro(user, PRO_DAYS_FOR_QUESTS, SOURCE_QUESTS)
        await session.commit()
        await session.refresh(claim)
        return claim, completed_all

    async def settle(self, session: AsyncSession, claim: QuestClaim) -> QuestClaim:
        """Mint what a claim is owed. Each transaction is sent at most once:
        a retry after a failure only sends what is still missing."""
        if self.minter is None or claim.status == STATUS_MINTED:
            return claim
        quest = QUESTS[claim.quest]
        try:
            if claim.tx_token is None:
                claim.tx_token = await self.minter.mint(claim.wallet_address, quest.mbk * 10**TOKEN_DECIMALS)
            if quest.badge and claim.tx_badge is None:
                claim.tx_badge = await self.minter.award(claim.wallet_address, quest_kind(quest.id),
                                                        self.metadata_uri(quest.id))
            claim.status, claim.error, claim.settled_at = STATUS_MINTED, None, utc_now()
        except Exception as error:  # RPC down, no gas, reverted: keep the claim for a retry
            claim.status, claim.error = STATUS_FAILED, str(error)[:500]
        await session.commit()
        return claim

    async def settle_by_id(self, claim_id: str) -> None:
        """For background tasks: a session of its own."""
        from app.db.database import session_factory

        async with session_factory()() as session:
            claim = await session.get(QuestClaim, claim_id)
            if claim:
                await self.settle(session, claim)

    async def settle_pending(self, session: AsyncSession) -> list[QuestClaim]:
        """Retry everything still owed (CLI, after the contracts are deployed)."""
        rows = list(await session.scalars(select(QuestClaim).where(QuestClaim.status != STATUS_MINTED)))
        for claim in rows:
            await self.settle(session, claim)
        return rows
