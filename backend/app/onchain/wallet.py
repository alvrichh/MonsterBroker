"""Read-only wallet queries over JSON-RPC. Uses plain httpx so it works
without web3.py; web3.py is only needed later for signing."""

from __future__ import annotations

import re

import httpx
from pydantic import BaseModel

from .chains import CHAINS, Chain

_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


class WalletError(Exception):
    pass


class Balance(BaseModel):
    address: str
    chain: str
    symbol: str
    balance: float
    wei: str
    explorer_url: str


def is_address(value: str) -> bool:
    return bool(_ADDRESS.match(value or ""))


class WalletService:
    def __init__(self, rpc_url: str = "", timeout: float = 10.0) -> None:
        self._rpc_url = rpc_url
        self._timeout = timeout

    def chain(self, chain_id: str) -> Chain:
        try:
            return CHAINS[chain_id]
        except KeyError as error:
            raise WalletError(f"unknown chain {chain_id!r}; available: {', '.join(CHAINS)}") from error

    def rpc_for(self, chain: Chain) -> str:
        # A configured RPC is assumed to be Ethereum mainnet unless the user
        # asks for another chain, which falls back to a public node.
        if self._rpc_url and chain.id == "ethereum":
            return self._rpc_url
        return chain.public_rpc

    async def balance(self, address: str, chain_id: str = "ethereum") -> Balance:
        if not is_address(address):
            raise WalletError("invalid EVM address")
        chain = self.chain(chain_id)
        payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [address, "latest"]}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self.rpc_for(chain), json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as error:
            raise WalletError(f"rpc error: {error}") from error
        if "error" in data:
            raise WalletError(str(data["error"].get("message", data["error"])))
        wei = int(data["result"], 16)
        return Balance(address=address, chain=chain.id, symbol=chain.symbol, balance=wei / 1e18, wei=str(wei),
                       explorer_url=f"{chain.explorer}/address/{address}")
