from __future__ import annotations

from indicators.common import clamp, ema
from skill.signal_schema import Candle, FeatureSignal


def rsi(values: list[float], period: int = 19) -> list[float | None]:
    out: list[float | None] = [None]
    gains: list[float] = []
    losses: list[float] = []
    avg_gain: float | None = None
    avg_loss: float | None = None
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        gains.append(gain)
        losses.append(loss)
        if i < period:
            out.append(None)
            continue
        if avg_gain is None or avg_loss is None:
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            out.append(100.0 - 100.0 / (1.0 + rs))
    return out


def mfi(candles: list[Candle], period: int = 19) -> list[float | None]:
    typical = [(c.high + c.low + c.close) / 3.0 for c in candles]
    flows = [typical[i] * max(candles[i].volume, 0.0) for i in range(len(candles))]
    out: list[float | None] = []
    for i in range(len(candles)):
        if i < period:
            out.append(None)
            continue
        positive = 0.0
        negative = 0.0
        for j in range(i - period + 1, i + 1):
            if typical[j] >= typical[j - 1]:
                positive += flows[j]
            else:
                negative += flows[j]
        out.append(100.0 if negative == 0 else 100.0 - 100.0 / (1.0 + positive / negative))
    return out


def rsi_mfi_ma3(
    candles: list[Candle],
    rsi_period: int = 19,
    mfi_period: int = 19,
    ma_period: int = 50,
    index: int | None = None,
) -> tuple[FeatureSignal, dict]:
    if len(candles) < rsi_period + mfi_period + ma_period:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "Not enough candles for RSI/MFI filter"), {}
    i = len(candles) - 1 if index is None else index
    closes = [c.close for c in candles[: i + 1]]
    rsi_values = rsi(closes, rsi_period)
    mfi_values = mfi(candles[: i + 1], mfi_period)
    rsi_clean = [50.0 if v is None else v for v in rsi_values]
    mfi_clean = [50.0 if v is None else v for v in mfi_values]
    rsi_ma = ema(rsi_clean, ma_period)
    mfi_ma = ema(mfi_clean, ma_period)
    combined_ma = [
        None if r is None or m is None else (r + m) / 2.0
        for r, m in zip(rsi_ma, mfi_ma, strict=False)
    ]
    current_rsi = rsi_values[i]
    current_mfi = mfi_values[i]
    ma = combined_ma[i - 1] if i > 0 else combined_ma[i]
    if current_rsi is None or current_mfi is None or ma is None:
        return FeatureSignal("NEUTRAL", 0.0, 999, None, "RSI/MFI MA is warming up"), {}
    rising = candles[i].close > candles[i - 1].close
    falling = candles[i].close < candles[i - 1].close
    bullish_votes = int(current_rsi > ma) + int(current_mfi > ma)
    bearish_votes = int(current_rsi < ma) + int(current_mfi < ma)
    if bullish_votes and rising:
        return FeatureSignal("BUY", clamp(0.42 + 0.22 * bullish_votes, 0.0, 1.0), 0, ma, "RSI/MFI participation is above its combined MA with rising close"), {
            "rsi": current_rsi,
            "mfi": current_mfi,
            "combined_ma": ma,
            "bullish_votes": bullish_votes,
        }
    if bearish_votes and falling:
        return FeatureSignal("SELL", clamp(0.42 + 0.22 * bearish_votes, 0.0, 1.0), 0, ma, "RSI/MFI participation is below its combined MA with falling close"), {
            "rsi": current_rsi,
            "mfi": current_mfi,
            "combined_ma": ma,
            "bearish_votes": bearish_votes,
        }
    return FeatureSignal("NEUTRAL", 0.2, 0, ma, "RSI/MFI participation does not agree with price direction"), {
        "rsi": current_rsi,
        "mfi": current_mfi,
        "combined_ma": ma,
    }

