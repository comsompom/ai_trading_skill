---
name: rsi-mfi-ma3-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's RSI_MFI_MA3 momentum logic, including RSI smoothing, MFI money flow, combined EMA baseline, bullish and bearish votes, price-direction confirmation, strength, and StrategySkill integration.
---

# RSI MFI MA3 Indicator Skill

## Role

You are the agent-facing operator for the repository's RSI/MFI momentum participation indicator.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/rsi_mfi_ma3.py`
- Public wrapper: `indicators/rsi.py`
- Strategy feature key: `momentum_rsi_mfi`
- Strategy value key: `rsi_mfi_ma3`
- Source listed in strategy spec: `RSI_MFI_MA3`

This indicator compares current RSI and MFI against a combined EMA baseline and requires the current close to agree with the direction.

## Inputs

Call:

```python
rsi_mfi_ma3(
    candles,
    rsi_period=19,
    mfi_period=19,
    ma_period=50,
    index=None,
)
```

Rules:

- Require at least `rsi_period + mfi_period + ma_period` candles.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate candles through that index.
- Return neutral if RSI, MFI, or the combined MA is still warming up.

## RSI Logic

`rsi(values, period=19)`:

1. Start output with `[None]`.
2. For each price change:

```text
gain = max(change, 0.0)
loss = max(-change, 0.0)
```

3. Return `None` until index `period`.
4. First averages:

```text
avg_gain = average(last period gains)
avg_loss = average(last period losses)
```

5. Later averages use Wilder-style smoothing:

```text
avg_gain = (avg_gain * (period - 1) + gain) / period
avg_loss = (avg_loss * (period - 1) + loss) / period
```

6. RSI:

```text
100.0 if avg_loss == 0
else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
```

## MFI Logic

`mfi(candles, period=19)`:

1. Typical price:

```text
typical = (high + low + close) / 3.0
```

2. Money flow:

```text
flow = typical * max(volume, 0.0)
```

3. Return `None` until index `period`.
4. For the rolling period, classify each bar from `i - period + 1` through `i`:

```text
positive += flow[j] if typical[j] >= typical[j - 1]
negative += flow[j] if typical[j] < typical[j - 1]
```

5. MFI:

```text
100.0 if negative == 0
else 100.0 - 100.0 / (1.0 + positive / negative)
```

## Combined MA Logic

1. Replace warming RSI values with `50.0`.
2. Replace warming MFI values with `50.0`.
3. Compute EMA of cleaned RSI with `ma_period=50`.
4. Compute EMA of cleaned MFI with `ma_period=50`.
5. Combined MA:

```text
combined_ma[j] = None if either EMA is None else (rsi_ema[j] + mfi_ema[j]) / 2.0
```

6. The signal uses the previous combined MA when available:

```text
ma = combined_ma[index - 1] if index > 0 else combined_ma[index]
```

## Signal Logic

Current direction confirmation:

```text
rising = current.close > previous.close
falling = current.close < previous.close
```

Votes:

```text
bullish_votes = int(current_rsi > ma) + int(current_mfi > ma)
bearish_votes = int(current_rsi < ma) + int(current_mfi < ma)
```

BUY:

```text
if bullish_votes and rising:
    strength = clamp(0.42 + 0.22 * bullish_votes, 0.0, 1.0)
```

SELL:

```text
if bearish_votes and falling:
    strength = clamp(0.42 + 0.22 * bearish_votes, 0.0, 1.0)
```

NEUTRAL:

```text
strength = 0.2
reason = RSI/MFI participation does not agree with price direction
```

One vote yields `0.64` strength. Two votes yield `0.86` strength.

## Output

Signal:

```text
FeatureSignal(direction, strength, 0, combined_ma, reason)
```

Values include:

```text
rsi
mfi
combined_ma
bullish_votes or bearish_votes when directional
```

## Strategy Integration

`StrategySkill._calculate_features()` stores this signal under `momentum_rsi_mfi`. In scoring, it is averaged equally with MACD OsMA:

```text
momentum_buy = (rsi_buy + osma_buy) / 2.0
momentum_sell = (rsi_sell + osma_sell) / 2.0
```

The momentum group contributes 20% to the final buy and sell scores.

## Safety Boundaries

This skill describes momentum participation only. It does not evaluate structure, reward/risk, or trigger validity and must not be used as a standalone trade order.

