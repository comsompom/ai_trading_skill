from __future__ import annotations

from skill.strategy_skill import strategy_spec


def skill_spec() -> dict:
    strategy = strategy_spec()
    return {
        "id": "ai_trading_skill",
        "name": "AI Trading Skill",
        "version": "0.1.0",
        "track": "track_2_strategy_skill",
        "description": "Deterministic, backtestable crypto strategy Skill built from ported MT4 indicator logic. It returns BUY, SELL, or HOLD and never executes trades.",
        "not_live_trading": True,
        "interfaces": {
            "flask": {
                "health": "GET /health",
                "skill_spec": "GET /skill/spec",
                "strategy_spec": "GET /strategy/spec",
                "analyze": "POST /analyze",
                "backtest": "POST /backtest",
            },
            "fast_mcp": {
                "module": "agent.mcp_server",
                "run_command": "python3 -m agent.mcp_server",
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
            },
        },
        "input_schema": {
            "type": "object",
            "required": ["symbol", "timeframe"],
            "properties": {
                "symbol": {"type": "string", "default": "BTCUSDT"},
                "timeframe": {"type": "string", "default": "1h"},
                "lookback": {"type": "integer", "minimum": 60, "maximum": 1000, "default": 300},
                "risk_profile": {
                    "type": "string",
                    "enum": ["conservative", "balanced", "aggressive"],
                    "default": "balanced",
                },
                "provider": {
                    "type": "string",
                    "enum": ["binance", "coingecko", "coinpaprika", "defillama"],
                    "default": "binance",
                },
                "market_data": {
                    "type": "array",
                    "description": "Optional normalized OHLCV candles. If empty, the configured provider is used.",
                    "items": {
                        "type": "object",
                        "required": ["timestamp", "open", "high", "low", "close"],
                        "properties": {
                            "symbol": {"type": "string"},
                            "timeframe": {"type": "string"},
                            "timestamp": {"type": "integer"},
                            "open": {"type": "number"},
                            "high": {"type": "number"},
                            "low": {"type": "number"},
                            "close": {"type": "number"},
                            "volume": {"type": "number", "default": 0},
                        },
                    },
                    "default": [],
                },
            },
        },
        "output_schema": {
            "type": "object",
            "required": [
                "symbol",
                "timeframe",
                "decision",
                "confidence",
                "probability_of_success",
                "score_breakdown",
                "indicator_values",
                "risk_assumptions",
            ],
            "properties": {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string"},
                "decision": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "probability_of_success": {"type": "number", "minimum": 0, "maximum": 1},
                "probability_model": {"type": "string", "enum": ["heuristic", "calibrated"]},
                "probability_sample_size": {"type": "integer", "minimum": 0},
                "score_breakdown": {"type": "object"},
                "indicator_values": {"type": "object"},
                "explanation": {"type": "string"},
                "risk_assumptions": {"type": "object"},
                "backtestable_rules": {"type": "array", "items": {"type": "string"}},
            },
        },
        "capabilities": [
            "closed-candle deterministic signal generation",
            "strategy specification for agent discovery",
            "normalized candle analysis",
            "provider-backed analysis when market_data is omitted",
            "backtestable rules and risk assumptions",
            "ABCD_hand_v4 projection context with D target and Fibonacci levels",
            "De_Mark_Support_V2 support/resistance TD breakout context",
            "APEX_Indi A-P-E-X pattern trigger",
            "HL_Signal session high/low context",
            "FastMCP trading decision tool with non-executing trade plan",
        ],
        "strategy": strategy,
    }
