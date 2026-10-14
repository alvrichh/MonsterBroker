"""The Crypto Fear & Greed index from alternative.me. Free, keyless; they ask
for attribution next to the number, which the UI shows."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.utils.cache import cache

from .http import JsonClient

FNG_API = "https://api.alternative.me"
HISTORY_DAYS = 30


class FearGreedPoint(BaseModel):
    date: str
    value: int


class FearGreed(BaseModel):
    value: int
    classification: str
    updated_at: int
    history: list[FearGreedPoint] = Field(default_factory=list)  # oldest first
    source: str = "alternative.me"


def parse_fng(payload: dict) -> FearGreed:
    rows = payload.get("data") or []
    if not rows:
        raise ValueError("empty fear & greed payload")
    latest = rows[0]
    history = [
        FearGreedPoint(date=datetime.fromtimestamp(int(r["timestamp"]), UTC).date().isoformat(), value=int(r["value"]))
        for r in reversed(rows)
    ]
    return FearGreed(
        value=int(latest["value"]),
        classification=str(latest.get("value_classification", "")),
        updated_at=int(latest["timestamp"]),
        history=history,
    )


class SentimentService(JsonClient):
    def __init__(self) -> None:
        super().__init__(FNG_API)

    async def fear_greed(self) -> FearGreed:
        return await cache.get_or_fetch("fng", 600, self._fetch)

    async def _fetch(self) -> FearGreed:
        try:
            return parse_fng(await self.get("/fng/", limit=HISTORY_DAYS))
        except (KeyError, ValueError) as error:
            from .http import UpstreamError

            raise UpstreamError(f"fear & greed: {error}") from error


_service: SentimentService | None = None


def get_sentiment() -> SentimentService:
    global _service
    if _service is None:
        _service = SentimentService()
    return _service
