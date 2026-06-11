from __future__ import annotations

import math

from indicators.common import clamp, ema
from skill.signal_schema import Candle, FeatureSignal


def session_vwap(candles: list[Candle]) -> list[float | None]:
    out: list[float | None] = []
    current_day: int | None = None
    pv_total = 0.0
    vol_total = 0.0
    for candle in candles:
        day = candle.timestamp // 86400
        if day != current_day:
            current_day = day
            pv_total = 0.0
            vol_total = 0.0
        typical = (candle.open + candle.high + candle.low + candle.close) / 4.0
        volume = max(candle.volume, 0.0)
        pv_total += typical * volume
        vol_total += volume
        out.append(pv_total / vol_total if vol_total > 0 else typical)
    return out


def _slope_line(candles: list[Candle], period: int) -> list[float | None]:
    prices = [c.close for c in candles]
    half = max(1, round(period / 2))
    sqrt_period = max(1, round(math.sqrt(period)))
    fast = ema(prices, half)
    slow = ema(prices, period)
    diff = [
        None if f is None or s is None else 2.0 * f - s
        for f, s in zip(fast, slow, strict=False)
    ]
    clean = [prices[i] if value is None else value for i, value in enumerate(diff)]
    return ema(clean, sqrt_period)


def vwap_candle_breakout(
    candles: list[Candle],
    body_atr_fraction: float = 0.12,
    slope_period: int = 32,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < slope_period + 2:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for VWAP breakout"), {}
    i = len(candles) - 1 if index is None else index
    prev = candles[i - 1]
    cur = candles[i]
    vwaps = session_vwap(candles[: i + 1])
    slopes = _slope_line(candles[: i + 1], slope_period)
    vwap = vwaps[i]
    prev_vwap = vwaps[i - 1]
    slope = slopes[i]
    prev_slope = slopes[i - 1]
    avg_range = sum(c.high - c.low for c in candles[max(0, i - 20) : i + 1]) / min(i + 1, 21)
    body = abs(cur.close - cur.open)
    min_body = avg_range * body_atr_fraction
    bullish_cross = prev.close <= prev_vwap and cur.close > vwap
    bearish_cross = prev.close >= prev_vwap and cur.close < vwap
    slope_up = slope is not None and prev_slope is not None and slope > prev_slope
    slope_down = slope is not None and prev_slope is not None and slope < prev_slope
    body_ok = body >= min_body
    direction = "NEUTRAL"
    reason = "No closed-candle VWAP breakout with slope confirmation"
    strength = 0.0
    if bullish_cross and cur.close > cur.open and body_ok and slope_up:
        direction = "BUY"
        strength = clamp(0.58 + body / max(avg_range, 1e-12) * 0.28, 0.0, 1.0)
        reason = "Close crossed above session VWAP with bullish body and rising slope line"
    elif bearish_cross and cur.close < cur.open and body_ok and slope_down:
        direction = "SELL"
        strength = clamp(0.58 + body / max(avg_range, 1e-12) * 0.28, 0.0, 1.0)
        reason = "Close crossed below session VWAP with bearish body and falling slope line"
    values = {
        "vwap": vwap,
        "slope_line": slope,
        "body": body,
        "avg_range": avg_range,
        "body_threshold": min_body,
        "slope_direction": "UP" if slope_up else "DOWN" if slope_down else "FLAT",
    }
    return FeatureSignal(direction, strength, 0, vwap, reason), values

