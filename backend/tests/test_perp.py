"""Paper perpetuals: executor arithmetic (margin, fees, PnL, funding,
liquidation) and the agent's long/short/flip flow with a fake futures feed."""

import pytest

from app.agent.agent import TradingAgent
from app.agent.executor import MAINTENANCE_MARGIN, TAKER_FEE, PaperExecutor, PerpExecutor, liquidation_price
from app.agent.memory import Memory
from app.agent.state import AgentConfig, AgentState, Market, Portfolio, Side
from app.services.exchange import Candle
from app.services.futures import PremiumIndex
from app.strategies import Action
from app.strategies.base import Signal

NOW = "2026-10-14T05:00:00+00:00"


def buy(symbol="BTC/USDT"):
    return Signal(strategy="t", symbol=symbol, action=Action.BUY, confidence=1.0, reason="up")


def sell(symbol="BTC/USDT"):
    return Signal(strategy="t", symbol=symbol, action=Action.SELL, confidence=1.0, reason="down")


# ------------------------------------------------------------------ executor


def test_liquidation_price_sits_one_over_leverage_away():
    assert liquidation_price(Side.LONG, 100.0, 4.0) == pytest.approx(100 * (1 - 0.25 + MAINTENANCE_MARGIN))
    assert liquidation_price(Side.SHORT, 100.0, 4.0) == pytest.approx(100 * (1 + 0.25 - MAINTENANCE_MARGIN))
    assert liquidation_price(Side.LONG, 100.0, 1.0) == pytest.approx(0.5)  # 1x can only die at zero (plus buffer)


def test_open_long_locks_margin_and_charges_the_fee():
    portfolio = Portfolio(cash=1000.0)
    trade = PerpExecutor().open(portfolio, buy(), price=100.0, fraction=0.5, leverage=4.0, now=NOW)
    position = portfolio.perp_positions["BTC/USDT"]
    assert trade.action == "open" and trade.position_side == Side.LONG and trade.leverage == 4.0
    assert position.margin == 500.0 and position.size == pytest.approx(20.0)  # 500 * 4 / 100
    assert trade.fee == pytest.approx(2000 * TAKER_FEE)
    assert portfolio.cash == pytest.approx(1000 - 500 - 0.8)


def test_close_long_with_profit_returns_margin_plus_pnl():
    portfolio = Portfolio(cash=1000.0)
    executor = PerpExecutor()
    executor.open(portfolio, buy(), price=100.0, fraction=0.5, leverage=4.0, now=NOW)
    trade = executor.close(portfolio, "BTC/USDT", price=110.0, now=NOW, strategy="t", reason="tp")
    # 20 contracts * +10 = +200, minus the closing fee on 2200 notional
    assert trade.action == "close" and trade.side == Action.SELL
    assert trade.pnl == pytest.approx(200 - 2200 * TAKER_FEE)
    assert portfolio.cash == pytest.approx(1000 - 0.8 + trade.pnl)
    assert portfolio.perp_positions == {}


def test_short_profits_when_price_falls():
    portfolio = Portfolio(cash=1000.0)
    executor = PerpExecutor()
    executor.open(portfolio, sell(), price=100.0, fraction=0.5, leverage=2.0, now=NOW)
    assert portfolio.perp_positions["BTC/USDT"].side == Side.SHORT
    trade = executor.close(portfolio, "BTC/USDT", price=90.0, now=NOW, strategy="t", reason="tp")
    assert trade.side == Action.BUY
    assert trade.pnl == pytest.approx(10 * 10 - 900 * TAKER_FEE)  # 10 contracts * +10


def test_funding_moves_margin_pro_rata():
    portfolio = Portfolio(cash=1000.0)
    executor = PerpExecutor()
    executor.open(portfolio, buy(), price=100.0, fraction=0.5, leverage=4.0, now=NOW)
    paid = executor.accrue_funding(portfolio, "BTC/USDT", rate=0.0001, hours=4.0, mark=100.0)
    assert paid == pytest.approx(0.0001 * 2000 * 0.5)  # half a funding period on the notional
    position = portfolio.perp_positions["BTC/USDT"]
    assert position.margin == pytest.approx(500 - paid) and position.funding_paid == pytest.approx(paid)

    executor.open(portfolio, sell("ETH/USDT"), price=50.0, fraction=0.2, leverage=1.0, now=NOW)
    received = executor.accrue_funding(portfolio, "ETH/USDT", rate=0.0001, hours=8.0, mark=50.0)
    assert received < 0  # shorts receive positive funding


def test_liquidation_wipes_the_margin():
    portfolio = Portfolio(cash=1000.0)
    executor = PerpExecutor()
    executor.open(portfolio, buy(), price=100.0, fraction=0.5, leverage=4.0, now=NOW)
    position = portfolio.perp_positions["BTC/USDT"]
    assert not executor.is_liquidated(position, low=80.0, high=101.0)
    assert executor.is_liquidated(position, low=75.0, high=101.0)
    trade = executor.close(portfolio, "BTC/USDT", price=74.0, now=NOW, strategy="t", reason="liq", liquidated=True)
    assert trade.action == "liquidation" and trade.pnl == -500.0 and trade.price == position.liquidation_price
    assert portfolio.cash == pytest.approx(1000 - 500 - 0.8)  # nothing comes back


def test_equity_values_perps_at_mark():
    portfolio = Portfolio(cash=1000.0)
    PerpExecutor().open(portfolio, buy(), price=100.0, fraction=0.5, leverage=4.0, now=NOW)
    assert portfolio.equity({"BTC/USDT": 105.0}) == pytest.approx(1000 - 0.8 + 100)  # +5 * 20 contracts


# --------------------------------------------------------------------- agent


class FakeFutures:
    def __init__(self, series: dict[str, list[float]], funding: float = 0.0, mark: float | None = None) -> None:
        self.series, self.funding, self.mark = series, funding, mark

    async def klines(self, symbol, interval="1h", limit=100):
        base = symbol.replace("USDT", "") + "/USDT"
        return [Candle(time=i, open=v, high=v, low=v, close=v, volume=1.0) for i, v in enumerate(self.series[base])]

    async def premium(self, symbol):
        base = symbol.replace("USDT", "") + "/USDT"
        price = self.mark or self.series[base][-1]
        return PremiumIndex(symbol=symbol, mark_price=price, index_price=price, funding_rate=self.funding,
                            funding_annualized=self.funding * 1095, next_funding_time=0, time=0)


class FakeSpot:
    async def ohlcv(self, symbol, timeframe="1h", limit=100):
        return [Candle(time=0, open=100, high=100, low=100, close=100, volume=1.0)]


GOLDEN = [100.0] * 29 + [101.0]
DEATH = [100.0] * 29 + [99.0]


def make_agent(tmp_path, futures, **config):
    settings = {"symbols": ["BTC/USDT"], "strategy": "sma_cross", "use_llm_review": False, "market": Market.PERP,
                "leverage": 3.0, **config}
    initial = AgentState(config=AgentConfig(**settings), portfolio=Portfolio(cash=1000.0))
    return TradingAgent(FakeSpot(), Memory(tmp_path / "state.json", initial), PaperExecutor(), futures=futures)


@pytest.mark.asyncio
async def test_perp_long_then_flip_to_short(tmp_path):
    futures = FakeFutures({"BTC/USDT": GOLDEN})
    agent = make_agent(tmp_path, futures)

    first = await agent.tick()
    assert [t.action for t in first.trades] == ["open"]
    position = agent.state().portfolio.perp_positions["BTC/USDT"]
    assert position.side == Side.LONG and position.leverage == 3.0

    again = await agent.tick()  # same cross: stays long
    assert again.trades == [] and "ya en largo" in again.decisions[0].reason

    futures.series["BTC/USDT"] = DEATH
    flipped = await agent.tick()
    assert [t.action for t in flipped.trades] == ["close", "open"]
    assert agent.state().portfolio.perp_positions["BTC/USDT"].side == Side.SHORT


@pytest.mark.asyncio
async def test_perp_sell_only_closes_when_shorts_are_off(tmp_path):
    futures = FakeFutures({"BTC/USDT": GOLDEN})
    agent = make_agent(tmp_path, futures, allow_shorts=False)
    await agent.tick()
    futures.series["BTC/USDT"] = DEATH
    result = await agent.tick()
    assert [t.action for t in result.trades] == ["close"]
    assert agent.state().portfolio.perp_positions == {}

    nothing = await agent.tick()
    assert nothing.trades == [] and "cortos desactivados" in nothing.decisions[0].reason


@pytest.mark.asyncio
async def test_perp_liquidation_on_a_crash_candle(tmp_path):
    futures = FakeFutures({"BTC/USDT": GOLDEN})
    agent = make_agent(tmp_path, futures, leverage=10.0)
    await agent.tick()
    liq = agent.state().portfolio.perp_positions["BTC/USDT"].liquidation_price
    assert liq == pytest.approx(101 * (1 - 0.1 + MAINTENANCE_MARGIN))

    # Next candle gaps well below the liquidation level.
    futures.series["BTC/USDT"] = GOLDEN + [80.0]
    futures.mark = 80.0
    result = await agent.tick()
    assert result.trades[0].action == "liquidation" and result.trades[0].pnl == -250.0
    # The crash is also a death cross, so a fresh short may follow; the long is gone either way.
    assert all(p.side == Side.SHORT for p in agent.state().portfolio.perp_positions.values())
    assert any("liquidación" in d.reason for d in agent.state().decisions)


@pytest.mark.asyncio
async def test_perp_funding_is_charged_between_ticks(tmp_path):
    futures = FakeFutures({"BTC/USDT": GOLDEN}, funding=0.001)
    agent = make_agent(tmp_path, futures)
    await agent.tick()
    state = agent.state()
    state.last_tick = "2026-01-01T00:00:00+00:00"  # pretend the last tick was long ago (capped at a week)
    agent.memory.save(state)
    await agent.tick()
    position = agent.state().portfolio.perp_positions["BTC/USDT"]
    assert position.funding_paid > 0 and position.margin < 250.0


def test_config_rejects_bad_market_and_leverage(tmp_path):
    agent = make_agent(tmp_path, FakeFutures({"BTC/USDT": GOLDEN}))
    with pytest.raises(ValueError):
        agent.update_config(market="options")
    with pytest.raises(ValueError):
        agent.update_config(leverage=50)
    state = agent.update_config(market="spot", leverage=5)
    assert state.config.market == Market.SPOT and state.config.leverage == 5.0
