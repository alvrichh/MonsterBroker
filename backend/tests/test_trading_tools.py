"""Exits, sizing, risk limits and the Time Machine: the pure tools first, then
the agent using them, then the route. Ported from day-trader-skill's tools
to crypto; the numbers here are made up so each one can be checked by hand."""

import pytest

from app.agent.agent import TradingAgent
from app.agent.executor import PaperExecutor
from app.agent.memory import Memory
from app.agent.state import AgentConfig, AgentState, Market, Portfolio
from app.services.exchange import Candle
from app.services.timemachine import TimeMachineError, run_time_machine
from app.strategies import get_strategy
from app.tools.exits import atr, exit_hit, plan_exit
from app.tools.risk import EntryCheck, check_entry
from app.tools.sizing import units_for_risk
from app.tools.timemachine import PastEntry, build_pool, history_replay, simulate, slots_of, verdict

# ------------------------------------------------------------------ exits


def test_atr_is_the_average_true_range():
    highs, lows, closes = [11, 12, 13, 14], [9, 10, 11, 12], [10, 11, 12, 13]
    assert atr(highs, lows, closes, period=3) == pytest.approx(2.0)
    assert atr(highs, lows, closes, period=4) is None  # needs period + 1 bars


def test_atr_counts_gaps():
    # the second bar gaps up: its true range runs from the previous close
    assert atr([10, 20], [9, 19], [10, 20], period=1) == pytest.approx(10.0)


def test_plan_exit_long_and_short():
    long = plan_exit(True, entry=100.0, atr_value=2.0, stop_atr=1.5, target_r=2.0)
    assert (long.stop, long.target, long.risk, long.r_target) == (97.0, 106.0, 3.0, 2.0)
    short = plan_exit(False, entry=100.0, atr_value=2.0, stop_atr=1.5, target_r=2.0)
    assert (short.stop, short.target) == (103.0, 94.0)
    assert plan_exit(True, 100.0, 0.0, 1.5, 2.0) is None
    assert plan_exit(False, 10.0, 2.0, 1.0, 5.0) is None  # target below zero


def test_a_bar_through_both_counts_as_the_stop():
    assert exit_hit(True, low=95, high=110, stop=97, target=106) == "stop"
    assert exit_hit(True, low=98, high=110, stop=97, target=106) == "target"
    assert exit_hit(False, low=90, high=104, stop=103, target=94) == "stop"
    assert exit_hit(False, low=93, high=101, stop=103, target=94) == "target"
    assert exit_hit(True, low=98, high=105, stop=97, target=106) is None


# ----------------------------------------------------------------- sizing


def test_units_for_risk_and_the_cash_cap():
    # lose at most 10 with 2 of risk a unit: 5 units, if the cash allows
    assert units_for_risk(10, 2, price=100, budget_cap=1000) == 5
    assert units_for_risk(10, 2, price=100, budget_cap=300) == 3  # the cash cap wins
    assert units_for_risk(10, 2, price=100, budget_cap=100, leverage=5) == 5  # margin 100 at 5x = 500 notional
    assert units_for_risk(0, 2, price=100, budget_cap=100) == 0


# ------------------------------------------------------------------- risk


def test_check_entry_passes_and_blocks():
    ok = EntryCheck(equity=1000, loss_at_stop=10, max_loss=10)
    assert check_entry(ok) == []
    assert check_entry(EntryCheck(equity=1000, loss_at_stop=15, max_loss=10))[0].startswith("pérdida en el stop")
    assert "pérdida diaria" in check_entry(EntryCheck(equity=940, loss_at_stop=None, max_loss=None,
                                                      day_start_equity=1000, daily_loss_limit=0.05))[0]
    assert check_entry(EntryCheck(equity=960, loss_at_stop=None, max_loss=None,
                                  day_start_equity=1000, daily_loss_limit=0.05)) == []
    assert "entradas por día" in check_entry(EntryCheck(equity=1000, loss_at_stop=None, max_loss=None,
                                                         entries_today=3, max_entries_per_day=3))[0]
    beyond = EntryCheck(equity=1000, loss_at_stop=None, max_loss=None, stop=60, liquidation=67, long=True)
    assert "liquidación" in check_entry(beyond)[0]


# ----------------------------------------------------------- time machine


def pool_of(bar):
    return [[bar] * 10 for _ in range(24)]


def test_simulate_every_replay_rises_to_the_target():
    sim = simulate(pool_of((1.0, 1.02, 1.0, 1.01)), 0, entry=100, stop=98, target=104, horizon=10, replays=500)
    assert (sim.p_target, sim.p_stop, sim.p_neither, sim.p_green) == (1.0, 0.0, 0.0, 1.0)
    assert sim.avg_r == pytest.approx(2.0) and sim.r_at_target == 2.0
    assert len(sim.bands) == 11 and sim.bands[0] == [100] * 5


def test_simulate_every_replay_falls_to_the_stop_and_shorts_mirror_it():
    falling = pool_of((1.0, 1.0, 0.98, 0.99))
    assert simulate(falling, 0, 100, 98, 104, horizon=10, replays=500).p_stop == 1.0
    assert simulate(falling, 0, 100, 102, 96, horizon=10, long=False, replays=500).p_target == 1.0


def test_simulate_is_repeatable_with_the_seed():
    mixed = [[(1.0, 1.01, 0.99, 1.005), (1.0, 1.01, 0.99, 0.995), (1.0, 1.0, 0.97, 0.98)] for _ in range(24)]
    a = simulate(mixed, 5, 100, 97, 103, horizon=24, replays=2000, seed=7)
    b = simulate(mixed, 5, 100, 97, 103, horizon=24, replays=2000, seed=7)
    assert (a.p_target, a.p_stop, a.median_close) == (b.p_target, b.p_stop, b.median_close)
    assert a.p_target + a.p_stop + a.p_neither == pytest.approx(1.0)


def test_simulate_refuses_a_backwards_plan():
    with pytest.raises(ValueError):
        simulate(pool_of((1, 1, 1, 1)), 0, entry=100, stop=101, target=104, horizon=5)


def test_slots_follow_the_utc_day():
    hour = 3_600_000
    slots, per_day = slots_of([0, hour, 23 * hour, 24 * hour], hour)
    assert per_day == 24 and slots == [0, 1, 23, 0]
    assert slots_of([0, 86_400_000], 86_400_000) == ([0, 0], 1)
    pool = build_pool([1, 1], [1, 2], [1, 1], [1, 2], [0, 1], 2)
    assert pool == [[], [(1.0, 2.0, 1.0, 2.0)]]


def test_history_replay_one_trade_at_a_time():
    closes = [100, 101, 102, 103, 104, 105, 104, 103, 102, 101]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    entries = [PastEntry(0, True, 99, 102.5),  # target on bar 2
               PastEntry(1, True, 99, 110),  # skipped: the first is still open on bar 1
               PastEntry(4, True, 102.6, 110)]  # stop on bar 8 (low 101.5)
    h = history_replay(highs, lows, closes, entries, horizon=4)
    assert (h.fired, h.target, h.stop, h.neither) == (2, 1, 1, 0)


def test_verdict_weighs_the_targets_r():
    from app.tools.timemachine import Simulation

    def sim(pt, ps, r=1.0, avg=0.0):
        return Simulation(replays=1, seed=19, horizon=1, p_target=pt, p_stop=ps, p_neither=1 - pt - ps, p_green=0,
                          median_close=0, p5_close=0, p95_close=0, avg_r=avg, r_at_target=r)

    assert verdict(sim(0.30, 0.28)).code == "coin_flip"
    assert verdict(sim(0.25, 0.50, r=2.0)).code == "break_even"  # needs 33%, got 33%
    assert verdict(sim(0.40, 0.30)).code == "leans_target"
    assert verdict(sim(0.10, 0.60)).code == "strong_stop"
    assert verdict(sim(0.0, 0.0)).code == "no_decision"
    assert verdict(sim(0.20, 0.15)).many_neither
    assert verdict(sim(0.40, 0.30, avg=-0.1)).avg_r_disagrees


def wavy_candles(n=300, hour=3_600_000):
    out = []
    for i in range(n):
        c = 100 + 5 * ((i % 24) / 24) + (i % 7) * 0.3
        out.append(Candle(time=i * hour, open=c - 0.2, high=c + 1, low=c - 1, close=c, volume=1.0))
    return out


def test_run_time_machine_end_to_end():
    out = run_time_machine(wavy_candles(), get_strategy("sma_cross"), "BTC/USDT", True, "1h", stop_atr=2.0,
                           target_r=2.0, horizon=24, replays=2000, seed=19)
    assert out.plan.stop < out.plan.entry < out.plan.target
    assert out.plan.r_at_target == pytest.approx(2.0)
    assert out.p_target + out.p_stop + out.p_neither == pytest.approx(1.0)
    assert out.pool_candles == 299 and len(out.bands) == 25
    assert out.verdict.code in {"coin_flip", "break_even", "leans_target", "leans_stop", "strong_target",
                                "strong_stop", "no_decision"}
    with pytest.raises(TimeMachineError):
        run_time_machine(wavy_candles(50), get_strategy("sma_cross"), "BTC/USDT", True, "1h", 2.0, 2.0, 24, 1000, 19)


# ------------------------------------------------------------- the agent


class RangedMarket:
    """Candles one unit either side of the close, one hour apart."""

    def __init__(self, closes):
        self.closes = closes

    async def ohlcv(self, symbol, timeframe="1h", limit=100):
        return [Candle(time=i, open=c, high=c + 1, low=c - 1, close=c, volume=1.0) for i, c in enumerate(self.closes)]


GOLDEN = [100.0] * 29 + [101.0]


def agent_with(tmp_path, market, **config):
    settings = {"symbols": ["BTC/USDT"], "strategy": "sma_cross", "use_llm_review": False, **config}
    initial = AgentState(config=AgentConfig(**settings), portfolio=Portfolio(cash=1000.0))
    return TradingAgent(market, Memory(tmp_path / "state.json", initial), PaperExecutor())


@pytest.mark.asyncio
async def test_spot_entry_gets_a_stop_a_target_and_a_risk_size(tmp_path):
    market = RangedMarket(GOLDEN)
    agent = agent_with(tmp_path, market, stop_atr=1.0, target_r=2.0, risk_per_trade=0.002)
    result = await agent.tick()

    position = agent.state().portfolio.positions["BTC/USDT"]
    risk = 101.0 - position.stop
    assert position.target == pytest.approx(101.0 + 2 * risk)
    # 0.2% of 1000 = 2 lost at the stop
    assert position.amount * risk == pytest.approx(2.0)
    assert result.trades[0].value == pytest.approx(position.amount * 101.0)


@pytest.mark.asyncio
async def test_spot_stop_sells_on_the_next_candle_that_reaches_it(tmp_path):
    market = RangedMarket(GOLDEN)
    agent = agent_with(tmp_path, market, stop_atr=1.0, target_r=2.0, risk_per_trade=0.002)
    await agent.tick()
    stop = agent.state().portfolio.positions["BTC/USDT"].stop

    market.closes = GOLDEN + [stop - 0.5]  # its low (close - 1) goes through the stop
    result = await agent.tick()
    sale = result.trades[0]
    assert sale.side == "sell" and sale.price == pytest.approx(stop) and "stop" in sale.reason
    assert "BTC/USDT" not in agent.state().portfolio.positions


@pytest.mark.asyncio
async def test_same_candle_ticks_do_not_trigger_on_its_earlier_range(tmp_path):
    market = RangedMarket(GOLDEN)
    agent = agent_with(tmp_path, market, stop_atr=0.5, target_r=2.0, risk_per_trade=0.002)
    await agent.tick()
    # the entry candle's low (100) is below a 0.5-ATR stop, but it came before the fill
    result = await agent.tick()
    assert not [t for t in result.trades if t.side == "sell"]
    assert "BTC/USDT" in agent.state().portfolio.positions


@pytest.mark.asyncio
async def test_max_entries_per_day_blocks_the_next_buy(tmp_path):
    market = RangedMarket(GOLDEN)
    agent = agent_with(tmp_path, market, max_entries_per_day=1)
    await agent.tick()
    state = agent.state()
    del state.portfolio.positions["BTC/USDT"]  # as if it had been sold
    agent.memory.save(state)

    result = await agent.tick()
    assert result.trades == []
    assert "máximo de 1 entradas por día" in result.decisions[0].reason


@pytest.mark.asyncio
async def test_perp_stop_closes_the_position(tmp_path):
    from tests.test_perp import FakeFutures

    class RangedFutures(FakeFutures):
        async def klines(self, symbol, interval="1h", limit=100):
            base = symbol.replace("USDT", "") + "/USDT"
            return [Candle(time=i, open=v, high=v + 1, low=v - 1, close=v, volume=1.0)
                    for i, v in enumerate(self.series[base])]

    futures = RangedFutures({"BTC/USDT": GOLDEN})
    initial = AgentState(config=AgentConfig(symbols=["BTC/USDT"], strategy="sma_cross", use_llm_review=False,
                                            market=Market.PERP, leverage=3.0, stop_atr=1.0, target_r=2.0,
                                            risk_per_trade=0.002), portfolio=Portfolio(cash=1000.0))
    agent = TradingAgent(RangedMarket(GOLDEN), Memory(tmp_path / "state.json", initial), PaperExecutor(),
                         futures=futures)
    await agent.tick()
    position = agent.state().portfolio.perp_positions["BTC/USDT"]
    assert position.stop < 101.0 < position.target

    futures.series["BTC/USDT"] = GOLDEN + [position.stop - 0.5]
    result = await agent.tick()
    closed = [t for t in result.trades if t.action == "close"]
    assert closed and closed[0].price == pytest.approx(position.stop)


# --------------------------------------------------------------- the route


def test_time_machine_route(client):
    from app.api.deps import get_market

    app = client.app

    class Market:
        async def ohlcv(self, symbol, timeframe="1h", limit=100):
            return wavy_candles()

    app.dependency_overrides[get_market] = lambda: Market()
    try:
        response = client.get("/api/bot/timemachine", params={"symbol": "BTC/USDT", "replays": 1000})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["replays"] == 1000 and body["seed"] == 19 and body["plan"]["side"] == "long"
        assert client.get("/api/bot/timemachine", params={"symbol": "nope"}).status_code == 422
    finally:
        app.dependency_overrides.pop(get_market, None)
