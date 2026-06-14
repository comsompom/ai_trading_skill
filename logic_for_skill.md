# Logic for Skill

This document describes only the indicators and strategy logic currently implemented in the app. It does not list MT4 files that are present in the repository but not yet ported into the Python decision engine.

Demo video for the first implemented indicator-based Strategy Skill:

- https://www.youtube.com/watch?v=TA6gRVvitJs

## Implemented Indicators And Features

| Implemented feature | Source / file | Feature group | Current role in decision |
| --- | --- | --- | --- |
| Fisher transform | `Fisher_Yur4ik3-a_v6_MTF.mq4` ported in `indicators/custom_mql_ported/fisher_yur4ik.py` | `regime` | Provides bullish or bearish regime context from Fisher threshold direction. |
| Rolling high/low structure | Native Python proxy in `skill/strategy_skill.py` | `structure` | Detects close above recent rolling resistance or below recent rolling support. |
| ABCD projection | `ABCD_hand_v4.mq4` ported in `indicators/custom_mql_ported/abcd_hand.py` | `structure` | Infers A/B/C swing points, projects D as `C + PLevel * abs(B - A)`, and exposes Fibonacci levels. |
| DeMark support/resistance | `De_Mark_Support_V2.mq4` ported in `indicators/custom_mql_ported/demark_support.py` | `structure` | Builds support/resistance trendline context, detects TD1/TD2/TD3 breakouts, and exposes target context. |
| HL session signal | `HL_Signal.mq4` ported in `indicators/custom_mql_ported/hl_signal.py` | `structure` | Tracks 09:00-18:00 session high/low expansion and failure context. |
| RSI/MFI participation | `RSI_MFI_MA3.mq4` ported in `indicators/custom_mql_ported/rsi_mfi_ma3.py` | `momentum` | Confirms whether RSI/MFI are above or below the combined moving average with price direction agreement. |
| MACD OsMA | `MACD_OSMA_Bar_alert.mq4` ported in `indicators/custom_mql_ported/macd_osma.py` | `momentum` | Detects OsMA transition and slope confirmation against current candle direction. |
| VWAP candle breakout | `VWAP_CANDLE_BREAKOUT_slope_dir_line.mq4` ported in `indicators/custom_mql_ported/vwap_candle_breakout.py` | `trigger` | Detects VWAP cross with candle-body threshold and slope-line confirmation. |
| APEX pattern | `APEX_Indi.mq4` ported in `indicators/custom_mql_ported/apex_indi.py` | `trigger` | Detects the final `X` event after an A-P-E setup as a strong pattern trigger. |
| Power candle impulse | `Power_Candle_Alerts_v2.mq4` style logic implemented in `skill/strategy_skill.py` | `trigger` | Confirms large directional candles based on current range versus recent average range. |

## Feature Signal Contract

Every implemented indicator returns a normalized feature signal:

```json
{
  "direction": "BUY | SELL | NEUTRAL",
  "strength": 0.0,
  "freshness_bars": 0,
  "level": 0.0,
  "reason": ""
}
```

Each indicator also returns a raw values dictionary. That dictionary is included in `indicator_values` for explainability, MCP responses, Flask API responses, and backtest feature snapshots.

## Feature Groups

The strategy groups the implemented indicators into these blocks:

```text
regime:
  Fisher transform

structure:
  rolling high/low structure
  ABCD projection
  DeMark support/resistance
  HL session signal

momentum:
  RSI/MFI participation
  MACD OsMA

trigger:
  VWAP candle breakout
  APEX pattern
  power candle impulse

risk_context:
  ATR
  recent swing high/low
  deterministic stop and target levels
  configured reward-to-risk profile
```

Signals are evaluated on closed candles by default.

## Scoring Model

`StrategySkill._score()` calculates separate BUY and SELL scores.

Score weights:

```text
buy_score / sell_score =
  0.25 * regime_score +
  0.25 * structure_score +
  0.20 * momentum_score +
  0.20 * trigger_score +
  0.10 * risk_reward_score
```

Structure score combines:

```text
rolling high/low structure
ABCD projection, weighted as context
DeMark breakout, weighted as stronger structure evidence
HL session signal, weighted as session context
```

Trigger score combines:

```text
VWAP candle breakout
APEX X event
power candle impulse
```

Momentum score combines:

```text
RSI/MFI participation
MACD OsMA transition
```

## BUY Logic

The strategy returns `BUY` only when all implemented filters pass:

```text
buy_score >= 0.68
buy_score - sell_score >= 0.18
reward_to_risk >= 1.5
no bearish trigger blocker
```

Bullish evidence can come from:

```text
Fisher bullish regime
close above rolling resistance
ABCD D target still above current price
DeMark resistance breakthrough
HL session BUY context
RSI/MFI above combined MA with rising close
OsMA negative but improving with bullish candle, or positive slope context
VWAP bullish breakout with rising slope line
recent APEX BUY X event
bullish power candle
```

BUY risk levels:

```text
long_stop = current close - ATR/swing-based stop distance
long_target = current close + stop distance * reward_to_risk
```

## SELL Logic

The strategy returns `SELL` only when all implemented filters pass:

```text
sell_score >= 0.68
sell_score - buy_score >= 0.18
reward_to_risk >= 1.5
no bullish trigger blocker
```

Bearish evidence can come from:

```text
Fisher bearish regime
close below rolling support
price above ABCD projected D target
DeMark support breakthrough
HL session SELL context
RSI/MFI below combined MA with falling close
OsMA positive but weakening with bearish candle, or negative slope context
VWAP bearish breakdown with falling slope line
recent APEX SELL X event
bearish power candle
```

SELL risk levels:

```text
short_stop = current close + ATR/swing-based stop distance
short_target = current close - stop distance * reward_to_risk
```

## HOLD Logic

The strategy returns `HOLD` when:

```text
BUY and SELL evidence conflict
score threshold is not met
score spread is too small
reward_to_risk is below 1.5
an opposing trigger blocker is active
indicator evidence is stale or neutral
```

## Risk Context

Risk is deterministic and backtestable:

```text
ATR = average of recent true ranges
long stop = below recent swing/VWAP invalidation with ATR padding
short stop = above recent swing/VWAP invalidation with ATR padding
reward_to_risk =
  conservative: 1.5
  balanced: 1.6
  aggressive: 1.8
```

The app does not size or execute real orders. It only returns analysis and a non-executing plan through Flask and FastMCP.

## Probability Model

The current probability is heuristic:

```text
edge = selected_direction_score - opposite_direction_score
probability = 0.50 + 0.35 * edge
```

Additional current rule:

```text
probability -= 0.05 when reward_to_risk < 1.8
probability is clamped between 0.35 and 0.82
HOLD returns 0.50
```

The response reports:

```text
probability_model: heuristic
probability_sample_size: 0
```

Historical calibration is not implemented yet.

## Outputs

The strategy result includes:

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

`indicator_values.features` contains each normalized feature signal, including:

```text
regime
structure
structure_abcd
structure_demark
structure_hl_session
momentum_rsi_mfi
momentum_osma
trigger_vwap
trigger_apex
trigger_power_candle
```

## Interfaces Using This Logic

Flask endpoints:

```text
GET  /skill/spec
GET  /strategy/spec
POST /analyze
POST /backtest
```

FastMCP tools:

```text
get_skill_spec
get_strategy_spec
analyze_strategy
make_trading_decision
backtest_strategy
get_mcp_manifest
```

`make_trading_decision` wraps the same strategy result in a non-executing trade plan. It never places orders or signs transactions.
