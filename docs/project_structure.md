# Project Structure

This project is a CMC-powered deterministic crypto strategy Skill. It analyzes normalized OHLCV candles, calculates indicator-derived features from our own strategy logic, scores BUY and SELL evidence, and returns `BUY`, `SELL`, or `HOLD`. It does not place orders, sign transactions, or manage live funds.

The core Track 2 product uses CoinMarketCap as the primary provider when `market_data` is omitted. Binance remains a local no-key fallback and direct provider option. BNB AI Agent SDK integration is optional bonus/demo work, not a core dependency.

First implemented indicator-based Strategy Skill demo video:

- https://www.youtube.com/watch?v=TA6gRVvitJs

## Top-Level Layout

```text
ai_trading_skill/
  agent/                 FastMCP server and agent-facing adapters
  app/                   Flask API app and HTTP routes
  backtest/              Deterministic backtest engine
  bots/                  Optional notification senders
  data/                  Market-data providers and cache helpers
  docs/                  Strategy and project documentation
  indicators/            Native and ported indicator implementations
  skill/                 Core strategy Skill, recommendation Skill, schemas, and Skill spec
  tests/                 Unit and integration tests
  MT4Indicators/         Original MT4 indicator source references
  MT4EAS/                Original MT4 EA source references
```

## Runtime Surfaces

The same strategy logic is exposed through two interfaces.

Flask API:

```text
GET  /health
GET  /skill/spec
GET  /strategy/spec
GET  /indicator-recommendations/spec
POST /analyze
POST /backtest
POST /indicator-recommendations
POST /notify/test
```

FastMCP server:

```text
python3 -m agent.mcp_server
```

FastMCP tools:

```text
get_skill_spec
get_strategy_spec
analyze_strategy
make_trading_decision
backtest_strategy
get_mcp_manifest
```

FastMCP resources:

```text
skill://spec
strategy://spec
mcp://manifest
```

FastMCP prompt:

```text
trading_decision_request
```

## Core Request Flow

For `/analyze`, `analyze_strategy`, or `make_trading_decision`:

```text
client payload
  -> skill.signal_schema.AnalyzeRequest
  -> agent.skill_runner.analyze_payload
  -> data provider if market_data is empty
  -> skill.strategy_skill.StrategySkill.analyze
  -> indicator feature calculation
  -> scoring and risk context
  -> StrategyResult dict
```

Default provider behavior:

```text
market_data supplied -> use supplied normalized candles
market_data empty and provider omitted -> use provider=cmc
provider=cmc with CMC_API_KEY -> fetch CoinMarketCap historical OHLCV
provider=cmc without CMC_API_KEY -> fall back to CoinGecko when CMC_FALLBACK_PROVIDER=coingecko
provider=binance -> fetch Binance public OHLCV directly
```

`make_trading_decision` wraps the raw `StrategyResult` in a non-executing trade plan:

```text
BUY  -> long stop and long target from risk assumptions
SELL -> short stop and short target from risk assumptions
HOLD -> no entry, no stop, no target
```

The execution policy always states:

```text
places_orders: false
signs_transactions: false
```

For `/indicator-recommendations`:

```text
client payload
  -> skill.signal_schema.AnalyzeRequest
  -> market_data or data provider candles
  -> skill.indicator_recommendation_skill.IndicatorRecommendationSkill.analyze
  -> rolling indicator feature calculation from candle 60 onward
  -> per-indicator historical fit scoring
  -> indicator recommendation report
```

This route does not return a trading decision. It recommends which available indicators fit the selected symbol/timeframe and how strictly the user should filter their normalized signal strengths.

## Strategy Skill

Main file:

```text
skill/strategy_skill.py
```

Important functions:

```text
StrategySkill.analyze()
StrategySkill._calculate_features()
StrategySkill._score()
StrategySkill._risk_context()
strategy_spec()
```

The strategy uses five feature groups:

```text
regime
structure
momentum
trigger
risk_context
```

Decision thresholds:

```text
BUY:
  buy_score >= 0.68
  buy_score - sell_score >= 0.18
  reward_to_risk >= 1.5
  no bearish trigger blocker

SELL:
  sell_score >= 0.68
  sell_score - buy_score >= 0.18
  reward_to_risk >= 1.5
  no bullish trigger blocker

HOLD:
  evidence is mixed, stale, under threshold, or blocked
```

## Indicator Recommendation Skill

Main file:

```text
skill/indicator_recommendation_skill.py
```

Important functions:

```text
IndicatorRecommendationSkill.analyze_payload()
IndicatorRecommendationSkill.analyze()
indicator_recommendation_spec()
```

The recommendation skill is intentionally separate from `StrategySkill`. It reuses `StrategySkill._calculate_features()` to calculate the same indicator signals, then evaluates each indicator independently against historical forward returns.

Recommendation buckets:

```text
use                    strong enough historical fit to use as a primary input
use_with_confirmation  usable, but only with other indicator agreement
avoid_for_now          weak fit or too few signals for this symbol/timeframe
```

Scoring inputs:

```text
win rate
profit factor
average signal strength
sample size
signal coverage
```

The Flask dashboard exposes this skill on the `Indicator Fit` tab. The tab shares the same symbol, timeframe, provider, and candle-count controls as the main strategy view.

## Indicator Layer

Ported MT4 indicator implementations live in:

```text
indicators/custom_mql_ported/
```

Current indicator ports:

```text
abcd_hand.py
apex_indi.py
demark_support.py
fisher_yur4ik.py
hl_signal.py
macd_osma.py
rsi_mfi_ma3.py
vwap_candle_breakout.py
```

Each indicator returns:

```python
tuple[FeatureSignal, dict]
```

`FeatureSignal` contains:

```text
direction: BUY | SELL | NEUTRAL
strength: 0.0 to 1.0
freshness_bars
level
reason
```

The second return value is a dictionary with raw values, levels, targets, or implementation details for explainability and backtesting snapshots.

## Implemented MT4 Logic

`ABCD_hand_v4.mq4`

```text
Role: structure context
Logic: infer A/B/C from recent swings, project D as C + PLevel * abs(B - A), expose Fibonacci levels
```

`De_Mark_Support_V2.mq4`

```text
Role: structure confirmation
Logic: support/resistance trendline anchor, TD1/TD2/TD3 breakout checks, projected target
```

`APEX_Indi.mq4`

```text
Role: trigger
Logic: A-P-E setup followed by recent X breakout
```

`HL_Signal.mq4`

```text
Role: session structure context
Logic: 09:00-18:00 high/low expansion and reset conditions
```

`VWAP_CANDLE_BREAKOUT_slope_dir_line.mq4`

```text
Role: primary execution trigger
Logic: VWAP cross, candle body threshold, slope direction confirmation
```

`Fisher_Yur4ik3-a_v6_MTF.mq4`

```text
Role: regime
Logic: Fisher transform threshold direction
```

`RSI_MFI_MA3.mq4`

```text
Role: momentum participation
Logic: RSI/MFI relative to combined moving average and close direction
```

`MACD_OSMA_Bar_alert.mq4`

```text
Role: momentum transition
Logic: OsMA sign, slope, and candle direction
```

`Power_Candle_Alerts_v2.mq4`

```text
Role: trigger confirmation and blocker
Logic: candle range relative to recent average range
```

## Scoring

Scoring happens in `StrategySkill._score()`.

Current score weights:

```text
0.25 regime
0.25 structure
0.20 momentum
0.20 trigger
0.10 risk_reward
```

Structure combines:

```text
rolling support/resistance
ABCD projection
DeMark breakout
HL session signal
```

Trigger combines:

```text
VWAP breakout
APEX X event
power candle
```

Momentum combines:

```text
RSI/MFI
MACD OsMA
```

## Data Providers

Provider code lives in:

```text
data/providers/
```

Supported provider names in request payloads:

```text
binance
coingecko
coinpaprika
defillama
```

If `market_data` is supplied in the request, the strategy uses that directly and does not fetch from providers. If `market_data` is empty, `agent.skill_runner.analyze_payload()` loads a provider and requests candles.

## Backtesting

Main file:

```text
backtest/engine.py
```

Backtest flow:

```text
payload
  -> candles from market_data or provider
  -> rolling analysis from candle 60 onward
  -> enter on next candle close when decision is BUY or SELL
  -> exit on 2% move or when decision conflicts
  -> return trade list, signal history, win rate, drawdown, total return
```

Backtest assumptions:

```text
closed-candle signals
next-close execution
no fees
no slippage
no live execution
heuristic probability model
```

## Flask App

Main files:

```text
app/flask_app.py
app/routes.py
```

Route handlers are intentionally thin. They parse JSON, call core application functions, catch `ValueError`, and return JSON. Strategy logic should not be added directly to route handlers.

## FastMCP Server

Main file:

```text
agent/mcp_server.py
```

The MCP server is a tool surface over the same Skill logic used by Flask.

Important functions:

```text
make_trading_decision(payload)
analyze_strategy(payload)
backtest_strategy(payload)
get_skill_spec()
get_strategy_spec()
get_mcp_manifest()
```

`make_trading_decision` is the main MCP trading-decision entry point. It returns a decision and a plan, but the plan is advisory only. It does not execute.

## Schemas And Specs

Main files:

```text
skill/signal_schema.py
skill/spec.py
skill/indicator_recommendation_skill.py
docs/strategy_spec.md
docs/indicator_recommendation_skill.md
```

`skill/signal_schema.py` defines Python dataclasses:

```text
Candle
FeatureSignal
StrategyResult
AnalyzeRequest
```

`skill/spec.py` exposes the agent/Skill-facing spec used by Flask and MCP discovery.

`docs/strategy_spec.md` describes the strategy rules and indicator roles in human-readable form.

`docs/indicator_recommendation_skill.md` describes the separate symbol-level indicator-fit workflow.

## Notifications

Main files:

```text
bots/telegram_bot.py
bots/discord_bot.py
```

Notifications are optional and only used by `/notify/test` currently. They are not part of the trading decision loop.

## Tests

Tests live in:

```text
tests/
```

Coverage areas:

```text
test_abcd_hand.py              ABCD formula and snap behavior
test_additional_mql_ports.py   DeMark, APEX, and HL port integration
test_env.py                    environment loading
test_flask_routes.py           Flask API routes
test_indicator_recommendation_skill.py  indicator fit report shape
test_skill_spec.py             Skill spec and MCP decision contract
test_strategy_skill.py         core strategy result shape
```

Run:

```bash
pytest
```

Compile check:

```bash
python3 -m compileall skill indicators/custom_mql_ported agent app tests
```

## Adding A New Indicator

Use this process:

1. Add the Python implementation under `indicators/custom_mql_ported/`.
2. Return `tuple[FeatureSignal, dict]`.
3. Export it from `indicators/custom_mql_ported/__init__.py`.
4. Call it in `StrategySkill._calculate_features()`.
5. Add its signal into `_score()` under the correct feature group.
6. Add raw values to `indicator_values`.
7. Update `strategy_spec()` and `docs/strategy_spec.md`.
8. Add focused tests for the formula or signal behavior.

## Safety Boundaries

This project is Track 2 strategy-skill logic only.

It does not:

```text
place market or limit orders
sign wallet transactions
hold private keys
manage custody
perform autonomous execution
guarantee profit or probability estimates
```

Any live execution system must be a separate component with explicit user approval, custody rules, risk controls, exchange/wallet integration, and independent tests.
