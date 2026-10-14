from fastapi import APIRouter, HTTPException, Query

from app.agent.agent import TickResult
from app.agent.state import AgentState, Decision
from app.api.deps import AgentDep, SettingsDep
from app.api.schemas.bot import ConfigIn, PerpPositionOut, StatusOut, StrategyOut, TradesOut
from app.strategies import STRATEGIES

router = APIRouter()


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
async def tick(agent: AgentDep):
    try:
        return await agent.tick()
    except NotImplementedError as error:
        raise HTTPException(501, str(error)) from error


@router.put("/config", response_model=StatusOut)
def update_config(body: ConfigIn, agent: AgentDep, settings: SettingsDep):
    try:
        state = agent.update_config(**body.model_dump())
    except KeyError as error:
        raise HTTPException(400, str(error.args[0])) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return _status(state, settings.llm_enabled)


@router.post("/reset", response_model=StatusOut)
def reset(agent: AgentDep, settings: SettingsDep):
    return _status(agent.reset(), settings.llm_enabled)


@router.get("/trades", response_model=TradesOut)
def trades(agent: AgentDep, limit: int = Query(50, ge=1, le=500)):
    all_trades = agent.state().portfolio.trades
    return TradesOut(trades=all_trades[-limit:][::-1], total=len(all_trades))


@router.get("/decisions", response_model=list[Decision])
def decisions(agent: AgentDep, limit: int = Query(50, ge=1, le=500)):
    return agent.state().decisions[-limit:][::-1]
