"""Bybit spot parser and the Binance → Bybit switch for spot market data
when Binance refuses the host (Render's addresses get HTTP 418)."""

import asyncio

import pytest

from app.services.exchange import MarketDataError, ResilientMarket, Ticker
from app.services.exchange_bybit import parse_bybit_spot_ticker

SPOT_TICKER = {
    "symbol": "BTCUSDT", "lastPrice": "80847.1", "price24hPcnt": "-0.0322", "highPrice24h": "84100",
    "lowPrice24h": "80100", "turnover24h": "1200000000", "volume24h": "14800",
}


def test_spot_ticker_parser():
    ticker = parse_bybit_spot_ticker("BTC/USDT", SPOT_TICKER)
    assert ticker.symbol == "BTC/USDT" and ticker.price == 80847.1
    assert ticker.change_24h == pytest.approx(-3.22) and ticker.volume_24h == 1200000000


class FakeMarket:
    def __init__(self, provider: str, fail_with: str | None = None) -> None:
        self.provider, self.fail_with, self.calls = provider, fail_with, 0

    async def ticker(self, symbol):
        self.calls += 1
        if self.fail_with:
            raise MarketDataError(f"/ticker/24hr: {self.fail_with}")
        return Ticker(symbol=symbol, price=1.0, change_24h=0.0, high_24h=1.0, low_24h=1.0, volume_24h=1.0)

    async def ohlcv(self, symbol, timeframe="1h", limit=100):
        self.calls += 1
        if self.fail_with:
            raise MarketDataError(f"/klines: {self.fail_with}")
        return [self.provider]


def test_ban_switches_to_fallback_and_sticks():
    primary, fallback = FakeMarket("binance", "HTTP 418"), FakeMarket("bybit")
    market = ResilientMarket(primary, fallback)

    assert asyncio.run(market.ohlcv("BTC/USDT")) == ["bybit"]
    assert market.provider == "bybit"
    asyncio.run(market.ohlcv("BTC/USDT"))
    assert primary.calls == 1  # not retried during the cooldown


def test_tickers_see_the_ban():
    market = ResilientMarket(FakeMarket("binance", "HTTP 451"), FakeMarket("bybit"))
    tickers = asyncio.run(market.tickers(["BTC/USDT", "ETH/USDT"]))
    assert [t.symbol for t in tickers] == ["BTC/USDT", "ETH/USDT"]


def test_other_errors_do_not_switch():
    primary, fallback = FakeMarket("binance", "HTTP 400"), FakeMarket("bybit")
    market = ResilientMarket(primary, fallback)
    with pytest.raises(MarketDataError):
        asyncio.run(market.ohlcv("NOPE/USDT"))
    assert fallback.calls == 0 and market.provider == "binance"
