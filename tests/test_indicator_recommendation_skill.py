from __future__ import annotations

from skill.indicator_recommendation_skill import (
    IndicatorRecommendationSkill,
    indicator_recommendation_spec,
)
from skill.signal_schema import Candle


def _candles(count: int = 160) -> list[Candle]:
    candles = []
    price = 100.0
    for i in range(count):
        trend = 0.12 if i < count * 0.55 else -0.04
        wave = 0.65 if i % 9 < 5 else -0.45
        open_price = price
        close = max(2.0, open_price + trend + wave * 0.18)
        high = max(open_price, close) + 0.45 + (0.12 if i % 13 == 0 else 0.0)
        low = min(open_price, close) - 0.42
        candles.append(
            Candle(
                symbol="BTCUSDT",
                timeframe="4h",
                timestamp=1_700_000_000 + i * 14_400,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000 + i * 5,
            )
        )
        price = close
    return candles


def test_indicator_recommendation_skill_returns_fit_report():
    result = IndicatorRecommendationSkill().analyze(
        symbol="BTCUSDT",
        timeframe="4h",
        candles=_candles(),
        provider="inline",
    )

    assert result["symbol"] == "BTCUSDT"
    assert result["timeframe"] == "4h"
    assert result["skill"]["name"] == "Historical Indicator Recommendation Skill"
    assert result["analysis_settings"]["candles"] == 160
    assert result["analysis_settings"]["evaluated_windows"] > 0
    assert result["market_profile"]["direction"] in {"uptrend", "downtrend", "range"}
    assert len(result["all_indicators"]) == 10
    assert {
        item["recommendation"] for item in result["all_indicators"]
    } <= {"use", "use_with_confirmation", "avoid_for_now"}
    assert "summary" in result


def test_indicator_recommendation_spec_is_non_live():
    spec = indicator_recommendation_spec()
    assert spec["not_live_trading"] is True
    assert "recommended_indicators" in spec["outputs"]
