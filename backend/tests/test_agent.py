"""The agent loop end to end, with a fake exchange and a fake reviewer."""

import pytest

from app.agent.agent import Review, TradingAgent
from app.agent.executor import PaperExecutor
from app.agent.memory import Memory
from app.agent.state import AgentConfig, AgentState, Portfolio
from app.services.exchange import Candle


class FakeMarket:
    def __init__(self, series: dict[str, list[float]]) -> None:
        self.series = series

    async def ohlcv(self, symbol, timeframe="1h", limit=100):
        return [Candle(time=i, open=v, high=v, low=v, close=v, volume=1.0) for i, v in enumerate(self.series[symbol])]


class VetoReviewer:
    def __init__(self, approve: bool) -> None:
        self.approve = approve
        self.calls = 0

    async def review(self, signal, closes, portfolio):
        self.calls += 1
        return Review(approve=self.approve, confidence=0.9, rationale="fake")


GOLDEN = [100.0] * 29 + [101.0]
DEATH = [100.0] * 29 + [99.0]


def make_agent(tmp_path, market, reviewer=None, use_llm=True):
    initial = AgentState(
        config=AgentConfig(symbols=["BTC/USDT"], strategy="sma_cross", use_llm_review=use_llm),
        portfolio=Portfolio(cash=1000.0),
    )
    return TradingAgent(market, Memory(tmp_path / "state.json", initial), PaperExecutor(), reviewer)


@pytest.mark.asyncio
async def test_buy_then_skip_repeat_then_sell(tmp_path):
    market = FakeMarket({"BTC/USDT": GOLDEN})
    agent = make_agent(tmp_path, market)

    first = await agent.tick()
    assert len(first.trades) == 1 and first.trades[0].side == "buy"
    assert first.decisions[0].executed is True
    assert "BTC/USDT" in agent.state().portfolio.positions

    second = await agent.tick()  # same cross still visible: no second buy
    assert second.trades == []
    assert "ya en posición" in second.decisions[0].reason

    market.series["BTC/USDT"] = DEATH
    third = await agent.tick()
    assert len(third.trades) == 1 and third.trades[0].side == "sell"
    assert agent.state().portfolio.positions == {}
    assert agent.state().ticks == 3


@pytest.mark.asyncio
async def test_sell_without_position_is_recorded_not_executed(tmp_path):
    agent = make_agent(tmp_path, FakeMarket({"BTC/USDT": DEATH}))
    result = await agent.tick()
    assert result.trades == []
    assert result.decisions[0].action == "sell"
    assert "sin posición" in result.decisions[0].reason


@pytest.mark.asyncio
async def test_reviewer_can_veto(tmp_path):
    reviewer = VetoReviewer(approve=False)
    agent = make_agent(tmp_path, FakeMarket({"BTC/USDT": GOLDEN}), reviewer)
    result = await agent.tick()
    assert reviewer.calls == 1
    assert result.trades == []
    assert "veta" in result.decisions[0].review


@pytest.mark.asyncio
async def test_reviewer_is_skipped_when_disabled(tmp_path):
    reviewer = VetoReviewer(approve=False)
    agent = make_agent(tmp_path, FakeMarket({"BTC/USDT": GOLDEN}), reviewer, use_llm=False)
    result = await agent.tick()
    assert reviewer.calls == 0
    assert len(result.trades) == 1


@pytest.mark.asyncio
async def test_state_survives_reload(tmp_path):
    market = FakeMarket({"BTC/USDT": GOLDEN})
    await make_agent(tmp_path, market).tick()
    again = make_agent(tmp_path, market)
    assert again.state().ticks == 1
    assert len(again.state().portfolio.trades) == 1
