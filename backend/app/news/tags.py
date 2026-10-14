"""Topic tags for news stories. Word-bounded regexes so "sec" doesn't match
"second" and "eth" doesn't match "ethics"."""

from __future__ import annotations

import re

TAG_RULES: tuple[tuple[str, str], ...] = (
    ("Bitcoin", r"bitcoin|btc|satoshi|halving|lightning network|ordinals"),
    ("Ethereum", r"ethereum|eth|ether|vitalik|evm|erc-?20|erc-?721"),
    ("DeFi", r"defi|yield|liquidity|dex|uniswap|aave|curve|lending|staking|restaking|tvl"),
    ("Stablecoins", r"stablecoins?|usdt|usdc|tether|circle|dai|frax"),
    ("Regulation", r"sec|regulat\w*|lawsuit|congress|senate|mica|etfs?|legislat\w*|court|cftc|treasury|ban"),
    ("Exchanges", r"binance|coinbase|kraken|okx|bybit|bitget|exchanges?|listing|delist\w*"),
    ("Altcoins", r"solana|sol|xrp|ripple|cardano|ada|dogecoin|doge|altcoins?|avalanche|avax|polkadot|litecoin|ltc"
                 r"|bnb|tron|ton|sui|aptos"),
    ("Layer 2", r"layer[- ]?2|l2s?|rollups?|arbitrum|optimism|base|zk\w*|polygon|starknet"),
    ("NFT & Gaming", r"nfts?|metaverse|gaming|play-to-earn|opensea|collectibles?"),
    ("Security", r"hack\w*|exploit\w*|phishing|drained|breach|scam\w*|rug ?pull|stolen|attack\w*"),
    ("Web3", r"web3|daos?|wallets?|identity|decentrali[sz]\w*|protocol|on-?chain"),
    ("Markets", r"price|rally|crash|bull\w*|bear\w*|markets?|liquidations?|volatility|trading|futures|options"
                r"|whales?|ath"),
    ("AI", r"ai|artificial intelligence|agents?|llms?|machine learning"),
)

_COMPILED = tuple((tag, re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)) for tag, pattern in TAG_RULES)

ALL_TAGS = tuple(tag for tag, _ in TAG_RULES) + ("Crypto",)
MAX_TAGS = 4


def get_tags(title: str, summary: str = "") -> list[str]:
    haystack = f"{title} {summary}"
    tags = [tag for tag, pattern in _COMPILED if pattern.search(haystack)]
    return tags[:MAX_TAGS] if tags else ["Crypto"]
