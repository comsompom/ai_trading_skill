# Strategy Spec

This Track 2 Skill is a CMC-powered deterministic, backtestable crypto strategy based on our own indicator logic and analysis. It does not sign transactions or execute live trades.

CoinMarketCap is the primary provider when candles are not supplied in the request. Binance remains a local fallback for no-key development. BNB AI Agent SDK usage is optional bonus/demo work and is not required by the core strategy.

## Inputs

- Normalized OHLCV candles with `symbol`, `timeframe`, `timestamp`, `open`, `high`, `low`, `close`, and `volume`.
- `risk_profile`: `conservative`, `balanced`, or `aggressive`.

## Implemented First-Version Logic

- Regime: Fisher Yur4ik-style Fisher transform.
- Structure: rolling support/resistance breakout proxy, `ABCD_hand_v4` projection context, `De_Mark_Support_V2` TD breakouts, and `HL_Signal` session high/low context.
- Momentum: RSI/MFI versus combined moving average and MACD OsMA transition.
- Trigger: VWAP candle breakout with slope-direction confirmation, `APEX_Indi` A-P-E-X completion, and power-candle impulse.
- Risk: ATR-padded stops and fixed reward-to-risk profile.

## ABCD Hand Logic

`ABCD_hand_v4.mq4` is included as deterministic structure context. The original MT4 indicator is an interactive chart tool: clicked A, B, and C points snap to a nearby 3-bar high/low extreme, then D is projected as `D = C + PLevel * abs(B - A)`. The Python port infers A, B, and C from recent alternating swing points so the skill can run from normalized candles, and it exposes the projected D target plus the same Fibonacci level set used by the MQL indicator.

## Added MT4 Indicator Logic

`De_Mark_Support_V2.mq4` contributes structure. The port builds a support or resistance trendline from recent extreme anchors, checks TD1/TD2/TD3-style break conditions, and exposes the projected target when a breakout is active.

`APEX_Indi.mq4` contributes trigger strength. The port scans for the A-P-E setup and gives a strong BUY or SELL trigger only when the final X breakout leg completes recently.

`HL_Signal.mq4` contributes session context. The port tracks 09:00-18:00 high/low expansion and reset behavior, then adds BUY/SELL context when the session high or low failure condition appears.

## Decision Rules

- BUY requires `buy_score >= 0.68`, `buy_score - sell_score >= 0.18`, reward-to-risk at least `1.5R`, and no hard bearish trigger blocker.
- SELL requires `sell_score >= 0.68`, `sell_score - buy_score >= 0.18`, reward-to-risk at least `1.5R`, and no hard bullish trigger blocker.
- HOLD is returned for mixed, stale, blocked, or under-threshold evidence.

## Probability

The first version uses the heuristic transform from `logic_for_skill.md`. Calibration will replace this after enough backtest samples exist.
