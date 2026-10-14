"""Where the news radar reads from. All crypto-native, so every story is
relevant; the tags decide how it's filed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    url: str
    homepage: str


SOURCES: tuple[Source, ...] = (
    Source("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss", "https://www.coindesk.com"),
    Source("Cointelegraph", "https://cointelegraph.com/rss", "https://cointelegraph.com"),
    Source("Decrypt", "https://decrypt.co/feed", "https://decrypt.co"),
    Source("The Block", "https://www.theblock.co/rss.xml", "https://www.theblock.co"),
    Source("Bitcoin Magazine", "https://bitcoinmagazine.com/feed", "https://bitcoinmagazine.com"),
    Source("CryptoSlate", "https://cryptoslate.com/feed/", "https://cryptoslate.com"),
    Source("The Defiant", "https://thedefiant.io/api/feed", "https://thedefiant.io"),
    Source("NewsBTC", "https://www.newsbtc.com/feed/", "https://www.newsbtc.com"),
    Source("Ethereum Foundation", "https://blog.ethereum.org/en/feed.xml", "https://blog.ethereum.org"),
)

SOURCE_BY_NAME = {source.name: source for source in SOURCES}
