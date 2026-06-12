from __future__ import annotations

from skill.signal_schema import Candle
from skill.strategy_skill import StrategySkill, strategy_spec


def _candles(direction: str = "up", count: int = 140) -> list[Candle]:
    candles = []
    price = 100.0
    for i in range(count):
        drift = 0.35 if direction == "up" else -0.35
        open_price = price
        close = max(1.0, open_price + drift + (0.08 if i % 5 == 0 else 0.0))
        high = max(open_price, close) + 0.25
        low = min(open_price, close) - 0.25
        candles.append(
            Candle(
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=1_700_000_000 + i * 3600,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000 + i,
            )
        )
        price = close
    return candles


def test_strategy_result_has_required_fields():
    result = StrategySkill().analyze("BTCUSDT", "1h", _candles(), "balanced").to_dict()
    assert result["decision"] in {"BUY", "SELL", "HOLD"}
    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.35 <= result["probability_of_success"] <= 0.82 or result["decision"] == "HOLD"
    assert result["probability_model"] == "heuristic"
    assert "score_breakdown" in result
    assert "backtestable_rules" in result
    assert "de_mark_support_v2" in result["indicator_values"]
    assert "apex_indi" in result["indicator_values"]
    assert "hl_signal" in result["indicator_values"]


def test_strategy_spec_is_track_2_non_live():
    spec = strategy_spec()
    assert spec["not_live_trading"] is True
    assert set(spec["decisions"]) == {"BUY", "SELL", "HOLD"}
