---
name: power-candle-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's Power_Candle_Alerts_v2 style range impulse proxy, including average range calculation, multiplier threshold, direction from candle body, strength, values, and StrategySkill trigger integration.
---

# Power Candle Indicator Skill

## Role

You are the agent-facing operator for the repository's power candle trigger proxy.
Use the implementation as the source of truth:

- Core implementation: `StrategySkill._power_candle()` in `skill/strategy_skill.py`
- Strategy feature key: `trigger_power_candle`
- Strategy value key: `power_candle`
- Strategy spec label: `Power_Candle_Alerts_v2 style range impulse`

This is a deterministic local proxy for large impulse candles. It is used as supporting trigger evidence.

## Inputs

Called internally as:

```python
StrategySkill._power_candle(
    candles,
    lookback=20,
    multiplier=1.7,
)
```

Rules:

- The public strategy requires at least 60 candles before feature calculation.
- The method evaluates only the latest closed candle in the supplied candle list.
- The average range excludes the current candle.
- Range is `high - low`, not true range.

## Exact Logic

1. Current candle:

```text
current = candles[-1]
```

2. Previous range sample:

```text
ranges = [c.high - c.low for c in candles[-lookback - 1 : -1]]
```

For default `lookback=20`, this uses the 20 candles before the current candle.

3. Average range:

```text
average_range = sum(ranges) / len(ranges)
```

4. Current range:

```text
current_range = current.high - current.low
```

5. Impulse condition:

```text
current_range >= average_range * multiplier
```

6. If impulse condition is true, direction comes from the candle body:

```text
BUY if current.close > current.open
SELL if current.close < current.open
NEUTRAL if current.close == current.open
```

Directional impulse signal:

```text
strength = 0.68
freshness = 0
level = current.close
reason = Impulse candle range exceeds recent average
```

7. If impulse condition is false:

```text
direction = NEUTRAL
strength = 0.0
freshness = 0
level = current.close
reason = No power candle impulse
```

## Output

Signal:

```text
FeatureSignal(direction, strength, 0, current.close, reason)
```

Values include:

```text
current_range
average_range
multiplier
```

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `trigger_power_candle`. Power candle participates in the trigger group:

```text
trigger_buy = max(vwap_buy, apex_buy, (vwap_buy + power_buy + apex_buy) / 3.0)
trigger_sell = max(vwap_sell, apex_sell, (vwap_sell + power_sell + apex_sell) / 3.0)
```

Because blocker checks look at all keys starting with `trigger`, an opposing power candle with strength `0.68` can block the opposite direction.

## Safety Boundaries

This skill describes a range impulse proxy only. Large range does not imply continuation by itself. Do not treat a power candle as an execution instruction without the broader strategy checks.

