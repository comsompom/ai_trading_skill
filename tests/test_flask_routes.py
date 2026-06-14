from __future__ import annotations

import requests

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
    assert "Indicator Recommendations" in body
    assert "recommendBtn" in body
    assert "priceChart" in body
    assert "Binance explicit" not in body
    assert '<option value="4h" selected>4h</option>' in body
    assert '<option value="1d">1d</option>' in body
    assert '<option value="15m">' not in body
    assert '<option value="1h"' not in body


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


def test_indicator_recommendations_spec_route():
    app = create_app()
    client = app.test_client()
    response = client.get("/indicator-recommendations/spec")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["not_live_trading"] is True
    assert payload["name"] == "Historical Indicator Recommendation Skill"


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


def test_market_data_route_returns_provider_error(monkeypatch):
    class FailingProvider:
        def get_candles(self, symbol: str, timeframe: str, limit: int):
            raise requests.ConnectionError("provider unavailable")

    monkeypatch.setattr("app.routes.get_provider", lambda name: FailingProvider())

    app = create_app()
    client = app.test_client()
    response = client.post(
        "/market-data",
        json={"symbol": "BTCUSDT", "timeframe": "1h", "lookback": 80, "provider": "cmc", "market_data": []},
    )
    payload = response.get_json()
    assert response.status_code == 502
    assert "market data provider error" in payload["error"]


def test_indicator_recommendations_route_returns_inline_report():
    app = create_app()
    client = app.test_client()
    candles = [
        {
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "timestamp": 1_700_000_000 + i * 14_400,
            "open": 100 + i * 0.15,
            "high": 100.7 + i * 0.15,
            "low": 99.4 + i * 0.15,
            "close": 100.2 + i * 0.15 + (0.25 if i % 8 < 4 else -0.2),
            "volume": 1000 + i,
        }
        for i in range(130)
    ]
    response = client.post(
        "/indicator-recommendations",
        json={
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "lookback": 130,
            "provider": "cmc",
            "market_data": candles,
        },
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["symbol"] == "BTCUSDT"
    assert len(payload["all_indicators"]) == 10
    assert payload["analysis_settings"]["candles"] == 130


def test_analyze_route_sends_telegram_when_requested(monkeypatch):
    captured = {}

    def fake_analyze_payload(payload):
        return {
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "decision": "BUY",
            "confidence": 0.72,
            "probability_of_success": 0.57,
            "probability_model": "heuristic",
            "score_breakdown": {"buy_score": 0.72, "sell_score": 0.21},
            "risk_assumptions": {
                "risk_profile": "balanced",
                "reward_to_risk": 1.6,
                "long_stop": 100,
                "long_target": 116,
                "short_stop": 110,
                "short_target": 94,
            },
            "explanation": "test explanation",
        }

    def fake_send_telegram(message):
        captured["message"] = message
        return {"sent": True, "status_code": 200}

    monkeypatch.setattr("app.routes.analyze_payload", fake_analyze_payload)
    monkeypatch.setattr("app.routes.send_telegram", fake_send_telegram)

    app = create_app()
    client = app.test_client()
    response = client.post("/analyze", json={"notify_telegram": True})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["notifications"]["telegram"]["sent"] is True
    assert "AI Trading Skill Analysis" in captured["message"]
    assert "BTCUSDT/4h: BUY" in captured["message"]
    assert "Confidence: 72.0%" in captured["message"]


def test_analyze_route_does_not_send_telegram_by_default(monkeypatch):
    def fake_analyze_payload(payload):
        return {"symbol": "BTCUSDT", "timeframe": "4h", "decision": "HOLD", "confidence": 0.5}

    def fail_send_telegram(message):
        raise AssertionError("Telegram should not be called unless notify_telegram is requested")

    monkeypatch.setattr("app.routes.analyze_payload", fake_analyze_payload)
    monkeypatch.setattr("app.routes.send_telegram", fail_send_telegram)

    app = create_app()
    client = app.test_client()
    response = client.post("/analyze", json={})
    payload = response.get_json()

    assert response.status_code == 200
    assert "notifications" not in payload
