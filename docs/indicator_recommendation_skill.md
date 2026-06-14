# Indicator Recommendation Skill

The Indicator Recommendation Skill checks a user-selected symbol against historical candle data and recommends which implemented indicators are best suited for that symbol and timeframe. It is separate from the main `BUY` / `SELL` / `HOLD` strategy skill.

The agent-facing `SKILL.md` for this workflow lives at:

```text
skills/indicator-recommendation-skill/SKILL.md
```

It describes the operating prompt, workflow, historical suitability scoring, recommendation buckets, API surface, validation commands, and advisory-only boundaries for agents that need to run or explain this skill.

The first implemented indicator-based Strategy Skill that this recommendation skill builds on is shown in this demo video:

- https://www.youtube.com/watch?v=TA6gRVvitJs

Indicator Recommendation Skill demo video:

- https://youtu.be/j8ii27bbz4A

This skill does not produce a trade order. It answers a different question:

```text
For this symbol and timeframe, which indicators have recently produced the most useful historical directional evidence, and how should the user configure or combine them?
```

## Purpose

The main strategy skill combines regime, structure, momentum, trigger, and risk context into one deterministic trading decision. The Indicator Recommendation Skill evaluates those indicator signals independently over historical rolling windows.

Use it when:

- A user wants to choose a symbol such as `BTCUSDT`, `ETHUSDT`, or a custom pair.
- A user wants to understand which indicators fit that symbol's recent behavior.
- A user wants recommended indicator roles and minimum signal-strength settings.
- A user wants to avoid indicators that do not have enough recent signal quality for the selected symbol/timeframe.

## Inputs

The skill accepts the same market setup payload shape used by the Flask app:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "4h",
  "lookback": 140,
  "provider": "coingecko",
  "market_data": []
}
```

Fields:

- `symbol`: trading pair to analyze.
- `timeframe`: supported candle timeframe. The UI currently exposes `4h` and `1d`.
- `lookback`: historical candle count. The skill requires at least 90 candles.
- `provider`: market data provider used when `market_data` is empty.
- `market_data`: optional inline normalized OHLCV candles.
- `forward_bars`: optional forward evaluation horizon. Default is 3 bars.

## Method

The skill uses closed historical candles only.

Evaluation flow:

```text
payload
  -> skill.signal_schema.AnalyzeRequest
  -> market_data or provider candles
  -> IndicatorRecommendationSkill.analyze
  -> rolling windows from candle 60 onward
  -> StrategySkill._calculate_features per window
  -> independent indicator signal scoring
  -> suitability report
```

For each rolling window, the skill:

1. Calculates the same indicator features used by the strategy skill.
2. Records BUY and SELL signals above a minimum signal-strength floor.
3. Compares each directional signal with the close-to-close return after `forward_bars`.
4. Scores each indicator using win rate, profit factor, average signal strength, sample size, and coverage.
5. Assigns a recommendation bucket.

## Recommendation Buckets

`use`

The indicator has enough historical sample support and a strong enough suitability score to be used as a primary input for this symbol/timeframe.

`use_with_confirmation`

The indicator is usable, but should be combined with stronger regime, structure, momentum, or trigger confirmation.

`avoid_for_now`

The indicator has weak recent fit or too few historical directional signals. It should not be treated as a primary input until the sample improves.

## Indicators Evaluated

The skill evaluates these existing strategy feature keys:

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

Each result includes:

```text
name
category
role
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

## Settings Output

Each indicator recommendation includes practical settings:

```json
{
  "recommended_action": "use",
  "minimum_signal_strength": 0.58,
  "confirmation_required": false,
  "role": "Entry trigger",
  "setting_basis": "Use as an entry trigger when trend and structure agree."
}
```

The `minimum_signal_strength` value is not a new indicator parameter in the original MT4 sense. It is the recommended filter threshold for accepting that indicator's normalized `FeatureSignal.strength` inside this Python strategy system.

## Flask API

Spec endpoint:

```text
GET /indicator-recommendations/spec
```

Run endpoint:

```text
POST /indicator-recommendations
```

Example:

```bash
curl -X POST http://localhost:5000/indicator-recommendations \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","timeframe":"4h","lookback":140,"provider":"coingecko","market_data":[]}'
```

## Flask UI

The Flask dashboard exposes the skill on a separate tab:

```text
Indicator Fit
```

Workflow:

1. Select a symbol or enter a custom symbol.
2. Choose timeframe, candle count, provider, and live/demo mode.
3. Press `Recommend Indicators`.
4. Review the market profile, best-fit indicators, and full indicator review.

The tab uses the same market setup controls as the main strategy dashboard but calls the separate recommendation endpoint.

## Safety Boundaries

This skill is advisory and non-executing.

It does not:

```text
place orders
sign transactions
manage positions
guarantee future performance
replace backtesting or risk management
```

The output describes historical indicator fit for a symbol/timeframe. It is not a direct instruction to buy or sell.
