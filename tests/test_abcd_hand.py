from __future__ import annotations

from indicators.custom_mql_ported.abcd_hand import (
    abcd_hand_projection,
    project_d_target,
    snap_price_to_extreme,
)
from skill.signal_schema import Candle


def _candle(index: int, high: float, low: float, close: float | None = None) -> Candle:
    return Candle(
        symbol="BTCUSDT",
        timeframe="1h",
        timestamp=1_700_000_000 + index * 3600,
        open=(high + low) / 2.0,
        high=high,
        low=low,
        close=close if close is not None else (high + low) / 2.0,
        volume=1000.0,
    )


def test_project_d_target_matches_mql_formula():
    assert project_d_target(a_price=100.0, b_price=112.0, c_price=105.0, p_level=0.5) == 111.0
    assert project_d_target(a_price=112.0, b_price=100.0, c_price=105.0, p_level=0.25) == 108.0


def test_snap_price_to_extreme_uses_three_bar_window():
    candles = [
        _candle(0, high=101.0, low=99.0),
        _candle(1, high=104.0, low=98.0),
        _candle(2, high=103.0, low=97.0),
    ]
    low_index, low_price, low_kind = snap_price_to_extreme(candles, index=1, price=97.04, point_size=0.01)
    assert (low_index, low_price, low_kind) == (2, 97.0, "LOW")

    high_index, high_price, high_kind = snap_price_to_extreme(candles, index=1, price=103.96, point_size=0.01)
    assert (high_index, high_price, high_kind) == (1, 104.0, "HIGH")


def test_abcd_projection_exposes_target_and_fibo_levels():
    candles = [
        _candle(0, 101.0, 99.0),
        _candle(1, 102.0, 98.0),
        _candle(2, 104.0, 99.0),
        _candle(3, 103.0, 100.0),
        _candle(4, 108.0, 102.0),
        _candle(5, 106.0, 101.0),
        _candle(6, 105.0, 95.0),
        _candle(7, 103.0, 97.0),
        _candle(8, 106.0, 100.0),
        _candle(9, 105.0, 99.0),
        _candle(10, 104.0, 96.0),
        _candle(11, 107.0, 101.0),
        _candle(12, 109.0, 103.0, close=106.0),
        _candle(13, 108.0, 104.0, close=106.5),
        _candle(14, 110.0, 105.0, close=107.0),
        _candle(15, 109.0, 104.0, close=107.2),
        _candle(16, 111.0, 106.0, close=107.5),
        _candle(17, 110.0, 105.0, close=107.7),
        _candle(18, 112.0, 106.0, close=108.0),
        _candle(19, 111.0, 107.0, close=108.2),
    ]

    signal, values = abcd_hand_projection(candles, wing=1)

    assert signal.direction in {"BUY", "SELL", "NEUTRAL"}
    assert values["source_indicator"] == "ABCD_hand_v4.mq4"
    assert "d_target" in values
    assert values["fibonacci_levels"]["0"] == values["points"][2]["price"]
    assert values["logic"].startswith("D = C + PLevel")
