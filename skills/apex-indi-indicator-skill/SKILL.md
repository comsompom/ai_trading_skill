---
name: apex-indi-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's APEX_Indi A-P-E-X pattern trigger logic, including BUY and SELL state machines, X breakout events, signal freshness, strength decay, and StrategySkill trigger integration.
---

# APEX Indi Indicator Skill

## Role

You are the agent-facing operator for the repository's APEX pattern trigger.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/apex_indi.py`
- Strategy feature key: `trigger_apex`
- Strategy value key: `apex_indi`
- Source MQL indicator named by values: `APEX_Indi.mq4`

This indicator scans recent candles for an A-P-E setup followed by an X breakout. It is a trigger indicator, not a regime or risk model.

## Inputs

Call:

```python
apex_indi(
    candles,
    ap_diff=20,
    pe_diff=3,
    ex_diff=7,
    index=None,
)
```

Rules:

- Require at least `(ap_diff + pe_diff + ex_diff) + 8` candles.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate candles through that index.
- The scanner reviews at most `min(len(candles) - 3, (ap_diff + pe_diff + ex_diff) * 4)` historical shifts.
- `pe_diff` and `ex_diff` are part of the original parameter surface, but the current state-machine checks use fixed short windows around P and E.

## BUY State Machine

The scanner walks from older bars toward newer bars and maintains one `buy_state`.

1. Start BUY A when there is no active buy state and:

```text
current.open > current.close
current.high > previous.high
previous.close > previous.open
```

This records:

```text
a_index = current index
a_high = current.high
stage = A
```

2. While in stage A:
   - reset if `age > ap_diff`;
   - reset if a newer candle reaches or exceeds `a_high`;
   - advance to P when `age > 2`, current candle is bullish, and previous candle is bullish.

3. P records:

```text
p_index = current index - 1
stage = P
```

4. While in stage P, advance to E when:

```text
p_age < 2
current.high > previous.high
current.close > current.open
previous.close > previous.open
```

E records:

```text
e_index = current index
e_low = current.low
stage = E
```

5. While in stage E:
   - reset if `current.low < e_low`;
   - emit BUY X when a later candle breaks above `a_high` and closes bullish.

BUY event payload:

```text
direction = BUY
a_index
p_index
e_index
x_index
x_timestamp
x_price = current.high
```

## SELL State Machine

The scanner maintains one independent `sell_state`.

1. Start SELL A when no sell state exists and:

```text
current.open < current.close
current.low < previous.close
previous.close < previous.open
```

This records:

```text
a_index = current index
a_low = current.low
stage = A
```

2. While in stage A:
   - reset if `age > ap_diff`;
   - reset if a newer candle reaches or breaks below `a_low`;
   - advance to P when `older2` exists, `age > 2`, previous candle is bearish, and the candle two bars back is bullish.

3. P records:

```text
p_index = current index - 1
p_high = previous.high
stage = P
```

4. While in stage P:
   - reset if `current.high > p_high`;
   - advance to E when the next short-window bearish continuation appears:

```text
current index > p_index
current index - p_index < 2
current.low < previous.low
current.close < current.open
previous.close < previous.open
```

E records:

```text
e_index = current index
e_high = current.high
stage = E
```

5. While in stage E:
   - reset if `current.high > e_high`;
   - emit SELL X when a later candle breaks below `a_low` and closes bearish.

SELL event payload:

```text
direction = SELL
a_index
p_index
e_index
x_index
x_timestamp
x_price = current.low
```

## Signal Logic

If no events are found, return NEUTRAL with strength `0.0`, freshness `999`, and an empty `events` list.

For the latest event:

```text
freshness = latest_bar_index - latest.x_index
strength = clamp(0.78 - 0.08 * freshness, 0.0, 0.78)
```

If `freshness > 3`, return NEUTRAL with strength `0.0`; the last event is stale.
Otherwise return the latest event direction with the decayed strength and `x_price` as the signal level.

## Output

Signal:

```text
FeatureSignal(direction, strength, freshness, latest_x_price, reason)
```

Values include:

```text
source_indicator
latest_event
events
logic
```

Only the five latest events are retained in the values payload when events exist.

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `trigger_apex`. In scoring, APEX participates in the trigger group:

```text
trigger_buy = max(vwap_buy, apex_buy, (vwap_buy + power_buy + apex_buy) / 3.0)
trigger_sell = max(vwap_sell, apex_sell, (vwap_sell + power_sell + apex_sell) / 3.0)
```

An opposing trigger with strength at least `0.68` can block the opposite trade direction.

## Safety Boundaries

This skill describes a pattern trigger only. Do not treat an APEX event as a complete strategy. It must be evaluated with regime, structure, momentum, and risk context before any advisory decision is formed.

