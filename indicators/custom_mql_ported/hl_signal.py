from __future__ import annotations

from datetime import datetime, timezone

from indicators.common import clamp
from skill.signal_schema import Candle, FeatureSignal


def hl_signal(
    candles: list[Candle],
    session_start_hour: int = 9,
    session_end_hour: int = 18,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < 10:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for HL signal"), {}
    i = len(candles) - 1 if index is None else index
    scoped = candles[: i + 1]
    events = _scan_hl(scoped, session_start_hour=session_start_hour, session_end_hour=session_end_hour)
    if not events:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "No session high/low signal"), {
            "source_indicator": "HL_Signal.mq4",
            "events": [],
        }
    latest = events[-1]
    freshness = len(scoped) - 1 - latest["index"]
    if freshness > 4:
        return FeatureSignal("NEUTRAL", 0.0, freshness, latest["level"], "Last HL session signal is stale"), {
            "source_indicator": "HL_Signal.mq4",
            "latest_event": latest,
            "events": events[-5:],
        }
    strength = clamp(0.56 - 0.06 * freshness, 0.0, 0.56)
    return FeatureSignal(
        latest["direction"],
        strength,
        freshness,
        latest["level"],
        f"HL session {latest['direction']} signal from 09:00-18:00 high/low reset logic",
    ), {
        "source_indicator": "HL_Signal.mq4",
        "latest_event": latest,
        "events": events[-5:],
        "logic": "Tracks session highs/lows; BUY after high expansion fails below breakout candle low, SELL after low expansion fails above breakout candle high.",
    }


def _scan_hl(candles: list[Candle], session_start_hour: int, session_end_hour: int) -> list[dict]:
    prev_high = prev_low = 0.0
    res_high = res_low = 0.0
    buy_low = sell_high = 0.0
    current_day: int | None = None
    events: list[dict] = []

    for i, candle in enumerate(candles):
        dt = datetime.fromtimestamp(candle.timestamp, tz=timezone.utc)
        if current_day != dt.toordinal():
            current_day = dt.toordinal()
            prev_high = prev_low = 0.0
            res_high = res_low = 0.0
            buy_low = sell_high = 0.0
        if not (session_start_hour <= dt.hour < session_end_hour):
            continue

        if prev_high == 0.0:
            prev_high = candle.high
        if prev_low == 0.0:
            prev_low = candle.low

        if candle.high > prev_high:
            res_high = candle.high
            prev_high = res_high
            buy_low = candle.low
        if res_high and candle.high < res_high and candle.high < buy_low:
            events.append({"direction": "BUY", "index": i, "timestamp": candle.timestamp, "level": candle.low})
            prev_high = res_high = buy_low = 0.0

        if candle.low < prev_low:
            res_low = candle.low
            prev_low = res_low
            sell_high = candle.high
        if res_low and candle.low > res_low and candle.low > sell_high:
            events.append({"direction": "SELL", "index": i, "timestamp": candle.timestamp, "level": candle.high})
            prev_low = res_low = sell_high = 0.0
    return events
