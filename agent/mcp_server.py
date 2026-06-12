from __future__ import annotations

from agent.skill_runner import analyze_payload
from skill.spec import skill_spec
from skill.strategy_skill import strategy_spec

try:  # FastMCP package.
    from fastmcp import FastMCP
except ImportError:  # Official MCP Python SDK compatibility.
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        FastMCP = None  # type: ignore[assignment]


def get_skill_spec() -> dict:
    return skill_spec()


def get_strategy_spec() -> dict:
    return strategy_spec()


def analyze_strategy(payload: dict) -> dict:
    return analyze_payload(payload)


def create_mcp_server():
    if FastMCP is None:
        raise RuntimeError('FastMCP is not installed. Install the MCP extra with: pip install -e ".[mcp]"')

    mcp = FastMCP("ai_trading_skill")
    mcp.tool()(get_skill_spec)
    mcp.tool()(get_strategy_spec)
    mcp.tool()(analyze_strategy)
    return mcp


server = create_mcp_server() if FastMCP is not None else None


if __name__ == "__main__":
    create_mcp_server().run()
