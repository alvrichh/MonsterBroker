"""Token info, badge metadata and the learn-to-earn claims, with and
without a minter. No chain is touched: the contracts are not configured
and the minter is a fake."""

from tests.conftest import register_and_verify, wallet_sign_in

TX_MINT, TX_AWARD = "0x" + "11" * 32, "0x" + "22" * 32


class FakeMinter:
    address = "0x" + "ab" * 20

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def mint(self, to, amount_wei):
        self.calls.append(("mint", to, amount_wei))
        return TX_MINT

    async def award(self, to, kind, uri):
        self.calls.append(("award", to, kind, uri))
        return TX_AWARD


def _quest(me: dict, quest_id: str) -> dict:
    return next(q for q in me["quests"] if q["id"] == quest_id)


def test_info_without_contracts(client):
    data = client.get("/api/token/info").json()
    assert data["configured"] is False and data["chain_id"] == 84532 and data["chain_name"] == "Base Sepolia"
    assert data["symbol"] == "MBK" and data["cap"] is None and data["minter_address"] is None
    assert [q["id"] for q in data["quests"]] == ["welcome", "first_tick", "glossary"]
    assert data["explorer"] == "https://sepolia.basescan.org"


def test_badge_metadata(client):
    data = client.get("/api/token/metadata/first_tick").json()
    assert data["name"] == "Monster Badge · First tick"
    assert data["image"] == "http://test/images/badges/first_tick.svg"
    assert {"trait_type": "kind", "value": "first_tick"} in data["attributes"]
    assert client.get("/api/token/metadata/nope").status_code == 404


def test_claim_needs_a_session_and_a_wallet(client):
    assert client.post("/api/token/claim", json={"quest": "welcome"}).status_code == 401
    headers = {"Authorization": f"Bearer {register_and_verify(client)}"}
    response = client.post("/api/token/claim", json={"quest": "welcome"}, headers=headers)
    assert response.status_code == 400 and response.json()["detail"]["code"] == "no_wallet"
    me = client.get("/api/token/me", headers=headers).json()
    assert me["wallet_address"] is None and _quest(me, "welcome")["eligible"] is False


def test_claims_wait_without_a_minter(client):
    token, address = wallet_sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/api/token/claim", json={"quest": "welcome"}, headers=headers)
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending" and created.json()["wallet_address"] == address
    assert created.json()["mbk"] == 10

    again = client.post("/api/token/claim", json={"quest": "welcome"}, headers=headers)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "already_claimed"

    me = client.get("/api/token/me", headers=headers).json()
    assert me["balance_mbk"] is None  # contracts not deployed: nothing to read
    assert _quest(me, "welcome")["claim"]["status"] == "pending"
    assert _quest(me, "first_tick")["eligible"] is False and _quest(me, "first_tick")["claim"] is None
    assert _quest(me, "glossary")["eligible"] is True

    early = client.post("/api/token/claim", json={"quest": "first_tick"}, headers=headers)
    assert early.status_code == 400 and early.json()["detail"]["code"] == "not_eligible"
    assert client.post("/api/token/claim", json={"quest": "nope"}, headers=headers).status_code == 404


def test_claims_mint_with_a_minter(client, settings_env):
    from app.api import deps

    fake = FakeMinter()
    deps.get_quests(settings_env).minter = fake
    agent = deps.get_agent(settings_env)
    state = agent.state()
    state.ticks = 1  # the Monster has run once
    agent.memory.save(state)

    token, address = wallet_sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/token/claim", json={"quest": "first_tick"}, headers=headers)
    assert created.status_code == 201, created.text

    # TestClient runs the background task before answering, so it is settled already.
    me = client.get("/api/token/me", headers=headers).json()
    claim = _quest(me, "first_tick")["claim"]
    assert claim["status"] == "minted" and claim["tx_token"] == TX_MINT and claim["tx_badge"] == TX_AWARD
    assert fake.calls[0] == ("mint", address, 25 * 10**18)
    kind, uri = fake.calls[1][2], fake.calls[1][3]
    assert fake.calls[1][:2] == ("award", address) and len(kind) == 32
    assert uri == "http://127.0.0.1:8000/api/token/metadata/first_tick"


def test_failed_claim_retries_only_what_is_missing(client, settings_env):
    import asyncio

    from app.api import deps
    from app.db.models import QuestClaim

    class FlakyMinter(FakeMinter):
        async def award(self, to, kind, uri):
            if len(self.calls) == 1:  # first award fails after the mint went through
                self.calls.append(("award-failed",))
                raise RuntimeError("rpc down")
            return await super().award(to, kind, uri)

    flaky = FlakyMinter()
    quests = deps.get_quests(settings_env)
    quests.minter = flaky
    token, _ = wallet_sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/token/claim", json={"quest": "welcome"}, headers=headers)

    me = client.get("/api/token/me", headers=headers).json()
    claim = _quest(me, "welcome")["claim"]
    assert claim["status"] == "failed" and claim["tx_token"] == TX_MINT and claim["tx_badge"] is None
    assert "rpc down" in claim["error"]

    async def retry():
        from app.db.database import session_factory

        async with session_factory()() as session:
            await quests.settle_pending(session)
            return (await session.get(QuestClaim, claim["id"])).status

    assert asyncio.run(retry()) == "minted"
    assert [c[0] for c in flaky.calls] == ["mint", "award-failed", "award"]  # no second mint
