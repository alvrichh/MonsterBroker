from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DefiDep
from app.services.defillama import ChainTvl, ProtocolTvl, TvlPoint
from app.services.http import UpstreamError

router = APIRouter()


@router.get("/chains", response_model=list[ChainTvl])
async def chains(defi: DefiDep, limit: int = Query(12, ge=3, le=50)):
    try:
        return await defi.chains(limit)
    except UpstreamError as error:
        raise HTTPException(502, str(error)) from error


@router.get("/protocols", response_model=list[ProtocolTvl])
async def protocols(defi: DefiDep, limit: int = Query(15, ge=3, le=100)):
    try:
        return await defi.protocols(limit)
    except UpstreamError as error:
        raise HTTPException(502, str(error)) from error


@router.get("/tvl-history", response_model=list[TvlPoint])
async def tvl_history(defi: DefiDep, days: int = Query(180, ge=7, le=3650)):
    try:
        return await defi.tvl_history(days)
    except UpstreamError as error:
        raise HTTPException(502, str(error)) from error
