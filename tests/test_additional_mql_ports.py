from __future__ import annotations

from indicators.custom_mql_ported import apex_indi, demark_support, hl_signal
from skill.signal_schema import Candle
from skill.strategy_skill import StrategySkill, strategy_spec


def _candles(count: int = 90) -> list[Candle]:
    candles = []
    price = 100.0
    for i in range(count):
        drift = 0.18 if i % 11 < 6 else -0.12
        open_price = price
        close = open_price + drift
        high = max(open_price, close) + 0.5 + (0.9 if i == 35 else 0.0)
        low = min(open_price, close) - 0.5 - (0.9 if i == 55 else 0.0)
        candles.append(
            Candle(
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=1_700_000_000 + i * 3600,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000.0 + i,
            )
        )
        price = close
    return candles


def test_new_mql_ports_return_feature_signals():
    candles = _candles()
    for indicator in (demark_support, apex_indi, hl_signal):
        signal, values = indicator(candles)
        assert signal.direction in {"BUY", "SELL", "NEUTRAL"}
        assert isinstance(values, dict)
        assert "source_indicator" in values or values == {}


def test_strategy_output_includes_new_indicator_values_and_features():
    result = StrategySkill().analyze("BTCUSDT", "1h", _candles(140), "balanced").to_dict()
    indicators = result["indicator_values"]
    assert "de_mark_support_v2" in indicators
    assert "apex_indi" in indicators
    assert "hl_signal" in indicators
    assert "structure_demark" in indicators["features"]
    assert "trigger_apex" in indicators["features"]
    assert "structure_hl_session" in indicators["features"]


def test_strategy_spec_lists_new_indicators():
    implemented = "\n".join(strategy_spec()["indicators_implemented"])
    assert "De_Mark_Support_V2" in implemented
    assert "APEX_Indi" in implemented
    assert "HL_Signal" in implemented
