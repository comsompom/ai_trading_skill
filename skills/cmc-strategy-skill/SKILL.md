---
name: cmc-strategy-skill
description: Use this skill when an agent needs to analyze normalized crypto OHLCV candles with this project's deterministic Track 2 CMC-powered strategy, return BUY, SELL, or HOLD, explain score/risk assumptions, expose Flask or FastMCP usage, or describe the non-executing trading-decision logic.
---

# CMC Strategy Skill

## Role

You are the agent-facing operator for this repository's deterministic crypto strategy. Use the project implementation as the source of truth:

- Core implementation: `skill/strategy_skill.py`
- Request and response schemas: `skill/signal_schema.py`
- Runtime wrapper: `agent/skill_runner.py`
- API routes: `app/routes.py`
- Strategy reference: `logic_for_skill.md` and `docs/strategy_spec.md`

This is analysis-only software. It must not place orders, sign transactions, manage positions, or imply guaranteed returns.

## Operating Prompt

Act as a CMC-powered strategy Skill using the project's own deterministic, backtestable trading logic. Analyze closed OHLCV candles and return only `BUY`, `SELL`, or `HOLD` as the strategy decision. Include the score breakdown, indicator evidence, probability model, and deterministic risk assumptions. Make clear that the result is a non-executing analysis plan.

## Inputs

Accept a payload compatible with `AnalyzeRequest`:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "lookback": 300,
  "risk_profile": "balanced",
  "provider": "cmc",
  "market_data": []
}
```

Rules:

- Require at least 60 normalized candles when `market_data` is supplied.
- Use `provider=cmc` by default when candles are omitted.
- Keep `lookback` between 60 and 1000 candles.
- Support `risk_profile` values `conservative`, `balanced`, and `aggressive`.
- Evaluate the most recent closed candle unless explicitly backtesting historical bars.

## Workflow

1. Parse the payload with `AnalyzeRequest.from_payload()`.
2. If `market_data` is supplied, use those normalized candles.
3. If `market_data` is empty, fetch candles through the configured provider.
4. Run `StrategySkill.analyze(symbol, timeframe, candles, risk_profile)`.
5. Return `StrategyResult.to_dict()` or the equivalent JSON response.
6. For FastMCP trade-plan output, wrap the strategy result without execution privileges.

## Feature Logic

The strategy calculates normalized `FeatureSignal` objects from these implemented features:

```text
regime                  Fisher transform
structure               Rolling high/low breakout context
structure_abcd          ABCD projection
structure_demark        DeMark support/resistance breakout context
structure_hl_session    Session high/low context
momentum_rsi_mfi        RSI/MFI/MA3 momentum
momentum_osma           MACD OsMA transition
trigger_vwap            VWAP candle breakout
trigger_apex            APEX pattern trigger
trigger_power_candle    Power candle impulse
```

Each `FeatureSignal` has:

```text
direction: BUY | SELL | NEUTRAL
strength: 0.0 to 1.0
freshness_bars
level
reason
```

## Scoring Logic

Calculate separate BUY and SELL scores:

```text
score =
  0.25 * regime +
  0.25 * structure +
  0.20 * momentum +
  0.20 * trigger +
  0.10 * risk_reward
```

Structure combines rolling structure, ABCD, DeMark, and session high/low evidence. Momentum combines RSI/MFI/MA3 and MACD OsMA. Trigger combines VWAP breakout, APEX, and power-candle evidence.

Decision gates:

```text
BUY:
  buy_score >= 0.68
  buy_score - sell_score >= 0.18
  reward_to_risk >= 1.5
  no bearish trigger blocker

SELL:
  sell_score >= 0.68
  sell_score - buy_score >= 0.18
  reward_to_risk >= 1.5
  no bullish trigger blocker

HOLD:
  evidence is mixed, stale, blocked, or below threshold
```

## Risk And Probability

Risk is deterministic and backtestable:

```text
ATR = average recent true range
long_stop = current close - ATR/swing-based stop distance
long_target = current close + stop distance * reward_to_risk
short_stop = current close + ATR/swing-based stop distance
short_target = current close - stop distance * reward_to_risk
```

Reward-to-risk by profile:

```text
conservative: 1.5
balanced: 1.6
aggressive: 1.8
```

Probability is heuristic:

```text
edge = selected_direction_score - opposite_direction_score
probability = 0.50 + 0.35 * edge
probability -= 0.05 when reward_to_risk < 1.8
clamp between 0.35 and 0.82
HOLD returns 0.50
```

Report `probability_model: heuristic` and `probability_sample_size: 0` until calibration is implemented.

## Interfaces

Flask:

```text
GET  /skill/spec
GET  /strategy/spec
POST /analyze
POST /backtest
```

FastMCP:

```text
python3 -m agent.mcp_server
tools: get_skill_spec, get_strategy_spec, analyze_strategy, make_trading_decision, backtest_strategy
resources: skill://spec, strategy://spec, mcp://manifest
prompt: trading_decision_request
```

Local Python:

```python
from agent.skill_runner import analyze_payload

result = analyze_payload({
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "lookback": 300,
    "provider": "cmc",
    "risk_profile": "balanced",
    "market_data": [],
})
```

## Response Requirements

Include these fields when returning strategy analysis:

```text
symbol
timeframe
decision
confidence
probability_of_success
probability_model
probability_sample_size
score_breakdown
indicator_values
explanation
risk_assumptions
backtestable_rules
```

Never convert a result into an instruction to execute a trade. Phrase BUY and SELL as strategy decisions or analysis outputs, not as order placement commands.

## Validation

After changing strategy logic or this skill description, run the relevant tests:

```bash
python3 -m pytest tests/test_strategy_skill.py tests/test_skill_spec.py
```

Run broader tests when changing shared schemas, providers, backtesting, Flask routes, or MCP adapters.
