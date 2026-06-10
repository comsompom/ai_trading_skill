# Logic for Skill

## Indicator Understanding and Best Use

The proposed indicators should not all be used as equal entry signals. The strongest combined logic is to separate them into roles: market regime, structure, momentum confirmation, entry trigger, risk/target context, and validation.

| Indicator | What It Detects | Best Thing to Use in Combined Logic |
| --- | --- | --- |
| `ABCD_hand_v4.mq4` | Manual ABCD swing projection. It stores A, B, C, and projected D, with D calculated from `C + PLevel * abs(B - A)` and Fibonacci levels. | Use as optional harmonic target/context after swing points are available. Do not make it a primary automated signal because it depends on manual point placement. |
| `APEX_Indi.mq4` | A staged A-P-E-X candle sequence that confirms a bullish or bearish breakout after a setup, pullback, and expansion leg. | Use the final `X` event as a strong pattern trigger, because it requires multiple candle conditions before confirming continuation. |
| `Binary_Options.mq4` | H1 session breakout/reversal logic between 09:00 and 18:00 with stop-loss buffers. | Use its high/low invalidation idea as a risk reference. Its fixed session window is weaker for 24/7 crypto, so it should be secondary or disabled unless a user selects session-based trading. |
| `Candlestick - Hammer and Shooting Star Signal.mq4` | Hammer and shooting-star reversal candles at local lows/highs, using wick-to-body ratios and minimum candle size. | Use hammer as bullish reversal trigger and shooting star as bearish reversal trigger, only near support/resistance, VWAP, Fibonacci, or fractal levels. |
| `De_Mark_Support_V2.mq4` | DeMark-style support/resistance trendline breakout with TD1/TD2/TD3 breakout checks and target projection. | Use support/resistance breakout as a high-value structure confirmation and use its projected target as take-profit context. |
| `FIBO_Simple_v3.mq4` | Draws Fibonacci levels from higher-timeframe anchor bars, with standard or custom extension levels. | Use levels as confluence zones: entry quality improves near retracement/extension levels, and exits can target the next level. |
| `Fisher_Yur4ik3-a_v6_MTF.mq4` | Fisher transform with upper/lower thresholds and higher-timeframe confirmation. Buy occurs when Fisher crosses up through the upper level; sell occurs when it crosses down through the lower level. | Use as the main regime and momentum filter. It should gate trades so BUY needs bullish Fisher alignment and SELL needs bearish Fisher alignment. |
| `FX5_MACD_Divergence_V1_1_2.mq4` | Classical and reverse MACD divergence from MACD peaks/troughs versus price highs/lows. | Use classical divergence as early reversal evidence and reverse divergence as continuation evidence. It should add confidence, not trigger trades alone. |
| `HL_Signal.mq4` | Intraday high/low session signal based on highs/lows formed between 09:00 and 18:00. | Use only as optional session structure. For crypto default logic, replace fixed hours with rolling high/low windows. |
| `IndCandleBreakout_v3.mq4` | Candle breakout lines based on smoothed/open-derived high and low buffers, with trend and reversal arrows. | Use as a breakout trigger: BUY trend/reversal when price breaks above the dynamic high line; SELL when it breaks below the dynamic low line. |
| `MACD_OSMA_Bar_alert.mq4` | OsMA histogram strength and direction. It marks BUY when OsMA is negative while candle is bullish, and SELL when OsMA is positive while candle is bearish; histogram slope shows acceleration/deceleration. | Use as momentum exhaustion/transition confirmation. Best feature is OsMA sign plus histogram slope, not the arrow alone. |
| `MTF_Fractal_v2.mq4` | Higher-timeframe fractal highs and lows, optionally extended as levels. | Use fractal highs/lows as support/resistance, stop placement, and breakout validation. |
| `Power_Candle_Alerts_v2.mq4` | Detects candles whose range is at least `Set_Alert_At_Val` times the average range of the last `Candles_Range` candles. | Use as volatility/impulse confirmation. A power candle in signal direction increases confidence; a power candle against signal direction blocks entry. |
| `Range_n_Line_v8_1.mq4` | Range, channel, and line logic with breakout detection above/below recent range levels. | Use as a range-state detector: avoid mean-reversion entries inside compressed ranges and prefer trades after a confirmed range break. |
| `RSI_MFI_MA3.mq4` | RSI and custom MFI compared with their combined moving average; price close direction must agree. | Use as a participation filter. BUY requires RSI and/or MFI above the RSI/MFI MA with rising close; SELL requires RSI and/or MFI below it with falling close. |
| `Seq_Boool_Bear_v7.1.mq4` | Counts consecutive bullish or bearish candles, then signals exhaustion based on best sequence length and selected risk style. | Use as an exhaustion warning. Long bearish sequence can support reversal BUY; long bullish sequence can support reversal SELL. It should reduce confidence for late continuation entries. |
| `VWAP_CANDLE_BREAKOUT_slope_dir_line.mq4` | VWAP breakout with candle body threshold and slope-direction-line filter. BUY requires candle crossing above VWAP with bullish body and rising slope; SELL requires crossing below VWAP with bearish body and falling slope. | Use as the primary execution trigger because it combines price location, candle body, and trend slope. |

## Combined Signal Model

The Skill should calculate normalized features from all indicators and group them into five blocks:

1. `regime`: Fisher MTF, slope direction, range state.
2. `structure`: VWAP, DeMark lines, fractals, Fibonacci, rolling highs/lows.
3. `momentum`: MACD divergence, OsMA, RSI/MFI.
4. `trigger`: VWAP candle breakout, IndCandleBreakout, APEX X, hammer/shooting star, power candle.
5. `risk_context`: stop distance, target distance, nearest opposite level, volatility expansion.

Each feature returns:

```json
{
  "direction": "BUY | SELL | NEUTRAL",
  "strength": 0.0,
  "freshness_bars": 0,
  "level": 0.0,
  "reason": ""
}
```

Signals are evaluated only on closed candles by default. Current-candle mode can be exposed later, but backtests should use closed candles.

## BUY Logic

Return `BUY` when all hard filters pass and the bullish score is high enough.

Hard filters:

- Higher-timeframe Fisher regime is bullish or recently crossed bullish.
- Price is not directly under a strong resistance/fractal/Fibonacci/DeMark level unless the current candle closes through it.
- Stop distance to invalidation is not larger than configured maximum risk.
- Reward-to-risk to the nearest target is at least `1.5R`.
- No active bearish power candle or bearish VWAP/slope breakdown in the last `N` bars.

Core BUY confirmations:

- VWAP candle breakout BUY: close is above VWAP, candle body exceeds the body threshold, and slope direction is rising.
- Fisher crosses above `Upper_Level` or remains bullish on current timeframe with higher-timeframe support.
- RSI and/or MFI is above the combined RSI/MFI MA and close is rising.
- OsMA is improving from negative or histogram slope is rising.
- Structure supports the entry: break above IndCandleBreakout high line, DeMark resistance breakout, range breakout, or close above recent fractal high.
- Trigger quality improves if APEX prints final bullish `X`, hammer appears near support, or a bullish power candle confirms impulse.

BUY score:

```text
buy_score =
  0.25 * regime_bullish_score +
  0.25 * structure_bullish_score +
  0.20 * momentum_bullish_score +
  0.20 * trigger_bullish_score +
  0.10 * risk_reward_score
```

Decision:

- `BUY` when `buy_score >= 0.68` and `buy_score - sell_score >= 0.18`.
- `HOLD` when score is below threshold or bullish/bearish evidence conflicts.

Suggested BUY stop and target:

- Stop: below nearest valid structure level, using the lowest of recent swing/fractal/VWAP invalidation, with ATR or average-range padding.
- Target 1: next Fibonacci/DeMark/fractal resistance or `1.5R`.
- Target 2: next extension level or `2.5R`.

## SELL Logic

Return `SELL` when all hard filters pass and the bearish score is high enough.

Hard filters:

- Higher-timeframe Fisher regime is bearish or recently crossed bearish.
- Price is not directly above strong support/fractal/Fibonacci/DeMark level unless the current candle closes through it.
- Stop distance to invalidation is not larger than configured maximum risk.
- Reward-to-risk to the nearest target is at least `1.5R`.
- No active bullish power candle or bullish VWAP/slope breakout in the last `N` bars.

Core SELL confirmations:

- VWAP candle breakout SELL: close is below VWAP, candle body exceeds the body threshold, and slope direction is falling.
- Fisher crosses below `Lower_Level` or remains bearish on current timeframe with higher-timeframe support.
- RSI and/or MFI is below the combined RSI/MFI MA and close is falling.
- OsMA is weakening from positive or histogram slope is falling.
- Structure supports the entry: break below IndCandleBreakout low line, DeMark support breakdown, range breakdown, or close below recent fractal low.
- Trigger quality improves if APEX prints final bearish `X`, shooting star appears near resistance, or a bearish power candle confirms impulse.

SELL score:

```text
sell_score =
  0.25 * regime_bearish_score +
  0.25 * structure_bearish_score +
  0.20 * momentum_bearish_score +
  0.20 * trigger_bearish_score +
  0.10 * risk_reward_score
```

Decision:

- `SELL` when `sell_score >= 0.68` and `sell_score - buy_score >= 0.18`.
- `HOLD` when score is below threshold or bullish/bearish evidence conflicts.

Suggested SELL stop and target:

- Stop: above nearest valid structure level, using the highest of recent swing/fractal/VWAP invalidation, with ATR or average-range padding.
- Target 1: next Fibonacci/DeMark/fractal support or `1.5R`.
- Target 2: next extension level or `2.5R`.

## Probability of Success

The Skill should expose `probability_of_success`, but it must be treated as an estimated probability, not a guarantee.

Before enough backtest data exists, use a conservative score-to-probability transform:

```text
edge_score = selected_direction_score - opposite_direction_score
raw_probability = 0.50 + 0.35 * edge_score
probability_of_success = clamp(raw_probability, 0.35, 0.82)
```

Then apply penalties:

```text
probability_of_success -= 0.05 if reward_to_risk < 1.8
probability_of_success -= 0.05 if signal is against higher-timeframe trend
probability_of_success -= 0.04 if nearest opposing level is closer than 0.75R
probability_of_success -= 0.03 if volatility is extreme versus recent average
probability_of_success -= 0.03 if signal is older than 2 closed candles
```

After backtesting is available, replace the raw transform with calibrated historical buckets:

```text
probability_of_success =
  historical_win_rate[
    direction,
    timeframe,
    market_regime_bucket,
    score_bucket,
    volatility_bucket,
    reward_risk_bucket
  ]
```

Minimum calibration rules:

- Require at least 30 historical trades in a bucket before using its exact win rate.
- If a bucket has fewer than 30 trades, blend it with the parent timeframe/regime bucket.
- Cap displayed probability at `85%` until live-forward validation exists.
- Always return sample size, backtest period, and whether probability is `heuristic` or `calibrated`.

Example response fields:

```json
{
  "decision": "BUY",
  "confidence": 0.74,
  "probability_of_success": 0.67,
  "probability_model": "heuristic",
  "probability_sample_size": 0,
  "score_breakdown": {
    "regime": 0.82,
    "structure": 0.70,
    "momentum": 0.66,
    "trigger": 0.78,
    "risk_reward": 0.71
  }
}
```

## Integration Notes

- Default mode should be trend-following breakout with reversal support, not pure reversal trading.
- `VWAP_CANDLE_BREAKOUT_slope_dir_line`, `Fisher_Yur4ik3-a_v6_MTF`, `RSI_MFI_MA3`, `FX5_MACD_Divergence_V1_1_2`, `MTF_Fractal_v2`, and `Power_Candle_Alerts_v2` should be ported first.
- `ABCD_hand_v4`, `Binary_Options`, and `HL_Signal` are useful, but should be optional context because they are manual or session-specific.
- Backtests must record every feature value at the signal candle so the probability model can be calibrated later.
