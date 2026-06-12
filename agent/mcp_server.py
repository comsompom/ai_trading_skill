from __future__ import annotations

import json
from typing import Any

from agent.skill_runner import analyze_payload
from backtest.engine import run_backtest
from skill.spec import skill_spec
from skill.strategy_skill import strategy_spec

try:  # FastMCP package.
    from fastmcp import FastMCP
except ImportError:  # Official MCP Python SDK compatibility.
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        FastMCP = None  # type: ignore[assignment]


def _decision_envelope(result: dict) -> dict:
    decision = result["decision"]
    risk = result["risk_assumptions"]
    if decision == "BUY":
        trade_plan = {
            "action": "BUY",
            "entry_reference": "latest_closed_candle_close",
            "stop": risk["long_stop"],
            "target": risk["long_target"],
            "reward_to_risk": risk["reward_to_risk"],
        }
    elif decision == "SELL":
        trade_plan = {
            "action": "SELL",
            "entry_reference": "latest_closed_candle_close",
            "stop": risk["short_stop"],
            "target": risk["short_target"],
            "reward_to_risk": risk["reward_to_risk"],
        }
    else:
        trade_plan = {
            "action": "HOLD",
            "entry_reference": None,
            "stop": None,
            "target": None,
            "reward_to_risk": risk["reward_to_risk"],
        }
    return {
        "server": "ai_trading_skill_fastmcp",
        "not_live_trading": True,
        "decision": decision,
        "trade_plan": trade_plan,
        "skill_result": result,
        "execution_policy": {
            "places_orders": False,
            "signs_transactions": False,
            "requires_user_or_external_executor": decision in {"BUY", "SELL"},
        },
    }


def get_skill_spec() -> dict:
    """Return the complete Skill specification for MCP clients."""
    return skill_spec()


def get_strategy_spec() -> dict:
    """Return the deterministic strategy rules and implemented indicators."""
    return strategy_spec()


def analyze_strategy(payload: dict) -> dict:
    """Analyze normalized candles or provider-backed market data and return the raw Skill output."""
    return analyze_payload(payload)


def make_trading_decision(payload: dict) -> dict:
    """Return a BUY, SELL, or HOLD trading decision plus a non-executing trade plan."""
    return _decision_envelope(analyze_payload(payload))


def backtest_strategy(payload: dict) -> dict:
    """Run the deterministic strategy backtest through the MCP server."""
    return run_backtest(payload)


def get_mcp_manifest() -> dict:
    """Return the MCP-facing manifest with tools, resources, and prompts."""
    return {
        "name": "ai_trading_skill_fastmcp",
        "description": "FastMCP server for deterministic crypto trading decisions from the AI Trading Skill.",
        "not_live_trading": True,
        "tools": [
            "get_skill_spec",
            "get_strategy_spec",
            "analyze_strategy",
            "make_trading_decision",
            "backtest_strategy",
            "get_mcp_manifest",
        ],
        "resources": ["skill://spec", "strategy://spec", "mcp://manifest"],
        "prompts": ["trading_decision_request"],
    }


def trading_decision_request(symbol: str = "BTCUSDT", timeframe: str = "1h", risk_profile: str = "balanced") -> str:
    """Prompt template for clients that want the agent to call make_trading_decision."""
    return (
        "Use the FastMCP tool `make_trading_decision` to evaluate this market. "
        f"Symbol: {symbol}. Timeframe: {timeframe}. Risk profile: {risk_profile}. "
        "Use provider-backed candles if `market_data` is not supplied. Return the decision, confidence, "
        "probability, main indicator reasons, stop, target, and the non-live-trading execution policy."
    )


def _json_resource(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _register_tool(mcp, fn, **kwargs) -> None:
    try:
        mcp.tool(**kwargs)(fn)
    except TypeError:
        mcp.tool()(fn)


def _register_resource(mcp, uri: str, fn, **kwargs) -> None:
    try:
        mcp.resource(uri, **kwargs)(fn)
    except TypeError:
        mcp.resource(uri)(fn)


def _register_prompt(mcp, fn, **kwargs) -> None:
    try:
        mcp.prompt(**kwargs)(fn)
    except TypeError:
        mcp.prompt()(fn)


def create_mcp_server():
    if FastMCP is None:
        raise RuntimeError('FastMCP is not installed. Install the MCP extra with: pip install -e ".[mcp]"')

    mcp = FastMCP("ai_trading_skill")
    readonly = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}
    open_world = {**readonly, "openWorldHint": True}
    closed_world = {**readonly, "openWorldHint": False}

    _register_tool(
        mcp,
        get_skill_spec,
        description="Return the AI Trading Skill specification for discovery.",
        annotations=closed_world,
    )
    _register_tool(
        mcp,
        get_strategy_spec,
        description="Return the deterministic strategy rules and indicator list.",
        annotations=closed_world,
    )
    _register_tool(
        mcp,
        analyze_strategy,
        description="Analyze candles or provider-backed market data and return the raw Skill result.",
        annotations=open_world,
    )
    _register_tool(
        mcp,
        make_trading_decision,
        description="Make a BUY, SELL, or HOLD decision and return a non-executing trade plan.",
        annotations=open_world,
    )
    _register_tool(
        mcp,
        backtest_strategy,
        description="Backtest the deterministic strategy using normalized or provider-backed candles.",
        annotations=open_world,
    )
    _register_tool(
        mcp,
        get_mcp_manifest,
        description="Return the MCP manifest for this server.",
        annotations=closed_world,
    )

    _register_resource(
        mcp,
        "skill://spec",
        lambda: _json_resource(get_skill_spec()),
        name="SkillSpec",
        description="AI Trading Skill specification as JSON.",
        mime_type="application/json",
    )
    _register_resource(
        mcp,
        "strategy://spec",
        lambda: _json_resource(get_strategy_spec()),
        name="StrategySpec",
        description="Trading strategy specification as JSON.",
        mime_type="application/json",
    )
    _register_resource(
        mcp,
        "mcp://manifest",
        lambda: _json_resource(get_mcp_manifest()),
        name="MCPManifest",
        description="MCP server manifest as JSON.",
        mime_type="application/json",
    )

    _register_prompt(
        mcp,
        trading_decision_request,
        description="Prompt template for asking an MCP client to call the decision tool.",
    )
    return mcp


server = create_mcp_server() if FastMCP is not None else None


if __name__ == "__main__":
    create_mcp_server().run()
