from __future__ import annotations

from agent.mcp_server import get_mcp_manifest, get_skill_spec, get_strategy_spec, make_trading_decision, trading_decision_request
from skill.spec import skill_spec


def test_skill_spec_describes_fast_mcp_tools():
    spec = skill_spec()
    assert spec["not_live_trading"] is True
    assert spec["core_product"]["market_data_primary_provider"] == "cmc"
    assert spec["core_product"]["uses_own_strategy_and_analysis"] is True
    assert spec["core_product"]["requires_bnb_ai_agent_sdk"] is False
    assert spec["optional_bonus_integrations"]["bnb_ai_agent_sdk"]["core_dependency"] is False
    assert spec["interfaces"]["fast_mcp"]["module"] == "agent.mcp_server"
    assert set(spec["interfaces"]["fast_mcp"]["tools"]) == {
        "get_skill_spec",
        "get_strategy_spec",
        "analyze_strategy",
        "make_trading_decision",
        "backtest_strategy",
        "get_mcp_manifest",
    }
    assert "skill://spec" in spec["interfaces"]["fast_mcp"]["resources"]
    assert "trading_decision_request" in spec["interfaces"]["fast_mcp"]["prompts"]
    assert "market_data" in spec["input_schema"]["properties"]
    assert spec["input_schema"]["properties"]["provider"]["default"] == "cmc"
    assert "cmc" in spec["input_schema"]["properties"]["provider"]["enum"]
    assert spec["strategy"]["not_live_trading"] is True


def test_mcp_helpers_return_specs_without_fastmcp_installed():
    assert get_skill_spec()["id"] == "ai_trading_skill"
    assert get_strategy_spec()["not_live_trading"] is True


def test_mcp_manifest_lists_decision_tool():
    manifest = get_mcp_manifest()
    assert "make_trading_decision" in manifest["tools"]
    assert manifest["not_live_trading"] is True


def test_trading_decision_prompt_names_tool():
    prompt = trading_decision_request("BTCUSDT", "1h", "balanced")
    assert "make_trading_decision" in prompt
    assert "BTCUSDT" in prompt


def test_make_trading_decision_returns_non_executing_plan():
    candles = []
    price = 100.0
    for i in range(80):
        open_price = price
        close = open_price + 0.2
        candles.append(
            {
                "timestamp": 1_700_000_000 + i * 3600,
                "open": open_price,
                "high": close + 0.4,
                "low": open_price - 0.4,
                "close": close,
                "volume": 1000 + i,
            }
        )
        price = close
    result = make_trading_decision(
        {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "risk_profile": "balanced",
            "market_data": candles,
        }
    )
    assert result["decision"] in {"BUY", "SELL", "HOLD"}
    assert result["trade_plan"]["action"] == result["decision"]
    assert result["execution_policy"]["places_orders"] is False
    assert result["execution_policy"]["signs_transactions"] is False
