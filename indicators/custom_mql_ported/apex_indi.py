from __future__ import annotations

from indicators.common import clamp
from skill.signal_schema import Candle, FeatureSignal


def apex_indi(
    candles: list[Candle],
    ap_diff: int = 20,
    pe_diff: int = 3,
    ex_diff: int = 7,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < (ap_diff + pe_diff + ex_diff) + 8:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for APEX pattern"), {}
    i = len(candles) - 1 if index is None else index
    scoped = candles[: i + 1]
    events = _scan_apex(scoped, ap_diff=ap_diff, pe_diff=pe_diff, ex_diff=ex_diff)
    if not events:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "No complete APEX X event"), {
            "source_indicator": "APEX_Indi.mq4",
            "events": [],
        }

    latest = events[-1]
    freshness = len(scoped) - 1 - latest["x_index"]
    strength = clamp(0.78 - 0.08 * freshness, 0.0, 0.78)
    if freshness > 3:
        return FeatureSignal("NEUTRAL", 0.0, freshness, latest["x_price"], "Last APEX X event is stale"), {
            "source_indicator": "APEX_Indi.mq4",
            "latest_event": latest,
            "events": events[-5:],
        }
    return FeatureSignal(
        latest["direction"],
        strength,
        freshness,
        latest["x_price"],
        f"APEX {latest['direction']} X event completed after A-P-E sequence",
    ), {
        "source_indicator": "APEX_Indi.mq4",
        "latest_event": latest,
        "events": events[-5:],
        "logic": "A-P-E setup followed by X breakout: BUY X breaks above A high with bullish candle; SELL X breaks below A low with bearish candle.",
    }


def _scan_apex(candles: list[Candle], ap_diff: int, pe_diff: int, ex_diff: int) -> list[dict]:
    events: list[dict] = []
    buy_state: dict | None = None
    sell_state: dict | None = None
    max_bars = min(len(candles) - 3, (ap_diff + pe_diff + ex_diff) * 4)

    for shift in range(max_bars, 0, -1):
        idx = len(candles) - 1 - shift
        cur = candles[idx]
        older1 = candles[idx - 1] if idx - 1 >= 0 else None
        older2 = candles[idx - 2] if idx - 2 >= 0 else None

        if older1 is None:
            continue

        if buy_state is None and cur.open > cur.close and cur.high > older1.high and older1.close > older1.open:
            buy_state = {"a_index": idx, "a_high": cur.high, "stage": "A"}

        if buy_state and buy_state["stage"] == "A":
            age = idx - buy_state["a_index"]
            if age > ap_diff or (idx > buy_state["a_index"] and cur.high >= buy_state["a_high"]):
                buy_state = None
            elif age > 2 and cur.close > cur.open and older1.close > older1.open:
                buy_state.update({"p_index": idx - 1, "stage": "P"})

        if buy_state and buy_state["stage"] == "P":
            p_age = idx - buy_state["p_index"]
            if p_age < 2 and cur.high > older1.high and cur.close > cur.open and older1.close > older1.open:
                buy_state.update({"e_index": idx, "e_low": cur.low, "stage": "E"})

        if buy_state and buy_state["stage"] == "E":
            if cur.low < buy_state["e_low"]:
                buy_state = None
            elif idx > buy_state["e_index"] and cur.high > buy_state["a_high"] and cur.close > cur.open:
                events.append(
                    {
                        "direction": "BUY",
                        "a_index": buy_state["a_index"],
                        "p_index": buy_state["p_index"],
                        "e_index": buy_state["e_index"],
                        "x_index": idx,
                        "x_timestamp": cur.timestamp,
                        "x_price": cur.high,
                    }
                )
                buy_state = None

        if sell_state is None and cur.open < cur.close and cur.low < older1.close and older1.close < older1.open:
            sell_state = {"a_index": idx, "a_low": cur.low, "stage": "A"}

        if sell_state and sell_state["stage"] == "A":
            age = idx - sell_state["a_index"]
            if age > ap_diff or (idx > sell_state["a_index"] and cur.low <= sell_state["a_low"]):
                sell_state = None
            elif older2 and age > 2 and older1.close < older1.open and older2.close > older2.open:
                sell_state.update({"p_index": idx - 1, "p_high": older1.high, "stage": "P"})

        if sell_state and sell_state["stage"] == "P":
            if cur.high > sell_state["p_high"]:
                sell_state = None
            elif idx > sell_state["p_index"] and idx - sell_state["p_index"] < 2 and cur.low < older1.low and cur.close < cur.open and older1.close < older1.open:
                sell_state.update({"e_index": idx, "e_high": cur.high, "stage": "E"})

        if sell_state and sell_state["stage"] == "E":
            if cur.high > sell_state["e_high"]:
                sell_state = None
            elif idx > sell_state["e_index"] and cur.low < sell_state["a_low"] and cur.close < cur.open:
                events.append(
                    {
                        "direction": "SELL",
                        "a_index": sell_state["a_index"],
                        "p_index": sell_state["p_index"],
                        "e_index": sell_state["e_index"],
                        "x_index": idx,
                        "x_timestamp": cur.timestamp,
                        "x_price": cur.low,
                    }
                )
                sell_state = None
    return events
