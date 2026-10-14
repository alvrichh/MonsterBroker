"""EVM chains the wallet routes understand. The RPC comes from settings; the
public ones here are fallbacks for reading balances only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chain:
    id: str
    name: str
    chain_id: int
    symbol: str
    explorer: str
    public_rpc: str


CHAINS: dict[str, Chain] = {
    c.id: c
    for c in (
        Chain("ethereum", "Ethereum", 1, "ETH", "https://etherscan.io", "https://ethereum-rpc.publicnode.com"),
        Chain("polygon", "Polygon", 137, "POL", "https://polygonscan.com", "https://polygon-bor-rpc.publicnode.com"),
        Chain("arbitrum", "Arbitrum One", 42161, "ETH", "https://arbiscan.io", "https://arbitrum-one-rpc.publicnode.com"),
        Chain("base", "Base", 8453, "ETH", "https://basescan.org", "https://base-rpc.publicnode.com"),
        Chain("base_sepolia", "Base Sepolia", 84532, "ETH", "https://sepolia.basescan.org", "https://sepolia.base.org"),
        Chain("bsc", "BNB Smart Chain", 56, "BNB", "https://bscscan.com", "https://bsc-rpc.publicnode.com"),
    )
}


def chain_by_id(chain_id: int) -> Chain:
    """The chain our contracts live on. An id we don't list still works if
    CHAIN_RPC_URL is set; it just has no explorer links."""
    for chain in CHAINS.values():
        if chain.chain_id == chain_id:
            return chain
    return Chain(f"chain-{chain_id}", f"Chain {chain_id}", chain_id, "ETH", "", "")
