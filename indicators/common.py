from __future__ import annotations

from collections.abc import Sequence


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sma(values: Sequence[float], period: int) -> list[float | None]:
    out: list[float | None] = []
    window_sum = 0.0
    for i, value in enumerate(values):
        window_sum += value
        if i >= period:
            window_sum -= values[i - period]
        out.append(window_sum / period if i >= period - 1 else None)
    return out


def ema(values: Sequence[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = []
    alpha = 2.0 / (period + 1.0)
    current: float | None = None
    for i, value in enumerate(values):
        if current is None:
            current = value if i == period - 1 else None
            if current is None:
                out.append(None)
                continue
        else:
            current = alpha * value + (1.0 - alpha) * current
        out.append(current)
    return out


def true_ranges(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]) -> list[float]:
    ranges = []
    for i, high in enumerate(highs):
        if i == 0:
            ranges.append(high - lows[i])
        else:
            ranges.append(max(high - lows[i], abs(high - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return ranges

