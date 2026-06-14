# AI Trading Skill

![AI Trading Skill logo](ai_crypto_skill_logo.jpg)

Track 2 CMC-powered Strategy Skill for a deterministic, backtestable crypto strategy based on our own trading logic and analysis. This is not a live trading agent and does not sign transactions.

The core Track 2 product does not depend on the BNB AI Agent SDK. BNB SDK integration is reserved for optional bonus-prize enhancement, such as agent identity, discovery, or job-service wrapping around the existing strategy.

First implemented indicator-based Strategy Skill demo video:

- https://www.youtube.com/watch?v=TA6gRVvitJs

Indicator Recommendation Skill demo video:

- https://youtu.be/j8ii27bbz4A

## Documentation

- [Project structure and workflow](docs/project_structure.md)
- [Strategy specification](docs/strategy_spec.md)
- [Indicator Recommendation Skill](docs/indicator_recommendation_skill.md)
- [Agent Skill: CMC Strategy Skill](skills/cmc-strategy-skill/SKILL.md)
- [Agent Skill: Indicator Recommendation Skill](skills/indicator-recommendation-skill/SKILL.md)

## Agent Skill Definitions

This repository includes two Codex-style `SKILL.md` files for agent-facing operation:

- `skills/cmc-strategy-skill/SKILL.md`: describes the deterministic CMC-powered strategy workflow, BUY/SELL/HOLD scoring logic, risk assumptions, Flask/FastMCP interfaces, and non-execution boundaries.
- `skills/indicator-recommendation-skill/SKILL.md`: describes the historical indicator-fit workflow, suitability scoring, recommendation buckets, API surface, and advisory-only boundaries.

The Python implementation remains under `skill/`. The `skills/` directory is documentation and prompt guidance for agents that need to operate or explain the two implemented skills.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Environment Setup

Create a local `.env` file from the tracked example:

```bash
cp .env.example .env
```

Fill only the values you need. The local no-key fallback uses CoinGecko. Private exchange data, account data, trading, paid market data, explorer lookups, and notifications require the provider-specific keys below.

Never commit `.env`. It can contain exchange credentials, webhook URLs, and bot tokens.

### CoinMarketCap / CMC Agent Hub

`provider=cmc` is the default market-data path for the Strategy Skill. Set `CMC_API_KEY` to use CoinMarketCap historical OHLCV data. Without a CMC key, local development falls back to CoinGecko when `CMC_FALLBACK_PROVIDER=coingecko`.

How to fill the CMC variables:

1. Create or sign in to a CoinMarketCap API account at https://pro.coinmarketcap.com/signup/.
2. Open the CoinMarketCap API dashboard and copy your API key.
3. Paste the key into your local `.env` file as `CMC_API_KEY`.
4. Keep `CMC_BASE_URL=https://pro-api.coinmarketcap.com` unless CoinMarketCap tells you to use a different endpoint.
5. Keep `CMC_CONVERT=USD` unless you want OHLCV prices normalized to another supported quote currency.
6. Keep `CMC_FALLBACK_PROVIDER=coingecko` for no-key local development. Set it to `none` or `disabled` if you want `provider=cmc` to fail when `CMC_API_KEY` is missing.

```env
CMC_API_KEY=your_coinmarketcap_api_key_here
CMC_BASE_URL=https://pro-api.coinmarketcap.com
CMC_CONVERT=USD
CMC_FALLBACK_PROVIDER=coingecko
```

Use this provider as the core CMC-powered data path for Track 2. The strategy itself remains our own deterministic indicator and scoring logic.

### Binance

Variables:

- `BINANCE_BASE_URL`

Use `BINANCE_BASE_URL=https://api.binance.com` only if you explicitly request `provider=binance`. Binance is no longer used as the default no-key fallback.

No Binance API key is needed by this project because it does not call signed/private Binance endpoints or execute live trades.

### CoinGecko

Variable:

- `COINGECKO_BASE_URL`
- `COINGECKO_API_KEY`

CoinGecko is the default no-key fallback for local market data when `CMC_API_KEY` is not configured. `COINGECKO_API_KEY` is optional and only needed for paid endpoints or higher rate limits.

To get a CoinGecko key:

1. Create or sign in to a CoinGecko API account.
2. Choose the plan required for the endpoints and limits you need.
3. Copy the API key from the CoinGecko developer dashboard.
4. Store it in `COINGECKO_API_KEY`.

When configured, the app sends this key in the `x-cg-pro-api-key` header.

CoinGecko auth docs: https://docs.coingecko.com/reference/authentication

### CoinPaprika

Variable:

- `COINPAPRIKA_API_KEY`

CoinPaprika supports simple public market-data requests without a key, but paid plans can be used for higher limits and advanced data.

To get a CoinPaprika key:

1. Create or sign in to a CoinPaprika account.
2. Open the API Dashboard.
3. Select the plan needed for your limits and data coverage.
4. Copy the API key into `COINPAPRIKA_API_KEY`.

CoinPaprika docs: https://docs.coinpaprika.com/

### BNB Chain RPC

Variable:

- `BNB_RPC_URL`

This is not always an API key. It is the JSON-RPC endpoint the app will use for BNB Chain on-chain reads.

Options:

1. Use a public BNB Chain RPC URL for local experiments.
2. For production or heavier usage, create an RPC endpoint with a provider such as QuickNode, Alchemy, Ankr, or another infrastructure provider.
3. Copy the full HTTPS RPC endpoint into `BNB_RPC_URL`.

BNB Chain RPC docs: https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/

### Etherscan API V2

Variable:

- `ETHERSCAN_API_KEY`

Use this for explorer-style data such as source/ABI lookup, transactions, token transfers, and contract metadata on supported EVM chains. Etherscan API V2 uses one account/key system across supported chains; BNB Smart Chain mainnet uses `chainid=56`.

To get the key:

1. Create or sign in to an Etherscan account.
2. Open the API Dashboard.
3. Click `Add +` to create an API key.
4. Store it in `ETHERSCAN_API_KEY`.
5. Check the supported-chain and plan limits before using it for BNB Smart Chain data.

Etherscan getting started docs: https://docs.etherscan.io/getting-started

### Telegram

Variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHANNEL_ID`
- `TELEGRAM_CHAT_ID`

To get a Telegram bot token:

1. Open Telegram and chat with `@BotFather`.
2. Run `/newbot`.
3. Follow the prompts and copy the bot token into `TELEGRAM_BOT_TOKEN`.
4. Add the bot to the target channel or group and grant posting permission.
5. Use Telegram Bot API `getUpdates` or another trusted chat-id helper to find the target channel ID.
6. Store that ID in `TELEGRAM_CHANNEL_ID`. Private channel and supergroup IDs usually start with `-100`.
7. `TELEGRAM_CHAT_ID` is still supported as a fallback for older configs or direct chat notifications.

Telegram bot docs: https://core.telegram.org/bots/features#botfather

### Discord

Variable:

- `DISCORD_WEBHOOK_URL`

To get a Discord webhook URL:

1. Open the target Discord server.
2. Open the channel settings for the channel that should receive alerts.
3. Go to Integrations.
4. Create or open a webhook.
5. Copy the webhook URL into `DISCORD_WEBHOOK_URL`.

Discord webhook docs: https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks

## Run API

```bash
python -m app.flask_app
```

Endpoints:

- `GET /health`
- `GET /skill/spec`
- `GET /strategy/spec`
- `GET /indicator-recommendations/spec`
- `POST /analyze`
- `POST /backtest`
- `POST /indicator-recommendations`
- `POST /notify/test`

## FastMCP

Install the optional MCP dependency and run the skill server:

```bash
pip install -e ".[mcp]"
python3 -m agent.mcp_server
```

FastMCP tools:

- `get_skill_spec`
- `get_strategy_spec`
- `analyze_strategy`
- `make_trading_decision`
- `backtest_strategy`
- `get_mcp_manifest`

FastMCP resources:

- `skill://spec`
- `strategy://spec`
- `mcp://manifest`

FastMCP prompt:

- `trading_decision_request`

## Analyze With Inline Candles

```bash
curl -X POST http://localhost:5000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","timeframe":"1h","market_data":[]}'
```

If `market_data` is empty and no provider is specified, the app uses `provider=cmc`. Without `CMC_API_KEY`, it falls back to CoinGecko for local development when `CMC_FALLBACK_PROVIDER=coingecko`. You can still force Binance directly with `provider=binance`.

## Recommend Indicators For A Symbol

The app includes a separate Indicator Recommendation Skill. It checks the selected symbol/timeframe against historical candles and recommends which implemented indicators are best suited, which should be used only with confirmation, and which should be avoided for now.

Use it from the Flask UI on the `Indicator Fit` tab, or call the API directly:

```bash
curl -X POST http://localhost:5000/indicator-recommendations \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","timeframe":"4h","lookback":140,"provider":"coingecko","market_data":[]}'
```

This endpoint is advisory only. It does not return a trade order; it returns indicator-fit recommendations and suggested normalized signal-strength filters.

## Optional Notifications

Telegram:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

When these are configured, pressing `Run Skill Analysis` in the Flask UI sends the completed analysis summary to Telegram. API callers can request the same behavior by adding `"notify_telegram": true` to the `/analyze` JSON payload.

Discord:

- `DISCORD_WEBHOOK_URL`
