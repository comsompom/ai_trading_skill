---
name: rolling-structure-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's rolling high/low structure proxy, including support/resistance window selection, breakout and midpoint logic, signal strength, values, and StrategySkill structure scoring.
---

# Rolling Structure Indicator Skill

## Role

You are the agent-facing operator for the repository's rolling high/low structure proxy.
Use the implementation as the source of truth:

- Core implementation: `StrategySkill._rolling_structure()` in `skill/strategy_skill.py`
- Strategy feature key: `structure`
- Strategy value key: `rolling_structure`
- Strategy spec label: `Rolling high/low structure proxy`

This is not an external MQL port. It is a deterministic local structure proxy used as the baseline structure component.

## Inputs

Called internally as:

```python
StrategySkill._rolling_structure(candles, lookback=24)
```

Rules:

- The public strategy requires at least 60 candles before feature calculation.
- The method itself expects enough candles to form `candles[-lookback - 1:-1]`.
- It evaluates only the latest closed candle in the supplied candle list.
- The current candle is excluded from support/resistance calculation.

## Exact Logic

1. Current candle:

```text
current = candles[-1]
```

2. Previous structure window:

```text
previous_window = candles[-lookback - 1 : -1]
```

For default `lookback=24`, this is the 24 candles before the current candle.

3. Resistance:

```text
resistance = max(c.high for c in previous_window)
```

4. Support:

```text
support = min(c.low for c in previous_window)
```

5. BUY breakout:

```text
if current.close > resistance:
    direction = BUY
    strength = 0.72
    freshness = 0
    level = resistance
    reason = Close broke above rolling resistance
```

6. SELL breakout:

```text
if current.close < support:
    direction = SELL
    strength = 0.72
    freshness = 0
    level = support
    reason = Close broke below rolling support
```

7. Inside structure:

```text
midpoint = (resistance + support) / 2.0
direction = BUY if current.close > midpoint
direction = SELL if current.close < midpoint
direction = NEUTRAL if current.close == midpoint
strength = 0.28
freshness = 0
level = midpoint
reason = Price remains inside rolling structure
```

## Output

Signal:

```text
FeatureSignal(direction, strength, 0, level, reason)
```

Values for breakout states:

```text
rolling_resistance
rolling_support
```

Values for inside-structure states:

```text
rolling_resistance
rolling_support
midpoint
```

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `structure`. It is the primary baseline for the structure group.

The structure group then blends this proxy with ABCD, DeMark, and HL session context:

```text
structure_buy = max(rolling_buy, (rolling_buy + 0.5 * abcd_buy + 0.8 * demark_buy + 0.4 * hl_buy) / 2.7)
structure_sell = max(rolling_sell, (rolling_sell + 0.5 * abcd_sell + 0.8 * demark_sell + 0.4 * hl_sell) / 2.7)
```

The structure group contributes 25% to the final buy and sell scores.

## Safety Boundaries

This skill describes a simple rolling-window proxy. It does not identify complex market structure, liquidity, or higher-timeframe levels. Do not treat an inside-window directional bias with strength `0.28` as a breakout.

