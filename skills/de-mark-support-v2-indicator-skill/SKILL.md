---
name: de-mark-support-v2-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's De_Mark_Support_V2 support/resistance line logic, including anchor selection, support and resistance line construction, TD1/TD2/TD3 breakout checks, target calculation, strength, and StrategySkill integration.
---

# De Mark Support v2 Indicator Skill

## Role

You are the agent-facing operator for the repository's DeMark support/resistance breakout indicator.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/demark_support.py`
- Strategy feature key: `structure_demark`
- Strategy value key: `de_mark_support_v2`
- Source MQL indicator named by values: `De_Mark_Support_V2.mq4`

This indicator builds a support or resistance line from the dominant historical extreme and checks whether the current closed candle has broken it using TD-style confirmation rules.

## Inputs

Call:

```python
demark_support(
    candles,
    number_bars=300,
    index=None,
)
```

Rules:

- Require at least 30 candles.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate candles through that index.
- The anchor search uses the last `min(number_bars, len(scoped))` candles.
- Return neutral if the selected high/low anchor is within 20 bars of the current candle.

## Anchor Selection

1. Scope candles through the evaluation index.
2. Search the lookback window for:

```text
lowest low candle
highest high candle
```

3. Convert relative positions back to full scoped indexes.
4. If the low anchor is newer than the high anchor, build a support line.
5. If the high anchor is newer than the low anchor, build a resistance line.
6. If both anchors are the same index, return NEUTRAL.

## Support Line Construction

Support requires `low_idx >= 3`.

Initial values:

```text
angle = (low[low_idx - 2] - low[low_idx]) / 2.0
second_idx = low_idx - 2
```

Then scan from `low_idx - 3` through the full scoped candle list, skipping `low_idx`.
For each candidate:

```text
bars = abs(candidate_idx - low_idx) + 1
current_angle = (candidate.low - anchor.low) / bars
```

If `current_angle < angle`, replace `angle` and `second_idx`.

Current line price:

```text
line_price = anchor.low + angle * abs(current_idx - low_idx)
```

The line payload is:

```text
kind = support
anchor_index
second_index
angle
line_price
```

## Resistance Line Construction

Resistance requires `high_idx >= 3`.

Initial values:

```text
angle = (high[high_idx] - high[high_idx - 2]) / 2.0
second_idx = high_idx - 2
```

Then scan from `high_idx - 3` through the scoped candles, skipping `high_idx`.
For each candidate:

```text
bars = abs(candidate_idx - high_idx) + 1
current_angle = (anchor.high - candidate.high) / bars
```

If `current_angle < angle`, replace `angle` and `second_idx`.

Current line price:

```text
line_price = anchor.high - angle * abs(current_idx - high_idx)
```

The line payload is:

```text
kind = resistance
anchor_index
second_index
angle
line_price
```

## Support Breakout Logic

For a support line, use the current, previous, and prior candles.

Only test TD rules when:

```text
current.close < line_price
```

Then assign the first matching TD break:

```text
TD1 if previous.close > prior.close
TD2 else if current.open < line_price
TD3 else if previous.close - (current.high - current.close) > line_price
```

If no TD rule matches, return NEUTRAL with strength `0.15`, freshness `0`, level `line_price`, and reason "Price has not broken DeMark support".

If TD exists, compute target:

```text
high_close_candle = candle with max close from anchor_index onward
projected_at_high = anchor.low + angle * abs(high_close_idx - anchor_index)
target = line_price - (high_close_candle.close - projected_at_high)
```

Return SELL with breakout strength and target.

## Resistance Breakout Logic

Only test TD rules when:

```text
current.close > line_price
```

Then assign the first matching TD break:

```text
TD1 if previous.close < prior.close
TD2 else if current.open > line_price
TD3 else if previous.close - (current.high - current.close) < line_price
```

If no TD rule matches, return NEUTRAL with strength `0.15`, freshness `0`, level `line_price`, and reason "Price has not broken DeMark resistance".

If TD exists, compute target:

```text
low_candle = candle with min low from anchor_index onward
projected_at_low = anchor.high - angle * abs(low_idx - anchor_index)
target = line_price + (low_candle.close - projected_at_low)
```

Return BUY with breakout strength and target.

## Strength Logic

For confirmed breakouts:

```text
atr = average true range over the last 14 candles
distance = abs(current.close - line_price)
strength = clamp(0.62 + distance / max(atr * 2.0, 1e-12) * 0.24, 0.0, 0.86)
```

## Output

Signal:

```text
FeatureSignal(direction, strength, freshness, level, reason)
```

Values include:

```text
source_indicator
number_bars
line
td_break
target
```

The signal `level` is the breakout target when a TD break exists; it is the line price for unbroken neutral states.

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `structure_demark`. In scoring, DeMark contributes to the structure group at `0.8` weight inside the blended structure proxy. It is stronger than ABCD and HL session context but still part of structure, not a standalone trigger.

## Safety Boundaries

This skill describes deterministic support/resistance breakout logic only. Do not treat the TD target as guaranteed. Do not issue trade orders from this indicator alone.

