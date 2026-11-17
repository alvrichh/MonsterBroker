from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.agent.agent import TickResult
from app.agent.state import AgentState, Decision
from app.api.deps import AgentDep, CurrentUser, DbSession, MarketDep, QuestsDep, SettingsDep, get_current_user
from app.api.schemas.bot import ConfigIn, PerpPositionOut, StatusOut, StrategyOut, TradesOut
from app.services.exchange import MarketDataError
from app.services.quests import EVENT_BOT_CONFIG, EVENT_BOT_TICK, EVENT_PERP_MODE
from app.services.timemachine import TimeMachineError, TimeMachineOut, run_time_machine
from app.strategies import STRATEGIES, get_strategy

router = APIRouter()

# Anyone can watch the bot; only signed-in users can drive it. There is one
# shared paper portfolio, so ticks, config changes and resets affect everyone.
signed_in = [Depends(get_current_user)]


def _perp_positions(state: AgentState) -> dict[str, PerpPositionOut]:
    out = {}
    for symbol, position in state.portfolio.perp_positions.items():
        mark = state.last_prices.get(symbol, position.entry_price)
        pnl = position.unrealized_pnl(mark)
        out[symbol] = PerpPositionOut(
            **position.model_dump(), mark_price=mark, unrealized_pnl=pnl,
            roe=(pnl / position.margin * 100) if position.margin else 0.0, equity=position.equity(mark),
        )
    return out


def _status(state: AgentState, llm: bool) -> StatusOut:
    return StatusOut(
        mode=state.mode,
        market=state.config.market,
        config=state.config,
        portfolio=state.portfolio,
        equity=state.portfolio.equity(state.last_prices),
        last_prices=state.last_prices,
        last_tick=state.last_tick,
        ticks=state.ticks,
        llm_review_available=llm,
        recent_decisions=state.decisions[-20:][::-1],
        perp_positions=_perp_positions(state),
        benchmark=state.benchmark,
    )


@router.get("/status", response_model=StatusOut)
def status(agent: AgentDep, settings: SettingsDep):
    return _status(agent.state(), settings.llm_enabled)


@router.get("/strategies", response_model=list[StrategyOut])
def strategies():
    return [s.describe() for s in STRATEGIES.values()]


@router.post("/tick", response_model=TickResult)
async def tick(agent: AgentDep, user: CurrentUser, session: DbSession, quests: QuestsDep):
    try:
        result = await agent.tick()
    except NotImplementedError as error:
        raise HTTPException(501, str(error)) from error
    await quests.record_event(session, user.id, EVENT_BOT_TICK)  # the "first tick" quest
    return result


@router.put("/config", response_model=StatusOut)
async def update_config(body: ConfigIn, agent: AgentDep, settings: SettingsDep, user: CurrentUser, session: DbSession,
                        quests: QuestsDep):
    try:
        state = agent.update_config(**body.model_dump())
    except KeyError as error:
        raise HTTPException(400, str(error.args[0])) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    # Points: touching the settings once, and switching to perpetuals once.
    await quests.record_event(session, user.id, EVENT_BOT_CONFIG)
    if body.market == "perp":
        await quests.record_event(session, user.id, EVENT_PERP_MODE)
    return _status(state, settings.llm_enabled)


@router.post("/reset", response_model=StatusOut, dependencies=signed_in)
def reset(agent: AgentDep, settings: SettingsDep):
    return _status(agent.reset(), settings.llm_enabled)


@router.get("/trades", response_model=TradesOut)
def trades(agent: AgentDep, limit: int = Query(50, ge=1, le=500)):
    all_trades = agent.state().portfolio.trades
    return TradesOut(trades=all_trades[-limit:][::-1], total=len(all_trades))


@router.get("/decisions", response_model=list[Decision])
def decisions(agent: AgentDep, limit: int = Query(50, ge=1, le=500)):
    return agent.state().decisions[-limit:][::-1]


TIME_MACHINE_CANDLES = 1000  # ~6 weeks of 1h candles, ~5 months of 4h ones
DEFAULT_STOP_ATR = 2.0  # when the bot runs without stops, the replay still needs one


@router.get("/timemachine", response_model=TimeMachineOut)
async def time_machine(agent: AgentDep, market: MarketDep,
                       symbol: str = Query(..., pattern=r"^[A-Za-z0-9]+/[A-Za-z0-9]+$"),
                       side: Literal["long", "short"] = "long",
                       horizon: int = Query(24, ge=4, le=168, description="candles ahead"),
                       replays: int = Query(10_000, ge=1_000, le=20_000),
                       seed: int = Query(19, ge=0, le=1_000_000),
                       stop_atr: float | None = Query(None, gt=0.0, le=10.0),
                       target_r: float | None = Query(None, ge=0.5, le=10.0)):
    """Replay a trade on the bot's timeframe and strategy before it is taken:
    N simulated futures from the coin's own candles, plus the strategy's real
    record on those candles. A simulation, not a prediction."""
    config = agent.state().config
    try:
        candles = await market.ohlcv(symbol.upper(), config.timeframe, TIME_MACHINE_CANDLES)
    except MarketDataError as error:
        raise HTTPException(502, str(error)) from error
    try:
        return await run_in_threadpool(
            run_time_machine, candles, get_strategy(config.strategy), symbol.upper(), side == "long",
            config.timeframe, stop_atr or config.stop_atr or DEFAULT_STOP_ATR, target_r or config.target_r,
            horizon, replays, seed,
        )
    except TimeMachineError as error:
        raise HTTPException(422, str(error)) from error
