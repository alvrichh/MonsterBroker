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
        Chain("bsc", "BNB Smart Chain", 56, "BNB", "https://bscscan.com", "https://bsc-rpc.publicnode.com"),
    )
}
