from fastapi import APIRouter

from app import __version__
from app.api.deps import SettingsDep

router = APIRouter()


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, object]:
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
        "paper_trading": settings.paper_trading,
        "llm_enabled": settings.llm_enabled,
        "web3_enabled": settings.web3_enabled,
    }
