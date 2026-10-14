"""Claude through the official SDK. Two jobs, both optional: vet the agent's
signals (Reviewer) and write the news digest. Without ANTHROPIC_API_KEY
nothing here is ever constructed."""

from __future__ import annotations

import json
import re

import anthropic

from app.agent.agent import Review
from app.agent.state import Portfolio
from app.config import get_settings
from app.news.collector import NewsItem
from app.prompts.agent_prompts import REVIEW_SYSTEM, review_prompt
from app.prompts.news_prompts import DIGEST_SYSTEM, digest_prompt
from app.strategies.base import Signal
from app.tools.indicators import snapshot
from app.utils.logger import get_logger

log = get_logger(__name__)


class LLMError(Exception):
    pass


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_OBJECT = re.compile(r"\{[\s\S]*\}")


def parse_json(text: str) -> dict:
    """The prompts ask for bare JSON; tolerate a code fence or a lead-in."""
    clean = _FENCE.sub("", text.strip())
    try:
        return json.loads(clean)
    except ValueError:
        match = _OBJECT.search(clean)
        if not match:
            raise LLMError("la respuesta no contiene JSON") from None
        try:
            return json.loads(match.group(0))
        except ValueError as error:
            raise LLMError("JSON mal formado en la respuesta") from error


def _clamp(value: object, default: float = 0.5) -> float:
    try:
        return min(1.0, max(0.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


class ClaudeClient:
    def __init__(self, api_key: str, model: str, effort: str = "medium") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.effort = effort

    async def _ask(self, system: str, prompt: str, max_tokens: int = 2000) -> str:
        try:
            response = await self._client.beta.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                output_config={"effort": self.effort},
                # If a safety classifier declines, the API re-runs the request on
                # a fallback model inside the same call instead of failing.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as error:
            raise LLMError("clave de Anthropic no válida") from error
        except anthropic.RateLimitError as error:
            raise LLMError("límite de peticiones de Anthropic alcanzado") from error
        except anthropic.APIStatusError as error:
            raise LLMError(f"API de Anthropic: {error.status_code} {error.message}") from error
        except anthropic.APIConnectionError as error:
            raise LLMError("sin conexión con la API de Anthropic") from error

        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            raise LLMError(f"Claude declinó la petición ({category or 'sin categoría'})")
        if response.stop_reason == "max_tokens":
            raise LLMError("respuesta truncada por max_tokens")
        log.debug("claude %s in=%s out=%s", self.model, response.usage.input_tokens, response.usage.output_tokens)
        return "".join(block.text for block in response.content if block.type == "text")

    # ------------------------------------------------------------ reviewer

    async def review(self, signal: Signal, closes: list[float], portfolio: Portfolio) -> Review:
        data = parse_json(await self._ask(REVIEW_SYSTEM, review_prompt(signal, snapshot(closes), portfolio)))
        return Review(
            approve=bool(data.get("approve", False)),
            confidence=_clamp(data.get("confidence")),
            rationale=str(data.get("rationale", "")).strip()[:400],
        )

    # -------------------------------------------------------------- digest

    async def news_digest(self, items: list[NewsItem]) -> tuple[str, str]:
        data = parse_json(await self._ask(DIGEST_SYSTEM, digest_prompt(items), max_tokens=1500))
        headline = str(data.get("headline", "")).strip()[:90] or "Radar cripto"
        insight = str(data.get("insight", "")).strip()[:400]
        return headline, insight


_llm: ClaudeClient | None = None


def get_llm() -> ClaudeClient:
    global _llm
    if _llm is None:
        settings = get_settings()
        if not settings.llm_enabled:
            raise LLMError("ANTHROPIC_API_KEY no configurada")
        _llm = ClaudeClient(settings.anthropic_api_key, settings.anthropic_model)
    return _llm
