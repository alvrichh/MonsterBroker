"""A tiny in-memory TTL cache so the free-tier APIs (CoinGecko, DefiLlama,
alternative.me) are hit once per window, not once per page view. If a
refresh fails and a stale value exists, the stale value is served."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    async def get_or_fetch(self, key: str, ttl: float, fetch: Callable[[], Awaitable[Any]]) -> Any:
        hit = self._store.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        try:
            value = await fetch()
        except Exception:
            if hit:
                return hit[1]
            raise
        self._store[key] = (time.monotonic() + ttl, value)
        return value

    def clear(self) -> None:
        self._store.clear()


cache = TTLCache()
