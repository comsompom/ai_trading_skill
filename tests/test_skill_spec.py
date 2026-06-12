from __future__ import annotations

from agent.mcp_server import get_skill_spec, get_strategy_spec
from skill.spec import skill_spec


def test_skill_spec_describes_fast_mcp_tools():
    spec = skill_spec()
    assert spec["not_live_trading"] is True
    assert spec["interfaces"]["fast_mcp"]["module"] == "agent.mcp_server"
    assert set(spec["interfaces"]["fast_mcp"]["tools"]) == {
        "get_skill_spec",
        "get_strategy_spec",
        "analyze_strategy",
    }
    assert "market_data" in spec["input_schema"]["properties"]
    assert spec["strategy"]["not_live_trading"] is True


def test_mcp_helpers_return_specs_without_fastmcp_installed():
    assert get_skill_spec()["id"] == "ai_trading_skill"
    assert get_strategy_spec()["not_live_trading"] is True
