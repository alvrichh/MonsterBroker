"""Glue for the Time Machine: candles + the bot's strategy and exit rules in,
the odds, the fan chart, the history and the verdict out. No network here;
the route fetches the candles. See app/tools/timemachine.py for the method."""

from __future__ import annotations

from pydantic import BaseModel

from app.services.exchange import Candle
from app.strategies.base import Action, Strategy
from app.tools.exits import atr, plan_exit
from app.tools.timemachine import (
    BAND_Q,
    MIN_POOL,
    PastEntry,
    build_pool,
    history_replay,
    simulate,
    slots_of,
    verdict,
)

ATR_PERIOD = 14
INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000,
               "4h": 14_400_000, "1d": 86_400_000, "1w": 604_800_000}


class TimeMachineError(ValueError):
    """The run can't be made: too few candles, no ATR, a nonsense plan."""


class PlanOut(BaseModel):
    symbol: str
    side: str  # long | short
    timeframe: str
    entry: float
    stop: float
    target: float
    r_at_target: float
    atr: float
    stop_atr: float


class HistoryOut(BaseModel):
    strategy: str
    fired: int
    target: int
    stop: int
    neither: int
    avg_r: float | None


class VerdictOut(BaseModel):
    code: str
    share: float | None
    break_even: float | None
    many_neither: bool
    avg_r_disagrees: bool


class TimeMachineOut(BaseModel):
    plan: PlanOut
    replays: int
    seed: int
    horizon: int  # candles ahead
    pool_candles: int
    p_target: float
    p_stop: float
    p_neither: float
    p_green: float
    median_close: float
    p5_close: float
    p95_close: float
    avg_r: float
    band_quantiles: list[float]
    bands: list[list[float]]  # per step, the price at each quantile
    history: HistoryOut
    verdict: VerdictOut


def run_time_machine(candles: list[Candle], strategy: Strategy, symbol: str, long: bool, timeframe: str,
                     stop_atr: float, target_r: float, horizon: int, replays: int, seed: int) -> TimeMachineOut:
    """The last candle is the one still forming: the entry is its price, and it
    stays out of the pool and the history."""
    done = candles[:-1]
    if len(done) < MIN_POOL:
        raise TimeMachineError(f"too few candles: {len(done)} closed, {MIN_POOL} needed")
    interval = INTERVAL_MS.get(timeframe)
    if interval is None:
        raise TimeMachineError(f"unknown timeframe {timeframe!r}")

    opens, highs, lows, closes = ([c.open for c in done], [c.high for c in done], [c.low for c in done],
                                  [c.close for c in done])
    slots, per_day = slots_of([c.time for c in candles], interval)
    pool = build_pool(opens, highs, lows, closes, slots[:-1], per_day)

    entry = candles[-1].close
    value = atr(highs, lows, closes, ATR_PERIOD)
    exits = plan_exit(long, entry, value or 0.0, stop_atr, target_r)
    if exits is None or value is None:
        raise TimeMachineError("no stop can be set: not enough range in the candles")
    sim = simulate(pool, slots[-1], entry, exits.stop, exits.target, horizon, long=long, replays=replays, seed=seed)

    # History: every closed candle where the strategy gave this side's signal,
    # with the same exit rule as of that candle.
    wanted = Action.BUY if long else Action.SELL
    past: list[PastEntry] = []
    for i in range(max(strategy.min_candles, ATR_PERIOD + 1) - 1, len(done)):
        if strategy.evaluate(symbol, closes[: i + 1]).action != wanted:
            continue
        then = plan_exit(long, closes[i], atr(highs[: i + 1], lows[: i + 1], closes[: i + 1], ATR_PERIOD) or 0.0,
                         stop_atr, target_r)
        if then:
            past.append(PastEntry(index=i, long=long, stop=then.stop, target=then.target))
    history = history_replay(highs, lows, closes, past, horizon)
    v = verdict(sim)

    return TimeMachineOut(
        plan=PlanOut(symbol=symbol, side="long" if long else "short", timeframe=timeframe, entry=entry,
                     stop=exits.stop, target=exits.target, r_at_target=sim.r_at_target, atr=value, stop_atr=stop_atr),
        replays=sim.replays, seed=sim.seed, horizon=sim.horizon, pool_candles=len(done),
        p_target=sim.p_target, p_stop=sim.p_stop, p_neither=sim.p_neither, p_green=sim.p_green,
        median_close=sim.median_close, p5_close=sim.p5_close, p95_close=sim.p95_close, avg_r=sim.avg_r,
        band_quantiles=list(BAND_Q), bands=sim.bands,
        history=HistoryOut(strategy=strategy.name, fired=history.fired, target=history.target, stop=history.stop,
                           neither=history.neither, avg_r=history.avg_r),
        verdict=VerdictOut(code=v.code, share=v.share, break_even=v.break_even, many_neither=v.many_neither,
                           avg_r_disagrees=v.avg_r_disagrees),
    )
