# Strategy Spec

This Track 2 Skill is a deterministic, backtestable crypto strategy. It does not sign transactions or execute live trades.

## Inputs

- Normalized OHLCV candles with `symbol`, `timeframe`, `timestamp`, `open`, `high`, `low`, `close`, and `volume`.
- `risk_profile`: `conservative`, `balanced`, or `aggressive`.

## Implemented First-Version Logic

- Regime: Fisher Yur4ik-style Fisher transform.
- Structure: rolling support/resistance breakout proxy.
- Momentum: RSI/MFI versus combined moving average and MACD OsMA transition.
- Trigger: VWAP candle breakout with slope-direction confirmation and power-candle impulse.
- Risk: ATR-padded stops and fixed reward-to-risk profile.

## Decision Rules

- BUY requires `buy_score >= 0.68`, `buy_score - sell_score >= 0.18`, reward-to-risk at least `1.5R`, and no hard bearish trigger blocker.
- SELL requires `sell_score >= 0.68`, `sell_score - buy_score >= 0.18`, reward-to-risk at least `1.5R`, and no hard bullish trigger blocker.
- HOLD is returned for mixed, stale, blocked, or under-threshold evidence.

## Probability

The first version uses the heuristic transform from `logic_for_skill.md`. Calibration will replace this after enough backtest samples exist.

