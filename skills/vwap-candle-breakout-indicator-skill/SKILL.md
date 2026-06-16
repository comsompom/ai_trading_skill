---
name: vwap-candle-breakout-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's VWAP_CANDLE_BREAKOUT_slope_dir_line trigger logic, including session VWAP reset, slope line calculation, body threshold, bullish and bearish close crosses, strength, and StrategySkill integration.
---

# VWAP Candle Breakout Indicator Skill

## Role

You are the agent-facing operator for the repository's VWAP candle breakout trigger.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/vwap_candle_breakout.py`
- Strategy feature key: `trigger_vwap`
- Strategy value key: `vwap_candle_breakout`
- Source listed in strategy spec: `VWAP_CANDLE_BREAKOUT_slope_dir_line`

This indicator requires a closed-candle VWAP cross, candle body confirmation, and slope-line direction agreement.

## Inputs

Call:

```python
vwap_candle_breakout(
    candles,
    body_atr_fraction=0.12,
    slope_period=32,
    index=None,
)
```

Rules:

- Require at least `slope_period + 2` candles.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate candles through that index.
- VWAP resets by UTC day using `timestamp // 86400`.
- Candle body threshold uses average high-low range, not ATR true range.

## Session VWAP Logic

For each candle:

1. Reset `pv_total` and `vol_total` when `timestamp // 86400` changes.
2. Typical price:

```text
typical = (open + high + low + close) / 4.0
```

3. Volume:

```text
volume = max(candle.volume, 0.0)
```

4. Update:

```text
pv_total += typical * volume
vol_total += volume
```

5. VWAP:

```text
vwap = pv_total / vol_total if vol_total > 0 else typical
```

## Slope Line Logic

The slope line is a Hull-style EMA transform:

```text
half = max(1, round(period / 2))
sqrt_period = max(1, round(sqrt(period)))
fast = ema(closes, half)
slow = ema(closes, period)
diff = 2.0 * fast - slow where both exist
clean = close when diff is None else diff
slope_line = ema(clean, sqrt_period)
```

For the default `slope_period=32`, `half=16` and `sqrt_period=6`.

## Breakout Conditions

The signal uses the previous and current candles:

```text
bullish_cross = previous.close <= previous_vwap and current.close > current_vwap
bearish_cross = previous.close >= previous_vwap and current.close < current_vwap
slope_up = current_slope > previous_slope
slope_down = current_slope < previous_slope
body = abs(current.close - current.open)
avg_range = average(high - low over last up to 21 candles)
min_body = avg_range * body_atr_fraction
body_ok = body >= min_body
```

BUY requires all:

```text
bullish_cross
current.close > current.open
body_ok
slope_up
```

SELL requires all:

```text
bearish_cross
current.close < current.open
body_ok
slope_down
```

Otherwise the indicator returns NEUTRAL.

## Strength Logic

Directional strength:

```text
strength = clamp(0.58 + body / max(avg_range, 1e-12) * 0.28, 0.0, 1.0)
```

Neutral strength is `0.0`.

## Output

Signal:

```text
FeatureSignal(direction, strength, 0, current_vwap, reason)
```

Values include:

```text
vwap
slope_line
body
avg_range
body_threshold
slope_direction
```

`slope_direction` is `"UP"`, `"DOWN"`, or `"FLAT"` based on the slope comparison.

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `trigger_vwap`. In scoring, VWAP participates in the trigger group:

```text
trigger_buy = max(vwap_buy, apex_buy, (vwap_buy + power_buy + apex_buy) / 3.0)
trigger_sell = max(vwap_sell, apex_sell, (vwap_sell + power_sell + apex_sell) / 3.0)
```

An opposing trigger with strength at least `0.68` can block the opposite trade direction.

## Safety Boundaries

This skill describes a closed-candle trigger only. It does not include slippage, fees, order placement, or risk sizing. Do not convert a VWAP cross into a standalone trade order.

