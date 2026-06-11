from __future__ import annotations

from indicators.common import clamp, ema
from skill.signal_schema import Candle, FeatureSignal


def macd_osma(
    candles: list[Candle],
    fast: int = 2,
    slow: int = 8,
    signal: int = 6,
    multiplier: float = 2.0,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < slow + signal + 3:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for MACD OsMA"), {}
    i = len(candles) - 1 if index is None else index
    closes = [c.close for c in candles[: i + 1]]
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = [
        0.0 if f is None or s is None else f - s
        for f, s in zip(fast_ema, slow_ema, strict=False)
    ]
    sig = ema(macd_line, signal)
    osma = [
        None if sig_value is None else (macd_line[j] - sig_value) * max(multiplier, 1.0)
        for j, sig_value in enumerate(sig)
    ]
    current = osma[i]
    previous = osma[i - 1]
    if current is None or previous is None:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "OsMA is warming up"), {}
    slope = current - previous
    candle = candles[i]
    avg_abs = sum(abs(v) for v in osma[max(0, i - 20) : i + 1] if v is not None) / max(1, min(i + 1, 21))
    strength = clamp(abs(current) / max(avg_abs * 2.0, 1e-12), 0.0, 1.0)
    if current < 0 and candle.close > candle.open and slope > 0:
        return FeatureSignal("BUY", max(0.52, strength), 0, current, "OsMA is negative but improving while the candle is bullish"), {
            "osma": current,
            "osma_slope": slope,
            "macd": macd_line[i],
        }
    if current > 0 and candle.close < candle.open and slope < 0:
        return FeatureSignal("SELL", max(0.52, strength), 0, current, "OsMA is positive but weakening while the candle is bearish"), {
            "osma": current,
            "osma_slope": slope,
            "macd": macd_line[i],
        }
    direction = "BUY" if slope > 0 else "SELL" if slope < 0 else "NEUTRAL"
    return FeatureSignal(direction, min(0.45, strength), 0, current, "OsMA slope only; candle/sign transition is not complete"), {
        "osma": current,
        "osma_slope": slope,
        "macd": macd_line[i],
    }

