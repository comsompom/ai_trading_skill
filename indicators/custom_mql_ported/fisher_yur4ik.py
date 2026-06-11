from __future__ import annotations

import math

from indicators.common import clamp
from skill.signal_schema import Candle, FeatureSignal


def fisher_series(candles: list[Candle], period: int = 10) -> list[float | None]:
    values: list[float | None] = []
    value_prev = 0.0
    fish_prev = 0.0
    for i, candle in enumerate(candles):
        if i < period - 1:
            values.append(None)
            continue
        window = candles[i - period + 1 : i + 1]
        max_high = max(c.high for c in window)
        min_low = min(c.low for c in window)
        price = (candle.high + candle.low) / 2.0
        span = max(max_high - min_low, 1e-12)
        value = 0.33 * 2.0 * ((price - min_low) / span - 0.5) + 0.67 * value_prev
        value = clamp(value, -0.999, 0.999)
        fish = 0.5 * math.log((1.0 + value) / (1.0 - value)) + 0.5 * fish_prev
        values.append(fish)
        value_prev = value
        fish_prev = fish
    return values


def fisher_transform(
    candles: list[Candle],
    period: int = 10,
    upper_level: float = 0.3,
    lower_level: float = -0.3,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < period + 2:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for Fisher regime"), {}
    i = len(candles) - 1 if index is None else index
    series = fisher_series(candles[: i + 1], period=period)
    current = series[i]
    previous = series[i - 1]
    if current is None or previous is None:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Fisher value is warming up"), {}
    direction = "NEUTRAL"
    strength = clamp(abs(current) / 1.8, 0.0, 1.0)
    reason = "Fisher is between bullish and bearish trigger levels"
    if current >= upper_level:
        direction = "BUY"
        strength = max(strength, 0.62 if previous < upper_level else 0.54)
        reason = "Fisher is bullish above upper threshold"
    elif current <= lower_level:
        direction = "SELL"
        strength = max(strength, 0.62 if previous > lower_level else 0.54)
        reason = "Fisher is bearish below lower threshold"
    return FeatureSignal(direction, clamp(strength, 0.0, 1.0), 0, current, reason), {
        "fisher": current,
        "previous_fisher": previous,
        "upper_level": upper_level,
        "lower_level": lower_level,
    }

