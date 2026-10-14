"""The market routes against a fake exchange, so response shapes are checked
without the network (the ohlcv route once 500'd on dataclass candles)."""

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_market
from app.services.exchange import Candle, MarketDataError, Ticker


class FakeMarket:
    async def ticker(self, symbol):
        if symbol == "BAD/USDT":
            raise MarketDataError("unknown symbol")
        return Ticker(symbol=symbol, price=100.0, change_24h=1.5, high_24h=101.0, low_24h=99.0, volume_24h=1e6)

    async def tickers(self, symbols):
        out = []
        for s in symbols:
            try:
                out.append(await self.ticker(s))
            except MarketDataError:
                pass
        return out

    async def ohlcv(self, symbol, timeframe="1h", limit=100):
        if symbol == "BAD/USDT":
            raise MarketDataError("unknown symbol")
        return [Candle(time=1_700_000_000_000 + i * 3_600_000, open=100 + i, high=101 + i, low=99 + i, close=100.5 + i,
                       volume=10.0) for i in range(limit)]


@pytest.fixture
def market_client(settings_env):
    from main import create_app

    app = create_app()
    app.dependency_overrides[get_market] = lambda: FakeMarket()
    with TestClient(app) as client:
        yield client


def test_ohlcv_returns_candles(market_client):
    data = market_client.get("/api/market/ohlcv", params={"symbol": "btc/usdt", "limit": 12}).json()
    assert data["symbol"] == "BTC/USDT" and data["timeframe"] == "1h"
    assert len(data["candles"]) == 12
    assert set(data["candles"][0]) == {"time", "open", "high", "low", "close", "volume"}


def test_ohlcv_unknown_symbol_is_502(market_client):
    assert market_client.get("/api/market/ohlcv", params={"symbol": "BAD/USDT"}).status_code == 502


def test_ohlcv_rejects_bad_symbol_format(market_client):
    assert market_client.get("/api/market/ohlcv", params={"symbol": "BTCUSDT"}).status_code == 422


def test_indicators_snapshot(market_client):
    data = market_client.get("/api/market/indicators", params={"symbol": "ETH/USDT", "limit": 60}).json()
    assert data["candles"] == 60
    assert data["values"]["price"] == 100.5 + 59
    assert data["values"]["rsi_14"] == 100.0  # straight climb


def test_tickers_skip_failures(market_client):
    data = market_client.get("/api/market/tickers", params={"symbols": "BTC/USDT,BAD/USDT"}).json()
    assert [t["symbol"] for t in data] == ["BTC/USDT"]
