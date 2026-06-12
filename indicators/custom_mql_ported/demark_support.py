from __future__ import annotations

from indicators.common import clamp, true_ranges
from skill.signal_schema import Candle, FeatureSignal


def demark_support(
    candles: list[Candle],
    number_bars: int = 300,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < 30:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for DeMark support/resistance"), {}
    i = len(candles) - 1 if index is None else index
    scoped = candles[: i + 1]
    lookback = scoped[-min(number_bars, len(scoped)) :]
    offset = len(scoped) - len(lookback)
    low_rel, low_candle = min(enumerate(lookback), key=lambda item: item[1].low)
    high_rel, high_candle = max(enumerate(lookback), key=lambda item: item[1].high)
    low_idx = offset + low_rel
    high_idx = offset + high_rel

    values = {"source_indicator": "De_Mark_Support_V2.mq4", "number_bars": number_bars}
    if len(scoped) - max(low_idx, high_idx) <= 20:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "DeMark anchor is too recent"), values

    if low_idx > high_idx:
        line = _support_line(scoped, low_idx)
        if line is None:
            return FeatureSignal("NEUTRAL", 0.0, 999, None, "No valid DeMark support line"), values
        return _support_breakout(scoped, line, values)
    if high_idx > low_idx:
        line = _resistance_line(scoped, high_idx)
        if line is None:
            return FeatureSignal("NEUTRAL", 0.0, 999, None, "No valid DeMark resistance line"), values
        return _resistance_breakout(scoped, line, values)
    return FeatureSignal("NEUTRAL", 0.0, 999, None, "No DeMark support/resistance bias"), values


def _support_line(candles: list[Candle], low_idx: int) -> dict | None:
    if low_idx < 3:
        return None
    angle = (candles[low_idx - 2].low - candles[low_idx].low) / 2.0
    second_idx = low_idx - 2
    for idx in range(low_idx - 3, len(candles)):
        if idx == low_idx:
            continue
        bars = abs(idx - low_idx) + 1
        current_angle = (candles[idx].low - candles[low_idx].low) / bars
        if current_angle < angle:
            angle = current_angle
            second_idx = idx
    current_idx = len(candles) - 1
    line_price = candles[low_idx].low + angle * abs(current_idx - low_idx)
    return {"kind": "support", "anchor_index": low_idx, "second_index": second_idx, "angle": angle, "line_price": line_price}


def _resistance_line(candles: list[Candle], high_idx: int) -> dict | None:
    if high_idx < 3:
        return None
    angle = (candles[high_idx].high - candles[high_idx - 2].high) / 2.0
    second_idx = high_idx - 2
    for idx in range(high_idx - 3, len(candles)):
        if idx == high_idx:
            continue
        bars = abs(idx - high_idx) + 1
        current_angle = (candles[high_idx].high - candles[idx].high) / bars
        if current_angle < angle:
            angle = current_angle
            second_idx = idx
    current_idx = len(candles) - 1
    line_price = candles[high_idx].high - angle * abs(current_idx - high_idx)
    return {"kind": "resistance", "anchor_index": high_idx, "second_index": second_idx, "angle": angle, "line_price": line_price}


def _support_breakout(candles: list[Candle], line: dict, values: dict) -> tuple[FeatureSignal, dict]:
    current = candles[-1]
    previous = candles[-2]
    prior = candles[-3]
    line_price = line["line_price"]
    td = None
    if current.close < line_price:
        if previous.close > prior.close:
            td = "TD1"
        elif current.open < line_price:
            td = "TD2"
        elif previous.close - (current.high - current.close) > line_price:
            td = "TD3"
    target = None
    if td:
        high_close_idx, high_close_candle = max(enumerate(candles[line["anchor_index"] :], start=line["anchor_index"]), key=lambda item: item[1].close)
        projected_at_high = candles[line["anchor_index"]].low + line["angle"] * abs(high_close_idx - line["anchor_index"])
        target = line_price - (high_close_candle.close - projected_at_high)
    values.update({"line": line, "td_break": td, "target": target})
    if not td:
        return FeatureSignal("NEUTRAL", 0.15, 0, line_price, "Price has not broken DeMark support"), values
    strength = _breakout_strength(candles, abs(current.close - line_price))
    return FeatureSignal("SELL", strength, 0, target, f"DeMark support breakthrough by {td}"), values


def _resistance_breakout(candles: list[Candle], line: dict, values: dict) -> tuple[FeatureSignal, dict]:
    current = candles[-1]
    previous = candles[-2]
    prior = candles[-3]
    line_price = line["line_price"]
    td = None
    if current.close > line_price:
        if previous.close < prior.close:
            td = "TD1"
        elif current.open > line_price:
            td = "TD2"
        elif previous.close - (current.high - current.close) < line_price:
            td = "TD3"
    target = None
    if td:
        low_idx, low_candle = min(enumerate(candles[line["anchor_index"] :], start=line["anchor_index"]), key=lambda item: item[1].low)
        projected_at_low = candles[line["anchor_index"]].high - line["angle"] * abs(low_idx - line["anchor_index"])
        target = line_price + (low_candle.close - projected_at_low)
    values.update({"line": line, "td_break": td, "target": target})
    if not td:
        return FeatureSignal("NEUTRAL", 0.15, 0, line_price, "Price has not broken DeMark resistance"), values
    strength = _breakout_strength(candles, abs(current.close - line_price))
    return FeatureSignal("BUY", strength, 0, target, f"DeMark resistance breakthrough by {td}"), values


def _breakout_strength(candles: list[Candle], distance: float) -> float:
    ranges = true_ranges([c.high for c in candles], [c.low for c in candles], [c.close for c in candles])
    atr = sum(ranges[-14:]) / min(14, len(ranges))
    return clamp(0.62 + distance / max(atr * 2.0, 1e-12) * 0.24, 0.0, 0.86)
