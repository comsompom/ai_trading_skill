---
name: fisher-yur4ik-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's Fisher_Yur4ik Fisher transform regime indicator, including rolling high/low normalization, recursive Fisher calculation, threshold crossing logic, strength, and StrategySkill regime integration.
---

# Fisher Yur4ik Indicator Skill

## Role

You are the agent-facing operator for the repository's Fisher transform regime indicator.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/fisher_yur4ik.py`
- Strategy feature key: `regime`
- Strategy value key: `fisher_yur4ik`
- Source listed in strategy spec: `Fisher_Yur4ik3-a_v6_MTF core Fisher transform`

This indicator converts recent price location inside a high/low channel into a smoothed Fisher value. It provides bullish, bearish, or neutral regime context.

## Inputs

Call:

```python
fisher_transform(
    candles,
    period=10,
    upper_level=0.3,
    lower_level=-0.3,
    index=None,
)
```

Rules:

- Require at least `period + 2` candles.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate candles through that index.
- Values before `period - 1` are warm-up `None`.
- Return neutral if current or previous Fisher value is still warming up.

## Fisher Series Logic

The series calculation uses two recursive state variables:

```text
value_prev = 0.0
fish_prev = 0.0
```

For each candle after warm-up:

1. Use the latest `period` candles.
2. Compute:

```text
max_high = max(window.high)
min_low = min(window.low)
price = (current.high + current.low) / 2.0
span = max(max_high - min_low, 1e-12)
```

3. Normalize and smooth:

```text
value = 0.33 * 2.0 * ((price - min_low) / span - 0.5) + 0.67 * value_prev
value = clamp(value, -0.999, 0.999)
```

4. Fisher transform and smooth:

```text
fish = 0.5 * log((1.0 + value) / (1.0 - value)) + 0.5 * fish_prev
```

5. Store `fish`, then update `value_prev` and `fish_prev`.

## Signal Logic

For the evaluation index:

```text
current = fisher_series[index]
previous = fisher_series[index - 1]
base_strength = clamp(abs(current) / 1.8, 0.0, 1.0)
```

Default signal:

```text
direction = NEUTRAL
strength = base_strength
reason = Fisher is between bullish and bearish trigger levels
```

Bullish regime:

```text
if current >= upper_level:
    direction = BUY
    strength = max(base_strength, 0.62 if previous < upper_level else 0.54)
```

Bearish regime:

```text
if current <= lower_level:
    direction = SELL
    strength = max(base_strength, 0.62 if previous > lower_level else 0.54)
```

Final strength is clamped to `[0.0, 1.0]`.

The crossing bar gets a minimum strength of `0.62`; continued regime gets a minimum strength of `0.54`.

## Output

Signal:

```text
FeatureSignal(direction, strength, 0, current_fisher, reason)
```

Values include:

```text
fisher
previous_fisher
upper_level
lower_level
```

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `regime`. Regime contributes 25% of the final buy and sell score:

```text
buy_score += 0.25 * regime_buy
sell_score += 0.25 * regime_sell
```

Fisher does not set stops, targets, or trigger blocks.

## Safety Boundaries

This skill describes regime classification only. Do not use Fisher alone as a trade decision. A strong Fisher value means price is stretched inside its recent high/low transform, not that continuation is guaranteed.

