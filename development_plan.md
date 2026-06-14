# Track 2 Development Plan

## Goal

Build a Track 2 CMC-powered Strategy Skill that analyzes crypto market data, applies our own ported MetaTrader/MQL indicator logic, produces a backtestable trading decision, exposes the workflow through a Flask app, and publishes analysis results to Telegram and Discord.

This is **not** a live trading agent. It does not execute trades, sign transactions, or register for Track 1 on-chain competition. The BNB AI Agent SDK may be used only as an optional bonus-prize enhancement, not as a dependency for the core Track 2 product.

First implemented indicator-based Strategy Skill demo video:

- https://www.youtube.com/watch?v=TA6gRVvitJs

Indicator Recommendation Skill demo video:

- https://youtu.be/j8ii27bbz4A

## Architecture

```text
ai_trading_skill/
  app/
    flask_app.py
    routes.py
  agent/
    bnb_agent_runner.py
    skill_runner.py
  skill/
    strategy_skill.py
    signal_schema.py
    prompt_templates.py
  indicators/
    rsi.py
    macd.py
    custom_mql_ported/
  data/
    providers/
      cmc_agent_hub.py
      coingecko.py
      coinpaprika.py
      defillama.py
      binance.py
    cache.py
  backtest/
    engine.py
    reports.py
  bots/
    telegram_bot.py
    discord_bot.py
  tests/
  docs/
```

## 1. Build the Flask Application Skeleton

Create the base Flask API with these endpoints:

- `GET /health`
- `POST /analyze`
- `POST /backtest`
- `POST /notify/test`
- `GET /strategy/spec`

The Flask app will be the main local demo surface for the hackathon.

## 2. Add Market Data Provider Layer

Create one normalized data interface so the strategy does not care where candles or market context come from.

Normalized candle format:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "timestamp": 1234567890,
  "open": 0.0,
  "high": 0.0,
  "low": 0.0,
  "close": 0.0,
  "volume": 0.0
}
```

Recommended providers:

- CoinMarketCap / CMC Agent Hub as the primary Track 2 market-data path.
- CoinGecko for broad market data and historical data.
- CoinPaprika for free/no-card price, volume, market-cap, and historical data.
- DefiLlama for free DeFi/on-chain context, TVL, DEX volumes, stablecoins, yields, and open interest.
- Binance public market data for OHLCV candles and exchange-style market data.

Implementation order:

1. CoinMarketCap / CMC Agent Hub OHLCV adapter.
2. Binance OHLCV fallback adapter for no-key local development.
3. CoinPaprika adapter.
4. DefiLlama context adapter.
5. CoinGecko adapter.

## 3. Port MQL Indicators

The trading logic will come from the working MetaTrader/MQL indicators provided later.

Process for every indicator:

1. Inventory indicator inputs, buffers, timeframes, and outputs.
2. Identify exact formulas and edge-case behavior.
3. Port the logic to Python as a pure function.
4. Export sample MetaTrader results to CSV.
5. Add golden tests comparing Python output against MetaTrader output.
6. Only use the indicator in the Skill after tests match.


Target structure:

```text
indicators/
  custom_mql_ported/
    indicator_name.py
tests/
  fixtures/
    indicator_name_metatrader_output.csv
  test_indicator_name.py
```

## 4. Build the Strategy Skill

The Skill receives market data, indicator config, and risk settings.

Example request:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "lookback": 300,
  "risk_profile": "balanced",
  "market_data": []
}
```

Example response:

```json
{
  "decision": "BUY",
  "confidence": 0.72,
  "entry_reason": "Momentum and trend filters agree.",
  "exit_rules": "Exit on opposite signal or volatility stop.",
  "risk": {
    "stop_loss": "2.0%",
    "take_profit": "4.0%",
    "max_position_size": "10%"
  },
  "indicator_snapshot": {},
  "backtestable_rules": []
}
```

Allowed decisions:

- `BUY`
- `SELL`
- `HOLD`

The Skill must always return:

- decision
- confidence
- probability_of_success
- probability_model (`heuristic` before calibration, `calibrated` after enough backtest data)
- score_breakdown
- indicator values
- explanation
- risk assumptions
- backtestable rules

The combined indicator logic is defined in `logic_for_skill.md`.

Implementation priorities for the first deterministic version:

1. Port `VWAP_CANDLE_BREAKOUT_slope_dir_line` as the primary execution trigger.
2. Port `Fisher_Yur4ik3-a_v6_MTF` as the higher-timeframe regime filter.
3. Port `RSI_MFI_MA3` and `MACD_OSMA_Bar_alert` as momentum/participation filters.
4. Port `FX5_MACD_Divergence_V1_1_2` as reversal/continuation divergence evidence.
5. Port `MTF_Fractal_v2`, `FIBO_Simple_v3`, and `De_Mark_Support_V2` as support/resistance, target, and invalidation context.
6. Port `Power_Candle_Alerts_v2`, `IndCandleBreakout_v3`, `APEX_Indi`, and the hammer/shooting-star indicator as trigger/confluence modules.
7. Keep `ABCD_hand_v4`, `Binary_Options`, `HL_Signal`, `Range_n_Line_v8_1`, and `Seq_Boool_Bear_v7.1` as optional context until their behavior is validated for 24/7 crypto markets.

Combined decision model:

- Group indicator outputs into `regime`, `structure`, `momentum`, `trigger`, and `risk_context`.
- Generate BUY only when bullish score is at least `0.68`, bearish conflict is at least `0.18` lower, reward-to-risk is at least `1.5R`, and no hard bearish blocker is active.
- Generate SELL only when bearish score is at least `0.68`, bullish conflict is at least `0.18` lower, reward-to-risk is at least `1.5R`, and no hard bullish blocker is active.
- Return HOLD when evidence is mixed, stale, under-threshold, or blocked by nearby opposing structure.
- Estimate `probability_of_success` from directional edge first, then replace it with calibrated historical win-rate buckets after backtesting has enough samples.

## 5. Build the Backtest Engine

The backtest engine should replay candles and call the Skill or the deterministic strategy rules.

Minimum report fields:

- total return
- win rate
- max drawdown
- number of trades
- average trade return
- signal history
- per-trade feature snapshot and score breakdown
- probability estimate at entry
- probability calibration bucket and sample size
- assumptions
- input data range

Output formats:

- JSON for API responses
- CSV for detailed signal/trade history
- Markdown summary for DoraHacks documentation

## 6. Add Telegram and Discord Publishing

Telegram:

- Use a bot token from BotFather.
- Send messages through Telegram Bot API.
- Required environment variables:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`

Discord:

- Start with Discord incoming webhooks.
- Required environment variable:
  - `DISCORD_WEBHOOK_URL`

Notification format:

```text
BTCUSDT 1h
Decision: HOLD
Confidence: 62%
Reason: Momentum positive, but volatility filter blocks entry.
Risk: wait for pullback or confirmed breakout.
```

## 7. Add BNB AI Agent SDK Demo Layer

Use BNB AI Agent SDK as an optional bonus/demo layer, not as the core Track 2 requirement.

Planned usage:

1. Wrap the Strategy Skill so the BNB SDK can call it.
2. Optionally expose analysis as an agent service/job.
3. Optionally register an agent identity on BSC testnet for demo/discovery.
4. Document clearly that this is not Track 2 on-chain registration.

This may help target the cross-track "Best Use of BNB AI Agent SDK" bonus, but the core Track 2 product remains the Strategy Skill.

## 8. Flask Request Flow

`POST /analyze` flow:

1. Validate request payload.
2. Resolve symbol and timeframe.
3. Fetch normalized market data.
4. Run indicators.
5. Run Strategy Skill.
6. Save analysis result.
7. Optionally send result to Telegram and Discord.
8. Return JSON response.

`POST /backtest` flow:

1. Validate request payload.
2. Fetch historical candles.
3. Run indicator calculations over the full series.
4. Replay strategy rules.
5. Generate report.
6. Return JSON and save report artifact.

## 9. Environment Variables

```text
FLASK_ENV=development
APP_SECRET_KEY=

CMC_API_KEY=
COINGECKO_API_KEY=

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=

BNB_AGENT_PRIVATE_KEY=
BNB_AGENT_WALLET_PASSWORD=
BNB_AGENT_NETWORK=bsc-testnet
```

Only optional services should require keys. The app should still run locally without Telegram, Discord, CMC, or BNB SDK configured.

## 10. Documentation for Submission

Prepare these files:

- `README.md`: setup, run, API usage, demo flow.
- `docs/strategy_spec.md`: exact backtestable strategy rules.
- `docs/data_sources.md`: APIs used and fallback behavior.
- `docs/indicator_porting.md`: how MQL indicators were ported and tested.
- `docs/demo_script.md`: step-by-step judging demo.

## 11. Development Order

1. Create Flask skeleton.
2. Add normalized data provider interface.
3. Implement Binance OHLCV provider.
4. Implement CoinPaprika provider.
5. Add basic `/analyze` endpoint with placeholder strategy.
6. Port first MQL indicator.
7. Add golden tests against MetaTrader CSV output.
8. Replace placeholder strategy with real Strategy Skill logic.
9. Add `/backtest`.
10. Add Telegram notification sender.
11. Add Discord webhook sender.
12. Add BNB AI Agent SDK wrapper/demo.
13. Write submission documentation.
14. Record demo video or prepare live demo script.

## 12. Current Decision

Build the Flask app and Skill engine first.

Then add market data providers.

Then port the MQL indicators with tests.

Then add notifications.

Then add the BNB AI Agent SDK demo/checking layer.

The strongest Track 2 submission will be the one with a clear original strategy, reproducible backtest logic, and explainable signals based on the provided indicator analysis.
