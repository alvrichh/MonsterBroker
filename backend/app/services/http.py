"""A small JSON client the public-API services share: one httpx client per
service, one error type for the routes to translate into a 502."""

from __future__ import annotations

from typing import Any

import httpx

USER_AGENT = "monsterbroker/0.1 (+https://github.com/alvrichh/MonsterBroker)"


class UpstreamError(Exception):
    """A third-party API could not be read: network, rate limit, bad payload."""


class JsonClient:
    def __init__(self, base_url: str, timeout: float = 10.0, headers: dict[str, str] | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT, **(headers or {})},
        )
        self.base_url = base_url

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **params: Any) -> Any:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as error:
            raise UpstreamError(f"{self.base_url}{path}: HTTP {error.response.status_code}") from error
        except httpx.HTTPError as error:
            raise UpstreamError(f"{self.base_url}{path}: {error}") from error
        except ValueError as error:
            raise UpstreamError(f"{self.base_url}{path}: invalid JSON") from error
