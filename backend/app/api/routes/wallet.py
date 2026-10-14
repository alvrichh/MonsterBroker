from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import WalletDep
from app.onchain.chains import CHAINS
from app.onchain.wallet import Balance, WalletError

router = APIRouter()


@router.get("/chains")
def chains() -> list[dict[str, object]]:
    return [asdict(chain) for chain in CHAINS.values()]


@router.get("/balance", response_model=Balance)
async def balance(wallet: WalletDep, address: str = Query(min_length=42, max_length=42),
                  chain: str = Query("ethereum")):
    try:
        return await wallet.balance(address, chain)
    except WalletError as error:
        raise HTTPException(400 if "invalid" in str(error) or "unknown" in str(error) else 502, str(error)) from error
