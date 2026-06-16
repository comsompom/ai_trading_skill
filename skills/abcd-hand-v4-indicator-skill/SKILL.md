---
name: abcd-hand-v4-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's ABCD_hand_v4 projection indicator logic, including A-B-C swing inference, D target projection, Fibonacci projection levels, signal direction, strength, freshness, and StrategySkill integration.
---

# ABCD Hand v4 Indicator Skill

## Role

You are the agent-facing operator for the repository's ABCD projection indicator.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/abcd_hand.py`
- Strategy feature key: `structure_abcd`
- Strategy value key: `abcd_hand_v4`
- Source MQL indicator named by values: `ABCD_hand_v4.mq4`

This indicator is structure context. It projects a D target from inferred A-B-C swing points and returns advisory BUY/SELL/NEUTRAL context based on where the current close sits relative to that projected D price.

## Inputs

Call:

```python
abcd_hand_projection(
    candles,
    p_level=0.5,
    lookback=120,
    wing=2,
    index=None,
)
```

Rules:

- `candles` must be normalized `Candle` objects with `timestamp`, `open`, `high`, `low`, `close`, and `volume`.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate candles up to and including that index.
- Return neutral when there are fewer than `max(20, wing * 2 + 4)` candles.
- Use `lookback=120` bars and `wing=2` swing detection by default.
- Use `p_level=0.5` for the D projection by default.

## Exact Logic

1. Scope the input to `candles[:index + 1]` or all candles when `index` is absent.
2. Infer swing points over the last `lookback` bars with `_swing_points`.
3. A candle is a swing high when its `high` is greater than or equal to every high in the centered `2 * wing + 1` window.
4. A candle is a swing low when its `low` is less than or equal to every low in the centered window.
5. Adjacent swing points of the same kind are compressed:
   - keep the higher price for consecutive highs;
   - keep the lower price for consecutive lows.
6. Use the last three alternating swing points as A, B, and C.
7. If fewer than three points exist, return `NEUTRAL` with strength `0.0`, freshness `999`, and no values.
8. Project D:

```text
D = C + p_level * abs(B - A)
```

9. Compute true ranges for the scoped candles and average the last 14 values for ATR.
10. Compute:

```text
distance_to_d = D - current_close
ab_span = max(abs(B - A), 1e-12)
freshness = current_index - C.index
```

11. If `distance_to_d > 0`, return BUY because there is upside room toward D:

```text
room_score = clamp(distance_to_d / max(ab_span, atr, 1e-12), 0.0, 1.0)
strength = clamp(0.30 + 0.25 * room_score, 0.0, 0.55)
level = D
```

12. If `abs(distance_to_d) <= max(0.25 * atr, 1e-12)`, return NEUTRAL because price is at the target:

```text
strength = 0.25
level = D
```

13. Otherwise return SELL because price is above the projected target:

```text
extension_score = clamp(abs(distance_to_d) / max(ab_span, atr, 1e-12), 0.0, 1.0)
strength = clamp(0.28 + 0.18 * extension_score, 0.0, 0.46)
level = D
```

## Fibonacci Projection Values

The values payload includes projection levels from C toward D. For each level:

```text
level_price = C + (D - C) * level
```

Levels:

```text
0, 0.146, 0.236, 0.382, 0.5, 0.618, 0.764, 1.0, 1.236, 1.618, -0.236, -0.618, -1.0
```

## Snap Helper

`snap_price_to_extreme` is available for MQL-style hand-clicked point behavior. It clamps the requested index, checks the three-candle neighborhood, and snaps the price to a nearby high or low when the supplied price is at or within `5 * point_size` of that extreme. The strategy path does not call this helper; it exists to preserve the ported indicator behavior.

## Output

Signal:

```text
FeatureSignal(direction, strength, freshness, level, reason)
```

Values include:

```text
source_indicator
p_level
points
d_target
d_timestamp
distance_to_d
fibonacci_levels
logic
```

## Strategy Integration

`StrategySkill._calculate_features()` stores the signal under `structure_abcd`. In scoring, ABCD contributes to the structure group at half weight inside the blended structure proxy:

```text
structure_buy = max(rolling_buy, (rolling_buy + 0.5 * abcd_buy + 0.8 * demark_buy + 0.4 * hl_buy) / 2.7)
structure_sell = max(rolling_sell, (rolling_sell + 0.5 * abcd_sell + 0.8 * demark_sell + 0.4 * hl_sell) / 2.7)
```

ABCD alone should not be treated as an execution trigger.

## Safety Boundaries

This skill describes deterministic indicator logic only. Do not convert the projection into a trade order. Treat D and Fibonacci levels as historical structure context, not guaranteed support, resistance, or future price targets.

