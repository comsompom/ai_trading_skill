---
name: indicator-recommendation-skill
description: Use this skill when an agent needs to recommend which implemented crypto strategy indicators fit a selected symbol and timeframe, evaluate historical indicator suitability, explain use/use_with_confirmation/avoid_for_now buckets, or expose the indicator recommendation Flask API logic.
---

# Indicator Recommendation Skill

## Role

You are the agent-facing operator for this repository's historical indicator-fit workflow. Use the project implementation as the source of truth:

- Core implementation: `skill/indicator_recommendation_skill.py`
- Shared feature calculations: `skill/strategy_skill.py`
- Request schema: `skill/signal_schema.py`
- API route: `POST /indicator-recommendations`
- Human documentation: `docs/indicator_recommendation_skill.md`

This skill does not produce a trading decision. It recommends indicator fit for a symbol/timeframe based on closed historical candles.

## Operating Prompt

Evaluate a selected crypto symbol and timeframe against historical candles. Recommend which implemented indicators should be used as primary inputs, which should be used only with confirmation, and which should be avoided for now. Explain the recommendation using historical signal count, win rate, profit factor, average signal strength, sample size, and coverage. Do not return `BUY`, `SELL`, or `HOLD` as a trade decision.

## Inputs

Accept a payload compatible with `AnalyzeRequest`, plus optional `forward_bars`:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "4h",
  "lookback": 140,
  "provider": "cmc",
  "market_data": [],
  "forward_bars": 3
}
```

Rules:

- Require at least 90 candles.
- Clamp `forward_bars` between 1 and 12.
- Use `forward_bars=3` by default.
- Use supplied normalized `market_data` when present.
- Fetch candles through the configured provider when `market_data` is empty.

## Workflow

1. Parse the payload with `AnalyzeRequest.from_payload()`.
2. Resolve candles from inline `market_data` or the selected provider.
3. Run `IndicatorRecommendationSkill.analyze(...)`.
4. Iterate rolling windows from candle index 60 through the last index that has enough forward bars.
5. For each window, call `StrategySkill._calculate_features(window)`.
6. Record BUY/SELL indicator signals with strength at least `0.15`.
7. Compare each directional signal with the close-to-close return after `forward_bars`.
8. Build sorted indicator evaluations and group them into recommendation buckets.
9. Return the indicator-fit report.

## Indicators Evaluated

The skill evaluates these feature keys from the strategy:

```text
regime                  Fisher regime
structure               Rolling structure
structure_abcd          ABCD projection
structure_demark        DeMark support/resistance
structure_hl_session    Session high/low
momentum_rsi_mfi        RSI/MFI/MA3 momentum
momentum_osma           MACD OSMA
trigger_vwap            VWAP candle breakout
trigger_apex            APEX pattern
trigger_power_candle    Power candle
```

Each indicator has a category, default role, and setting basis defined in `INDICATOR_DESCRIPTIONS`.

## Evaluation Metrics

For each indicator, collect:

```text
signal_count
buy_signals
sell_signals
win_rate
average_forward_return
profit_factor
average_strength
coverage
suitability_score
recommendation
settings
reason
```

Win logic:

```text
BUY signal win  -> forward_return > movement_threshold
SELL signal win -> -forward_return > movement_threshold
```

Movement threshold:

```text
threshold = clamp((ATR / entry_price) * 0.18, 0.001, 0.025)
```

Suitability score:

```text
0.38 * win_rate
+ 0.26 * profit_factor_score
+ 0.18 * average_strength
+ 0.10 * sample_score
+ 0.08 * coverage_score
```

Where:

```text
profit_factor_score = profit_factor / (profit_factor + 1.0)
sample_score = clamp(signal_count / 18.0, 0.0, 1.0)
coverage_score = clamp(coverage / 0.55, 0.0, 1.0)
```

## Recommendation Buckets

```text
avoid_for_now:
  signal_count < 5, or suitability_score < 0.45

use_with_confirmation:
  signal_count >= 5 and suitability_score >= 0.45

use:
  signal_count >= 5 and suitability_score >= 0.58
```

Recommended strength floor:

```text
signal_count < 5                  -> 0.70
use                               -> max(0.58, average_strength * 0.9)
use_with_confirmation             -> max(0.66, average_strength * 0.9)
avoid_for_now with enough signals -> max(0.72, average_strength * 0.9)
clamp final value between 0.15 and 0.90
```

## Output

Return a report with:

```text
symbol
timeframe
provider
skill
summary
market_profile
recommended_indicators
confirmation_indicators
avoid_indicators
all_indicators
latest_signals
latest_indicator_values
analysis_settings
input_data_range
assumptions
```

The `summary` should name the current market profile, primary indicators, confirmation indicators, and count of avoided indicators.

## Interface

Flask:

```text
GET  /indicator-recommendations/spec
POST /indicator-recommendations
```

Local Python:

```python
from skill.indicator_recommendation_skill import IndicatorRecommendationSkill

result = IndicatorRecommendationSkill().analyze_payload({
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "lookback": 140,
    "provider": "cmc",
    "market_data": [],
    "forward_bars": 3,
})
```

## Safety Boundaries

Always state that the result is advisory indicator-fit analysis, not a trade order. Do not transform `recommended_indicators` into execution instructions. Do not claim future performance; the method uses historical close-to-close evaluation and excludes fees and slippage.

## Validation

After changing recommendation logic or this skill description, run:

```bash
python3 -m pytest tests/test_indicator_recommendation_skill.py tests/test_flask_routes.py
```

Run broader tests when changing shared schemas, providers, strategy feature calculations, or UI/API behavior.
