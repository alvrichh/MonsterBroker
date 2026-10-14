"""Bybit parsers (payloads shaped like the real v5 answers) and the
Binance → Bybit switch when Binance refuses the host."""

import asyncio

import pytest

from app.services.futures import ResilientFutures
from app.services.futures_bybit import (
    BybitFuturesService,
    parse_bybit_funding,
    parse_bybit_klines,
    parse_bybit_oi,
    parse_bybit_premium,
    parse_bybit_ratio,
    parse_bybit_ticker,
)
from app.services.http import UpstreamError

TICKER = {
    "symbol": "BTCUSDT", "lastPrice": "82000.5", "markPrice": "82001.0", "indexPrice": "81990.0",
    "fundingRate": "0.0001", "nextFundingTime": "1792022400000", "openInterest": "92130.5",
    "openInterestValue": "7550000000", "turnover24h": "11400000000", "volume24h": "139000",
    "price24hPcnt": "-0.0215", "highPrice24h": "84146.7", "lowPrice24h": "81588.8",
}


def test_parsers():
    premium = parse_bybit_premium(TICKER, now_ms=1)
    assert premium.mark_price == 82001.0 and premium.funding_rate == 0.0001 and premium.time == 1
    assert premium.funding_annualized == pytest.approx(0.0001 * 3 * 365)

    ticker = parse_bybit_ticker(TICKER)
    assert ticker.change_24h == pytest.approx(-2.15) and ticker.volume_24h == 11400000000

    funding = parse_bybit_funding([{"fundingRateTimestamp": "200", "fundingRate": "0.0002"},
                                  {"fundingRateTimestamp": "100", "fundingRate": "0.0001"}])
    assert [p.time for p in funding] == [100, 200]  # ascending, like Binance's

    oi = parse_bybit_oi([{"timestamp": "2", "openInterest": "10"}, {"timestamp": "1", "openInterest": "8"}], 100.0)
    assert [(p.time, p.contracts, p.value) for p in oi] == [(1, 8.0, 800.0), (2, 10.0, 1000.0)]

    ratio = parse_bybit_ratio([{"timestamp": "1", "buyRatio": "0.6", "sellRatio": "0.4"}])
    assert ratio[0].long == 0.6 and ratio[0].ratio == 1.5

    candles = parse_bybit_klines([["2000", "1", "2", "0.5", "1.5", "10", "15"], ["1000", "1", "1", "1", "1", "5", "5"]])
    assert [c.time for c in candles] == [1000, 2000] and candles[1].close == 1.5


class FakeFutures:
    provider = "fake"

    def __init__(self, fail_with: str | None = None) -> None:
        self.fail_with, self.calls = fail_with, 0

    async def premium(self, symbol):
        self.calls += 1
        if self.fail_with:
            raise UpstreamError(f"https://x/premium: {self.fail_with}")
        return f"{self.provider}:{symbol}"

    async def close(self):
        pass


def test_switches_to_the_fallback_when_blocked():
    binance, bybit = FakeFutures(fail_with="HTTP 418"), FakeFutures()
    bybit.provider = "bybit"
    futures = ResilientFutures(binance, bybit, cooldown=600)
    assert futures.provider == "fake"

    assert asyncio.run(futures.premium("BTCUSDT")) == "bybit:BTCUSDT"
    assert futures.blocked and futures.provider == "bybit"
    assert asyncio.run(futures.premium("ETHUSDT")) == "bybit:ETHUSDT"
    assert binance.calls == 1  # not retried while blocked

    futures._blocked_until = 0  # cooldown over: Binance gets another chance
    binance.fail_with = None
    assert asyncio.run(futures.premium("BTCUSDT")) == "fake:BTCUSDT" and not futures.blocked


def test_other_errors_and_no_fallback_propagate():
    binance = FakeFutures(fail_with="HTTP 500")
    futures = ResilientFutures(binance, FakeFutures())
    with pytest.raises(UpstreamError):
        asyncio.run(futures.premium("BTCUSDT"))
    assert not futures.blocked

    alone = ResilientFutures(FakeFutures(fail_with="HTTP 418"), None)
    with pytest.raises(UpstreamError):
        asyncio.run(alone.premium("BTCUSDT"))


def test_bybit_overview_from_canned_payloads(monkeypatch):
    service = BybitFuturesService()
    payloads = {
        "/v5/market/tickers": {"retCode": 0, "result": {"list": [TICKER]}},
        "/v5/market/account-ratio": {"retCode": 0, "result": {"list": [
            {"timestamp": "1", "buyRatio": "0.58", "sellRatio": "0.42"},
        ]}},
    }

    async def fake_get(path, **params):
        return payloads[path]

    monkeypatch.setattr(service, "get", fake_get)
    overview = asyncio.run(service.overview("BTCUSDT"))
    assert overview.provider == "bybit" and overview.index.mark_price == 82001.0
    assert overview.open_interest == 92130.5 and overview.ticker.last_price == 82000.5
    assert overview.long_short.long == 0.58 and overview.top_traders is None and overview.taker is None
    assert asyncio.run(service.quarterly()) == []

    bad = BybitFuturesService()

    async def refused(path, **params):
        return {"retCode": 10001, "retMsg": "params error"}

    monkeypatch.setattr(bad, "get", refused)
    with pytest.raises(UpstreamError):
        asyncio.run(bad.premium("ETHUSDT"))  # BTCUSDT is cached from above; the cache is shared
