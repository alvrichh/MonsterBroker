"""Small helpers shared across the app."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def today() -> str:
    return utc_now().date().isoformat()


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def to_exchange_symbol(symbol: str) -> str:
    """'BTC/USDT' -> 'BTCUSDT', what Binance's REST API expects."""
    return symbol.replace("/", "").upper()


_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def strip_html(value: str | None) -> str:
    return _SPACES.sub(" ", _TAGS.sub(" ", value or "")).strip()


def is_safe_url(value: str | None) -> bool:
    return bool(value) and value.lower().startswith(("http://", "https://"))
