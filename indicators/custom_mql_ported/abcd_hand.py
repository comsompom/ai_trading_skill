from __future__ import annotations

from dataclasses import dataclass

from indicators.common import clamp, true_ranges
from skill.signal_schema import Candle, FeatureSignal


FIBO_LEVELS = (
    0.0,
    0.146,
    0.236,
    0.382,
    0.5,
    0.618,
    0.764,
    1.0,
    1.236,
    1.618,
    -0.236,
    -0.618,
    -1.0,
)


@dataclass(frozen=True)
class ABCDPoint:
    label: str
    index: int
    timestamp: int
    price: float
    kind: str

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "index": self.index,
            "timestamp": self.timestamp,
            "price": self.price,
            "kind": self.kind,
        }


def snap_price_to_extreme(
    candles: list[Candle],
    index: int,
    price: float,
    point_size: float = 0.0,
) -> tuple[int, float, str]:
    if not candles:
        raise ValueError("candles must not be empty")
    index = max(0, min(index, len(candles) - 1))
    start = max(0, index - 1)
    end = min(len(candles), index + 2)
    window = candles[start:end]
    high_offset, high_candle = max(enumerate(window, start=start), key=lambda item: item[1].high)
    low_offset, low_candle = min(enumerate(window, start=start), key=lambda item: item[1].low)
    snap_distance = 5.0 * max(point_size, 0.0)
    if price <= low_candle.low or abs(price - low_candle.low) <= snap_distance:
        return low_offset, low_candle.low, "LOW"
    if price >= high_candle.high or abs(price - high_candle.high) <= snap_distance:
        return high_offset, high_candle.high, "HIGH"
    return index, price, "PRICE"


def project_d_target(a_price: float, b_price: float, c_price: float, p_level: float = 0.5) -> float:
    return c_price + p_level * abs(b_price - a_price)


def fibonacci_projection_levels(c_price: float, d_price: float) -> dict[str, float]:
    span = d_price - c_price
    return {f"{level:g}": c_price + span * level for level in FIBO_LEVELS}


def _swing_points(candles: list[Candle], lookback: int, wing: int) -> list[ABCDPoint]:
    start = max(wing, len(candles) - lookback)
    points: list[ABCDPoint] = []
    for i in range(start, len(candles) - wing):
        window = candles[i - wing : i + wing + 1]
        candle = candles[i]
        if candle.high >= max(c.high for c in window):
            points.append(ABCDPoint("", i, candle.timestamp, candle.high, "HIGH"))
        if candle.low <= min(c.low for c in window):
            points.append(ABCDPoint("", i, candle.timestamp, candle.low, "LOW"))

    alternating: list[ABCDPoint] = []
    for point in points:
        if not alternating or point.kind != alternating[-1].kind:
            alternating.append(point)
            continue
        previous = alternating[-1]
        if point.kind == "HIGH" and point.price > previous.price:
            alternating[-1] = point
        elif point.kind == "LOW" and point.price < previous.price:
            alternating[-1] = point
    return alternating


def infer_abcd_points(candles: list[Candle], lookback: int = 120, wing: int = 2) -> list[ABCDPoint]:
    points = _swing_points(candles, lookback=lookback, wing=wing)
    if len(points) < 3:
        return []
    selected = points[-3:]
    return [
        ABCDPoint(label, point.index, point.timestamp, point.price, point.kind)
        for label, point in zip(("A", "B", "C"), selected, strict=True)
    ]


def abcd_hand_projection(
    candles: list[Candle],
    p_level: float = 0.5,
    lookback: int = 120,
    wing: int = 2,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < max(20, wing * 2 + 4):
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for ABCD projection"), {}
    i = len(candles) - 1 if index is None else index
    scoped = candles[: i + 1]
    points = infer_abcd_points(scoped, lookback=lookback, wing=wing)
    if len(points) < 3:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "No complete A-B-C swing sequence for ABCD projection"), {}

    a_point, b_point, c_point = points
    d_price = project_d_target(a_point.price, b_point.price, c_point.price, p_level=p_level)
    current = scoped[-1]
    ranges = true_ranges([c.high for c in scoped], [c.low for c in scoped], [c.close for c in scoped])
    atr = sum(ranges[-14:]) / min(14, len(ranges))
    distance_to_d = d_price - current.close
    ab_span = max(abs(b_point.price - a_point.price), 1e-12)
    freshness = max(0, i - c_point.index)

    direction = "NEUTRAL"
    strength = 0.18
    reason = "ABCD projection is context only"
    if distance_to_d > 0:
        room_score = clamp(distance_to_d / max(ab_span, atr, 1e-12), 0.0, 1.0)
        direction = "BUY"
        strength = clamp(0.30 + 0.25 * room_score, 0.0, 0.55)
        reason = "ABCD hand projection leaves upside room toward D target"
    elif abs(distance_to_d) <= max(0.25 * atr, 1e-12):
        direction = "NEUTRAL"
        strength = 0.25
        reason = "Price is at the ABCD projected D target"
    else:
        direction = "SELL"
        extension_score = clamp(abs(distance_to_d) / max(ab_span, atr, 1e-12), 0.0, 1.0)
        strength = clamp(0.28 + 0.18 * extension_score, 0.0, 0.46)
        reason = "Price is above the ABCD projected D target"

    values = {
        "source_indicator": "ABCD_hand_v4.mq4",
        "p_level": p_level,
        "points": [point.to_dict() for point in points],
        "d_target": d_price,
        "d_timestamp": current.timestamp,
        "distance_to_d": distance_to_d,
        "fibonacci_levels": fibonacci_projection_levels(c_point.price, d_price),
        "logic": "D = C + PLevel * abs(B - A); click points snap to nearby 3-bar high/low extremes in the MQL indicator.",
    }
    return FeatureSignal(direction, strength, freshness, d_price, reason), values
