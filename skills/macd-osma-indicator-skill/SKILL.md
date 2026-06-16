---
name: macd-osma-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's MACD_OSMA_Bar_alert momentum logic, including fast and slow EMA calculation, signal EMA, OsMA histogram, slope/candle confirmation, strength, and StrategySkill integration.
---

# MACD OsMA Indicator Skill

## Role

You are the agent-facing operator for the repository's MACD OsMA momentum indicator.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/macd_osma.py`
- Public wrapper: `indicators/macd.py`
- Strategy feature key: `momentum_osma`
- Strategy value key: `macd_osma`
- Source listed in strategy spec: `MACD_OSMA_Bar_alert`

This indicator measures MACD histogram direction and requires candle agreement for stronger signals.

## Inputs

Call:

```python
macd_osma(
    candles,
    fast=2,
    slow=8,
    signal=6,
    multiplier=2.0,
    index=None,
)
```

Rules:

- Require at least `slow + signal + 3` candles.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate closes through that index.
- EMA uses the repository's `ema()` helper.
- `multiplier` is floored at `1.0` before applying to OsMA.

## EMA Helper Behavior

The shared EMA helper uses:

```text
alpha = 2.0 / (period + 1.0)
```

Warm-up behavior:

- returns `None` until index `period - 1`;
- seeds the first EMA value with the raw value at index `period - 1`;
- then applies standard recursive EMA:

```text
ema = alpha * value + (1.0 - alpha) * previous_ema
```

## Exact Logic

1. Extract closes through the evaluation index.
2. Compute fast EMA with period `2`.
3. Compute slow EMA with period `8`.
4. Compute MACD line:

```text
macd_line[j] = 0.0 if fast_ema[j] is None or slow_ema[j] is None else fast_ema[j] - slow_ema[j]
```

5. Compute signal EMA over `macd_line` with period `6`.
6. Compute OsMA:

```text
osma[j] = None if signal_ema[j] is None else (macd_line[j] - signal_ema[j]) * max(multiplier, 1.0)
```

7. Read current and previous OsMA. Return NEUTRAL if either is `None`.
8. Compute slope:

```text
slope = current_osma - previous_osma
```

9. Compute average absolute OsMA over the last up to 21 bars:

```text
avg_abs = average(abs(non_none_osma_values from max(0, index - 20) through index))
```

10. Compute base strength:

```text
strength = clamp(abs(current_osma) / max(avg_abs * 2.0, 1e-12), 0.0, 1.0)
```

## Signal Logic

Strong BUY:

```text
current_osma < 0
current candle is bullish
slope > 0
direction = BUY
strength = max(0.52, base_strength)
```

Strong SELL:

```text
current_osma > 0
current candle is bearish
slope < 0
direction = SELL
strength = max(0.52, base_strength)
```

Slope-only signal:

```text
direction = BUY if slope > 0
direction = SELL if slope < 0
direction = NEUTRAL if slope == 0
strength = min(0.45, base_strength)
```

Slope-only signals deliberately stay below the stronger confirmation floor.

## Output

Signal:

```text
FeatureSignal(direction, strength, 0, current_osma, reason)
```

Values include:

```text
osma
osma_slope
macd
```

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `momentum_osma`. In scoring, it is averaged equally with RSI/MFI:

```text
momentum_buy = (rsi_buy + osma_buy) / 2.0
momentum_sell = (rsi_sell + osma_sell) / 2.0
```

The momentum group contributes 20% to the final buy and sell scores.

## Safety Boundaries

This skill describes momentum logic only. OsMA slope or candle confirmation is not a complete strategy and should not be used as a trade order without structure, trigger, regime, and risk context.

