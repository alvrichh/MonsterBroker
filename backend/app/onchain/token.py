"""Read-only views of MonsterCoin and the Monster Badges over JSON-RPC.
Hand-encoded eth_call payloads: reading needs no web3.py."""

from __future__ import annotations

import httpx
from eth_utils import keccak, to_checksum_address
from pydantic import BaseModel

from .chains import chain_by_id

TOKEN_DECIMALS = 18
TOKEN_NAME, TOKEN_SYMBOL = "MonsterCoin", "MBK"


def selector(signature: str) -> str:
    return keccak(text=signature)[:4].hex()


def quest_kind(quest_id: str) -> bytes:
    """bytes32 id of a badge kind: keccak256 of the quest id, like the contract tests."""
    return keccak(text=quest_id)


SEL_TOTAL_SUPPLY = selector("totalSupply()")
SEL_CAP = selector("cap()")
SEL_BALANCE_OF = selector("balanceOf(address)")
SEL_TOTAL_MINTED = selector("totalMinted()")
SEL_AWARDED = selector("awarded(bytes32,address)")


def _word(address: str) -> str:
    """An address as a 32-byte ABI word."""
    return address[2:].lower().rjust(64, "0")


class TokenError(Exception):
    pass


class TokenInfo(BaseModel):
    configured: bool
    chain_id: int
    chain_name: str
    explorer: str
    token_address: str | None = None
    badge_address: str | None = None
    name: str = TOKEN_NAME
    symbol: str = TOKEN_SYMBOL
    decimals: int = TOKEN_DECIMALS
    cap: float | None = None
    total_supply: float | None = None
    badges_minted: int | None = None
    error: str | None = None  # the chain could not be read; the rest is still valid


class TokenService:
    def __init__(self, chain_id: int, token_address: str = "", badge_address: str = "", rpc_url: str = "",
                 timeout: float = 10.0) -> None:
        self.chain = chain_by_id(chain_id)
        self.token_address = to_checksum_address(token_address) if token_address else ""
        self.badge_address = to_checksum_address(badge_address) if badge_address else ""
        self.rpc_url = rpc_url or self.chain.public_rpc
        self._timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token_address and self.badge_address)

    async def _call(self, to: str, data: str) -> int:
        """eth_call returning one uint256 (or a bool/address, which decode the same)."""
        if not self.rpc_url:
            raise TokenError("no RPC for this chain; set CHAIN_RPC_URL")
        payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": to, "data": data}, "latest"]}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self.rpc_url, json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as error:
            raise TokenError(f"rpc error: {error}") from error
        if "error" in body:
            raise TokenError(str(body["error"].get("message", body["error"])))
        result = body.get("result") or "0x"
        if len(result) < 3:
            raise TokenError(f"no contract at {to}")
        return int(result, 16)

    async def info(self) -> TokenInfo:
        info = TokenInfo(configured=self.configured, chain_id=self.chain.chain_id, chain_name=self.chain.name,
                         explorer=self.chain.explorer, token_address=self.token_address or None,
                         badge_address=self.badge_address or None)
        if not self.configured:
            return info
        try:
            info.cap = await self._call(self.token_address, "0x" + SEL_CAP) / 10**TOKEN_DECIMALS
            info.total_supply = await self._call(self.token_address, "0x" + SEL_TOTAL_SUPPLY) / 10**TOKEN_DECIMALS
            info.badges_minted = await self._call(self.badge_address, "0x" + SEL_TOTAL_MINTED)
        except TokenError as error:
            info.error = str(error)
        return info

    async def balance_of(self, address: str) -> float:
        wei = await self._call(self.token_address, "0x" + SEL_BALANCE_OF + _word(address))
        return wei / 10**TOKEN_DECIMALS

    async def badges_of(self, address: str) -> int:
        return await self._call(self.badge_address, "0x" + SEL_BALANCE_OF + _word(address))

    async def has_badge(self, quest_id: str, address: str) -> bool:
        data = "0x" + SEL_AWARDED + quest_kind(quest_id).hex() + _word(address)
        return bool(await self._call(self.badge_address, data))
