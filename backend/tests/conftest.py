"""Every test gets a throwaway data dir and no external keys, so nothing
touches the network or the real paper portfolio."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def settings_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DOCS_DIR", str(tmp_path / "docs"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("WEB3_RPC_URL", "")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("NEWS_AUTO_REFRESH", "false")
    os.environ.pop("PAPER_TRADING", None)

    from app.api import deps
    from app.config import get_settings

    get_settings.cache_clear()
    deps.reset_singletons()
    yield get_settings()
    get_settings.cache_clear()
    deps.reset_singletons()


@pytest.fixture
def client(settings_env):
    from main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
