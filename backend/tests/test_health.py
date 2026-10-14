def test_health_reports_safe_defaults(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["paper_trading"] is True
    assert data["llm_enabled"] is False
    assert data["web3_enabled"] is False


def test_strategies_are_listed(client):
    names = {s["name"] for s in client.get("/api/bot/strategies").json()}
    assert {"sma_cross", "rsi_reversion"} <= names


def test_bot_status_starts_flat(client, settings_env):
    data = client.get("/api/bot/status").json()
    assert data["mode"] == "paper"
    assert data["portfolio"]["cash"] == settings_env.paper_starting_balance
    assert data["portfolio"]["positions"] == {}
    assert data["ticks"] == 0


def test_bot_config_rejects_unknown_strategy(client):
    response = client.put("/api/bot/config", json={"strategy": "moon_shot"})
    assert response.status_code == 400


def test_bot_config_updates(client):
    data = client.put("/api/bot/config", json={"symbols": ["BTC/USDT"], "trade_fraction": 0.5}).json()
    assert data["config"]["symbols"] == ["BTC/USDT"]
    assert data["config"]["trade_fraction"] == 0.5
