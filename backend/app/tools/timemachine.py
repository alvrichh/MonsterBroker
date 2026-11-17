"""The Time Machine: before the bot (or you) risks anything, replay what
could happen to a trade from the coin's own recent candles.

Ported to crypto from the Time Machine in Jake Schincariol's
day-trader-skill (MIT, see THIRD_PARTY_NOTICES.md). The method is the same:

1. The pool. Every past candle becomes four ratios to the candle before it
   (open, high, low, close over the previous close), filed under its time of
   day. Crypto never closes, so "time of day" is the candle's slot in the UTC
   day (hour 14 on 1h candles, the 08:00 slot on 4h ones...).
2. One replay. Start at the entry. For each candle of the horizon, draw a
   past candle from the same slot (± `window` slots) and scale it to the
   current price. Check the stop first, then the target; a candle that
   touches both counts as the stop.
3. N replays give the odds: target first, stop first, neither (still open at
   the end of the horizon) and green (target, or above the entry at the end).
   R is +r at the target, -1 at the stop, else the move over the risk.
4. The history. The strategy's own entries on those same candles, played out
   on the real candles that followed. What happened, not a simulation.
5. The verdict weighs the target's R: a 2R target only needs to come first in
   1 of 3 decided replays to break even.

Pure functions over lists of floats, seeded, so any run can be repeated.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field

BAND_Q = (0.05, 0.25, 0.5, 0.75, 0.95)
BAND_PATHS = 2000
COIN_FLIP = 0.05
STRONG = 0.15
MANY_NEITHER = 0.40
MIN_POOL = 100  # candles; fewer and the odds mean nothing

Bar = tuple[float, float, float, float]  # open, high, low, close over the previous close


def slots_of(times_ms: list[int], interval_ms: int) -> tuple[list[int], int]:
    """Each candle's slot in the UTC day and how many slots a day has (1 for
    daily candles and longer: then there is no time of day to match)."""
    per_day = max(1, 86_400_000 // interval_ms) if interval_ms > 0 else 1
    return [(t // interval_ms) % per_day if interval_ms > 0 else 0 for t in times_ms], per_day


def build_pool(opens: list[float], highs: list[float], lows: list[float], closes: list[float],
               slots: list[int], n_slots: int) -> list[list[Bar]]:
    pool: list[list[Bar]] = [[] for _ in range(n_slots)]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev <= 0:
            continue
        pool[slots[i] % n_slots].append((opens[i] / prev, highs[i] / prev, lows[i] / prev, closes[i] / prev))
    return pool


def _pct(sorted_values: list[float], q: float) -> float:
    return sorted_values[min(len(sorted_values) - 1, int(q * len(sorted_values)))]


@dataclass(slots=True)
class Simulation:
    replays: int
    seed: int
    horizon: int
    p_target: float
    p_stop: float
    p_neither: float
    p_green: float
    median_close: float
    p5_close: float
    p95_close: float
    avg_r: float
    r_at_target: float
    bands: list[list[float]] = field(default_factory=list)  # per step: the BAND_Q quantiles of the price


def simulate(pool: list[list[Bar]], start_slot: int, entry: float, stop: float, target: float, horizon: int,
             long: bool = True, replays: int = 10_000, seed: int = 19, window: int = 2) -> Simulation:
    n_slots = len(pool)
    everything = [bar for bars in pool for bar in bars]
    if not everything:
        raise ValueError("empty pool")
    risk = (entry - stop) if long else (stop - entry)
    if risk <= 0:
        raise ValueError("the stop must be on the losing side of the entry")
    r_target = round(((target - entry) if long else (entry - target)) / risk, 4)
    if r_target <= 0:
        raise ValueError("the target must be on the winning side of the entry")

    # Candidates per future step: its slot ± window, all of them on daily candles.
    candidates: list[list[Bar]] = []
    for step in range(1, horizon + 1):
        if n_slots <= 2 * window + 1:
            candidates.append(everything)
            continue
        slot = (start_slot + step) % n_slots
        near = [bar for d in range(-window, window + 1) for bar in pool[(slot + d) % n_slots]]
        candidates.append(near or everything)

    rng = random.Random(seed)
    outcomes: list[str] = []
    finals: list[float] = []
    for _ in range(replays):
        price, outcome = entry, None
        for bars in candidates:
            _, h, lo, c = rng.choice(bars)
            if outcome is None:
                high, low = price * h, price * lo
                if long:
                    outcome = "stop" if low <= stop else "target" if high >= target else None
                else:
                    outcome = "stop" if high >= stop else "target" if low <= target else None
            price *= c
        outcomes.append(outcome or "neither")
        finals.append(price)

    def r_of(outcome: str, final: float) -> float:
        if outcome == "target":
            return r_target
        if outcome == "stop":
            return -1.0
        return ((final - entry) if long else (entry - final)) / risk

    green = sum(1 for o, p in zip(outcomes, finals, strict=True)
                if o == "target" or (o == "neither" and (p > entry if long else p < entry)))
    ordered = sorted(finals)

    # Fan chart: a second, smaller run with the same seed, quantiles per step.
    rng = random.Random(seed)
    paths = []
    for _ in range(min(BAND_PATHS, replays)):
        price, path = entry, [entry]
        for bars in candidates:
            price *= rng.choice(bars)[3]
            path.append(price)
        paths.append(path)
    bands = []
    for step in range(horizon + 1):
        column = sorted(p[step] for p in paths)
        bands.append([_pct(column, q) for q in BAND_Q])

    return Simulation(
        replays=replays, seed=seed, horizon=horizon,
        p_target=outcomes.count("target") / replays, p_stop=outcomes.count("stop") / replays,
        p_neither=outcomes.count("neither") / replays, p_green=green / replays,
        median_close=_pct(ordered, 0.5), p5_close=_pct(ordered, 0.05), p95_close=_pct(ordered, 0.95),
        avg_r=statistics.fmean(r_of(o, p) for o, p in zip(outcomes, finals, strict=True)),
        r_at_target=r_target, bands=bands,
    )


@dataclass(slots=True, frozen=True)
class PastEntry:
    index: int  # the candle the entry filled on (its close)
    long: bool
    stop: float
    target: float


@dataclass(slots=True)
class History:
    fired: int = 0
    target: int = 0
    stop: int = 0
    neither: int = 0
    avg_r: float | None = None


def history_replay(highs: list[float], lows: list[float], closes: list[float], entries: list[PastEntry],
                   horizon: int) -> History:
    """Play each past entry forward on the real candles that followed. One
    trade at a time, like the bot: an entry while the previous one is still
    open is skipped. Entries without `horizon` candles after them are left
    out (they haven't finished yet)."""
    out = History()
    busy_until = -1
    rs: list[float] = []
    for e in sorted(entries, key=lambda e: e.index):
        if e.index <= busy_until or e.index + horizon >= len(closes):
            continue
        entry = closes[e.index]
        risk = (entry - e.stop) if e.long else (e.stop - entry)
        if risk <= 0:
            continue
        r_target = ((e.target - entry) if e.long else (entry - e.target)) / risk
        outcome, end = None, e.index + horizon
        for i in range(e.index + 1, e.index + horizon + 1):
            if e.long:
                outcome = "stop" if lows[i] <= e.stop else "target" if highs[i] >= e.target else None
            else:
                outcome = "stop" if highs[i] >= e.stop else "target" if lows[i] <= e.target else None
            if outcome:
                end = i
                break
        out.fired += 1
        if outcome == "target":
            out.target += 1
            rs.append(r_target)
        elif outcome == "stop":
            out.stop += 1
            rs.append(-1.0)
        else:
            out.neither += 1
            final = closes[end]
            rs.append(((final - entry) if e.long else (entry - final)) / risk)
        busy_until = end
    out.avg_r = statistics.fmean(rs) if rs else None
    return out


@dataclass(slots=True, frozen=True)
class Verdict:
    code: str  # no_decision | coin_flip | break_even | leans_target | leans_stop | strong_target | strong_stop
    share: float | None = None  # the target's share of the replays that hit a side
    break_even: float | None = None  # the share the target's R needs: 1 / (1 + R)
    many_neither: bool = False  # more than 40% hit neither: the price at the end decides those
    avg_r_disagrees: bool = False  # average R points against the lean


def verdict(sim: Simulation) -> Verdict:
    decided = sim.p_target + sim.p_stop
    if decided <= 0:
        return Verdict(code="no_decision")
    share, even = sim.p_target / decided, 1.0 / (1.0 + sim.r_at_target)
    gap = share - even
    if abs(gap) < COIN_FLIP:
        code = "coin_flip" if abs(sim.r_at_target - 1.0) < 0.005 else "break_even"
    elif abs(gap) < STRONG:
        code = "leans_target" if gap > 0 else "leans_stop"
    else:
        code = "strong_target" if gap > 0 else "strong_stop"
    disagrees = abs(gap) >= COIN_FLIP and sim.avg_r != 0 and (sim.avg_r > 0) != (gap > 0)
    return Verdict(code=code, share=share, break_even=even, many_neither=sim.p_neither > MANY_NEITHER,
                   avg_r_disagrees=disagrees)
