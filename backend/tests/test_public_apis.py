"""Parsers for the public data APIs, fed with payloads shaped like the real
ones, and the TTL cache they sit behind."""

import pytest

from app.services.coingecko import CoinRow, parse_coins, parse_global, sane_volume
from app.services.defillama import parse_chains, parse_history, parse_protocols
from app.services.sentiment import parse_fng
from app.utils.cache import TTLCache

GLOBAL = {"data": {
    "active_cryptocurrencies": 22230, "markets": 1510,
    "total_market_cap": {"usd": 2.8e12, "btc": 33950675.5},
    "total_volume": {"usd": 9.1e10},
    "market_cap_percentage": {"btc": 59.9, "eth": 10.9},
    "market_cap_change_percentage_24h_usd": 1.23, "updated_at": 1791936000,
}}

COINS = [{
    "id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "image": "https://img/btc.png",
    "current_price": 83680, "market_cap": 1681804921450, "market_cap_rank": 1, "total_volume": 3.2e10,
    "price_change_percentage_24h_in_currency": 1.16, "price_change_percentage_7d_in_currency": -1.12,
    "sparkline_in_7d": {"price": [float(i) for i in range(168)]},
}, {
    "id": "x", "symbol": "x", "name": "X", "current_price": None, "sparkline_in_7d": None,
}]

FNG = {"data": [
    {"value": "62", "value_classification": "Greed", "timestamp": "1791936000", "time_until_update": "74304"},
    {"value": "57", "value_classification": "Greed", "timestamp": "1791849600"},
    {"value": "69", "value_classification": "Greed", "timestamp": "1791763200"},
]}

CHAINS = [
    {"name": "Base", "tvl": 6.21e9, "tokenSymbol": None, "gecko_id": None},
    {"name": "Ethereum", "tvl": 51.01e9, "tokenSymbol": "ETH", "gecko_id": "ethereum"},
    {"name": "Empty", "tvl": 0},
]

PROTOCOLS = [
    {"name": "Binance CEX", "slug": "binance-cex", "category": "CEX", "tvl": 1.7e11},
    {"name": "Aave", "slug": "aave", "category": "Lending", "chain": "Multi-Chain", "tvl": 3.0e10,
     "change_1d": 0.5, "change_7d": -2.0, "logo": "https://icons/aave", "url": "https://aave.com"},
    {"name": "Lido", "slug": "lido", "category": "Liquid Staking", "tvl": 2.5e10},
]


def test_parse_global():
    metrics = parse_global(GLOBAL)
    assert metrics.total_market_cap == 2.8e12
    assert metrics.btc_dominance == 59.9
    assert metrics.market_cap_change_24h == 1.23


def test_parse_coins_thins_sparkline_and_tolerates_gaps():
    coins = parse_coins(COINS)
    assert coins[0].symbol == "BTC" and coins[0].rank == 1
    assert len(coins[0].sparkline_7d) == 42
    assert coins[1].price is None and coins[1].sparkline_7d == []


def test_sane_volume_drops_glitches_but_keeps_stablecoins():
    coins = [
        CoinRow(id="btc", symbol="BTC", name="Bitcoin", price=83_000, market_cap=1.68e12, volume_24h=1.04e12),  # glitch
        CoinRow(id="eth", symbol="ETH", name="Ethereum", price=2_500, market_cap=3.0e11, volume_24h=2.0e10),
        CoinRow(id="usdt", symbol="USDT", name="Tether", price=0.999, market_cap=1.8e11, volume_24h=1.2e11),  # ok
        CoinRow(id="x", symbol="X", name="X", price=1.5, market_cap=None, volume_24h=5.0e8),
    ]
    assert sane_volume(coins) == 2.0e10 + 1.2e11 + 5.0e8


def test_parse_fng_history_is_oldest_first():
    fng = parse_fng(FNG)
    assert fng.value == 62 and fng.classification == "Greed"
    assert [p.value for p in fng.history] == [69, 57, 62]
    assert fng.history[-1].date == "2026-10-14"


def test_parse_fng_rejects_empty():
    with pytest.raises(ValueError):
        parse_fng({"data": []})


def test_parse_chains_sorts_and_drops_empty():
    chains = parse_chains(CHAINS, limit=5)
    assert [c.name for c in chains] == ["Ethereum", "Base"]


def test_parse_protocols_excludes_cex_and_sorts():
    protocols = parse_protocols(PROTOCOLS, limit=5)
    assert [p.name for p in protocols] == ["Aave", "Lido"]
    assert protocols[0].change_7d == -2.0


def test_parse_history_keeps_last_days():
    rows = [{"date": 1791936000 - 86400 * i, "tvl": 1e9 + i} for i in range(10)][::-1]
    points = parse_history(rows, days=3)
    assert len(points) == 3 and points[-1].date == "2026-10-14"


@pytest.mark.asyncio
async def test_cache_serves_within_ttl_and_stale_on_error():
    cache = TTLCache()
    calls = {"n": 0}

    async def fetch():
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("upstream down")
        return "fresh"

    assert await cache.get_or_fetch("k", 60, fetch) == "fresh"
    assert await cache.get_or_fetch("k", 60, fetch) == "fresh"  # cached, no call
    assert calls["n"] == 1

    cache._store["k"] = (0, "fresh")  # expire it
    assert await cache.get_or_fetch("k", 60, fetch) == "fresh"  # fetch fails → stale served
    assert calls["n"] == 2
