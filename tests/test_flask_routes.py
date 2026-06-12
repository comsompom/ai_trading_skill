from __future__ import annotations

from app.flask_app import create_app


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
