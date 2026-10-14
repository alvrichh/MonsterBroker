"""The backend is the only minter: it turns a claimed quest into MBK and a
badge on-chain. web3.py is imported lazily; without MINTER_PRIVATE_KEY the
app has no minter and claims simply wait."""

from __future__ import annotations

from typing import Protocol

from eth_account import Account
from eth_utils import to_checksum_address

TOKEN_ABI = [{
    "name": "mint", "type": "function", "stateMutability": "nonpayable",
    "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [],
}]
BADGE_ABI = [{
    "name": "award", "type": "function", "stateMutability": "nonpayable",
    "inputs": [{"name": "to", "type": "address"}, {"name": "kind", "type": "bytes32"},
               {"name": "uri", "type": "string"}],
    "outputs": [{"name": "", "type": "uint256"}],
}]


class RewardsError(Exception):
    pass


class Minter(Protocol):
    address: str

    async def mint(self, to: str, amount_wei: int) -> str: ...

    async def award(self, to: str, kind: bytes, uri: str) -> str: ...


class Web3Minter:
    """Signs and sends with the MINTER_ROLE wallet; returns transaction hashes."""

    def __init__(self, rpc_url: str, chain_id: int, token_address: str, badge_address: str, private_key: str) -> None:
        from web3 import AsyncHTTPProvider, AsyncWeb3

        self.chain_id = chain_id
        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.token = self.w3.eth.contract(address=to_checksum_address(token_address), abi=TOKEN_ABI)
        self.badge = self.w3.eth.contract(address=to_checksum_address(badge_address), abi=BADGE_ABI)

    async def _send(self, call) -> str:
        nonce = await self.w3.eth.get_transaction_count(self.address, "pending")
        tx = await call.build_transaction({"from": self.address, "nonce": nonce, "chainId": self.chain_id})
        signed = self.account.sign_transaction(tx)
        tx_hash = await self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt["status"] != 1:
            raise RewardsError(f"transaction {self.w3.to_hex(tx_hash)} reverted")
        return self.w3.to_hex(tx_hash)

    async def mint(self, to: str, amount_wei: int) -> str:
        return await self._send(self.token.functions.mint(to_checksum_address(to), amount_wei))

    async def award(self, to: str, kind: bytes, uri: str) -> str:
        return await self._send(self.badge.functions.award(to_checksum_address(to), kind, uri))


def minter_address(private_key: str) -> str | None:
    """The address a key controls: what to pass as MINTER when deploying."""
    return Account.from_key(private_key).address if private_key else None
