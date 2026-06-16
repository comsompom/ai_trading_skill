---
name: hl-signal-indicator-skill
description: Use this skill when an agent needs to explain, inspect, or apply the repository's HL_Signal session high/low reversal logic, including UTC session reset, high and low expansion tracking, BUY/SELL event conditions, freshness, strength decay, and StrategySkill integration.
---

# HL Signal Indicator Skill

## Role

You are the agent-facing operator for the repository's session high/low signal indicator.
Use the implementation as the source of truth:

- Core implementation: `indicators/custom_mql_ported/hl_signal.py`
- Strategy feature key: `structure_hl_session`
- Strategy value key: `hl_signal`
- Source MQL indicator named by values: `HL_Signal.mq4`

This indicator scans a UTC intraday session for failed high or low expansion events. It is structure context with short-lived reversal signals.

## Inputs

Call:

```python
hl_signal(
    candles,
    session_start_hour=9,
    session_end_hour=18,
    index=None,
)
```

Rules:

- Require at least 10 candles.
- If `index` is `None`, evaluate the latest closed candle.
- If `index` is provided, evaluate candles through that index.
- Session timestamps are interpreted in UTC.
- Only candles with `9 <= hour < 18` are scanned by default.
- State resets at each new UTC day.

## Session State

For each UTC day, initialize:

```text
prev_high = 0.0
prev_low = 0.0
res_high = 0.0
res_low = 0.0
buy_low = 0.0
sell_high = 0.0
```

The first in-session candle seeds `prev_high` and `prev_low`.

## BUY Event Logic

1. When an in-session candle makes a new session high:

```text
if candle.high > prev_high:
    res_high = candle.high
    prev_high = res_high
    buy_low = candle.low
```

2. After that high expansion, emit BUY when price fails below the breakout candle low:

```text
if res_high and candle.high < res_high and candle.high < buy_low:
    event direction = BUY
    event level = candle.low
```

3. After emitting BUY, reset high-side state:

```text
prev_high = 0.0
res_high = 0.0
buy_low = 0.0
```

## SELL Event Logic

1. When an in-session candle makes a new session low:

```text
if candle.low < prev_low:
    res_low = candle.low
    prev_low = res_low
    sell_high = candle.high
```

2. After that low expansion, emit SELL when price fails above the breakout candle high:

```text
if res_low and candle.low > res_low and candle.low > sell_high:
    event direction = SELL
    event level = candle.high
```

3. After emitting SELL, reset low-side state:

```text
prev_low = 0.0
res_low = 0.0
sell_high = 0.0
```

## Signal Logic

If no events are found, return NEUTRAL with strength `0.0`, freshness `999`, and an empty `events` list.

For the latest event:

```text
freshness = latest_bar_index - latest.event_index
```

If `freshness > 4`, return NEUTRAL with strength `0.0`; the event is stale.

Otherwise:

```text
strength = clamp(0.56 - 0.06 * freshness, 0.0, 0.56)
direction = latest.direction
level = latest.level
```

## Output

Signal:

```text
FeatureSignal(direction, strength, freshness, level, reason)
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

`StrategySkill._calculate_features()` stores this signal under `structure_hl_session`. In scoring, HL session contributes to the structure group at `0.4` weight inside the blended structure proxy. It is lower weight than DeMark and ABCD.

## Safety Boundaries

This skill describes deterministic session high/low reversal context only. The default session is UTC 09:00-18:00 and may not match an exchange-local session. Do not treat HL events as standalone execution instructions.

