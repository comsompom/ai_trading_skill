from __future__ import annotations

from app.flask_app import create_app


def test_index_route_lists_endpoints():
    app = create_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    body = response.get_data(as_text=True)
    assert "AI Trading Skill" in body
    assert "Run Skill Analysis" in body
    assert "priceChart" in body


def test_favicon_route_returns_no_content():
    app = create_app()
    client = app.test_client()
    response = client.get("/favicon.ico")
    assert response.status_code == 204


def test_health_route():
    app = create_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_strategy_spec_route():
    app = create_app()
    client = app.test_client()
    response = client.get("/strategy/spec")
    assert response.status_code == 200
    assert response.get_json()["not_live_trading"] is True


def test_skill_spec_route():
    app = create_app()
    client = app.test_client()
    response = client.get("/skill/spec")
    assert response.status_code == 200
    assert response.get_json()["interfaces"]["fast_mcp"]["module"] == "agent.mcp_server"


def test_market_data_route_returns_inline_candles():
    app = create_app()
    client = app.test_client()
    candles = [
        {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "timestamp": 1_700_000_000 + i * 3600,
            "open": 100 + i,
            "high": 101 + i,
            "low": 99 + i,
            "close": 100.5 + i,
            "volume": 1000 + i,
        }
        for i in range(80)
    ]
    response = client.post(
        "/market-data",
        json={
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "lookback": 80,
            "provider": "cmc",
            "market_data": candles,
        },
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["symbol"] == "BTCUSDT"
    assert len(payload["candles"]) == 80
