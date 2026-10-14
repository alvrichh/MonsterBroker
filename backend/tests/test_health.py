def test_health_reports_safe_defaults(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["paper_trading"] is True
    assert data["llm_enabled"] is False
    assert data["web3_enabled"] is False


def test_strategies_are_listed(client, auth_headers):
    names = {s["name"] for s in client.get("/api/bot/strategies", headers=auth_headers).json()}
    assert {"sma_cross", "rsi_reversion"} <= names


def test_visitors_can_watch_the_bot_but_not_drive_it(client):
    # watching is public, so people can see what the app does without an account
    assert client.get("/api/bot/status").status_code == 200
    assert client.get("/api/bot/strategies").status_code == 200
    assert client.get("/api/bot/trades").status_code == 200
    assert client.get("/api/bot/decisions").status_code == 200
    assert client.get("/api/wallet/chains").status_code == 200
    # driving the shared paper portfolio needs an account
    assert client.post("/api/bot/tick").status_code == 401
    assert client.post("/api/bot/reset").status_code == 401
    assert client.put("/api/bot/config", json={"trade_fraction": 0.5}).status_code == 401


def test_bot_status_starts_flat(client, settings_env, auth_headers):
    data = client.get("/api/bot/status", headers=auth_headers).json()
    assert data["mode"] == "paper"
    assert data["portfolio"]["cash"] == settings_env.paper_starting_balance
    assert data["portfolio"]["positions"] == {}
    assert data["ticks"] == 0


def test_bot_config_rejects_unknown_strategy(client, auth_headers):
    response = client.put("/api/bot/config", json={"strategy": "moon_shot"}, headers=auth_headers)
    assert response.status_code == 400


def test_bot_config_updates(client, auth_headers):
    data = client.put("/api/bot/config", json={"symbols": ["BTC/USDT"], "trade_fraction": 0.5},
                      headers=auth_headers).json()
    assert data["config"]["symbols"] == ["BTC/USDT"]
    assert data["config"]["trade_fraction"] == 0.5
