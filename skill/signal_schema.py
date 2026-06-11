from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Decision = Literal["BUY", "SELL", "HOLD"]
Direction = Literal["BUY", "SELL", "NEUTRAL"]


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_payload(cls, payload: dict[str, Any], symbol: str, timeframe: str) -> "Candle":
        return cls(
            symbol=str(payload.get("symbol") or symbol).upper(),
            timeframe=str(payload.get("timeframe") or timeframe),
            timestamp=int(payload["timestamp"]),
            open=float(payload["open"]),
            high=float(payload["high"]),
            low=float(payload["low"]),
            close=float(payload["close"]),
            volume=float(payload.get("volume", 0.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass(frozen=True)
class FeatureSignal:
    direction: Direction
    strength: float
    freshness_bars: int
    level: float | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "strength": round(self.strength, 4),
            "freshness_bars": self.freshness_bars,
            "level": None if self.level is None else round(self.level, 8),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class StrategyResult:
    symbol: str
    timeframe: str
    decision: Decision
    confidence: float
    probability_of_success: float
    probability_model: Literal["heuristic", "calibrated"]
    probability_sample_size: int
    score_breakdown: dict[str, float]
    indicator_values: dict[str, Any]
    explanation: str
    risk_assumptions: dict[str, Any]
    backtestable_rules: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "decision": self.decision,
            "confidence": round(self.confidence, 4),
            "probability_of_success": round(self.probability_of_success, 4),
            "probability_model": self.probability_model,
            "probability_sample_size": self.probability_sample_size,
            "score_breakdown": {k: round(v, 4) for k, v in self.score_breakdown.items()},
            "indicator_values": self.indicator_values,
            "explanation": self.explanation,
            "risk_assumptions": self.risk_assumptions,
            "backtestable_rules": self.backtestable_rules,
        }


@dataclass(frozen=True)
class AnalyzeRequest:
    symbol: str
    timeframe: str
    lookback: int = 300
    risk_profile: str = "balanced"
    provider: str = "binance"
    market_data: list[Candle] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AnalyzeRequest":
        symbol = str(payload.get("symbol", "BTCUSDT")).upper()
        timeframe = str(payload.get("timeframe", "1h"))
        lookback = int(payload.get("lookback", 300))
        if lookback < 60:
            raise ValueError("lookback must be at least 60 candles")
        market_data = [
            Candle.from_payload(item, symbol=symbol, timeframe=timeframe)
            for item in payload.get("market_data", [])
        ]
        return cls(
            symbol=symbol,
            timeframe=timeframe,
            lookback=min(lookback, 1000),
            risk_profile=str(payload.get("risk_profile", "balanced")),
            provider=str(payload.get("provider", "binance")).lower(),
            market_data=market_data,
        )

