# AI Trading Skill

Track 2 CMC-powered Strategy Skill for a deterministic, backtestable crypto strategy based on our own trading logic and analysis. This is not a live trading agent and does not sign transactions.

The core Track 2 product does not depend on the BNB AI Agent SDK. BNB SDK integration is reserved for optional bonus-prize enhancement, such as agent identity, discovery, or job-service wrapping around the existing strategy.

## Documentation

- [Project structure and workflow](docs/project_structure.md)
- [Strategy specification](docs/strategy_spec.md)

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

Fill only the values you need. Public Binance candle data works without an API key. Private exchange data, account data, trading, paid market data, explorer lookups, and notifications require the provider-specific keys below.

Never commit `.env`. It can contain exchange credentials, webhook URLs, and bot tokens.

### CoinMarketCap / CMC Agent Hub

Variables:

- `CMC_API_KEY`
- `CMC_BASE_URL`
- `CMC_CONVERT`
- `CMC_FALLBACK_PROVIDER`

`provider=cmc` is the default market-data path for the Strategy Skill. Set `CMC_API_KEY` to use CoinMarketCap historical OHLCV data. Without a CMC key, local development falls back to Binance public candles when `CMC_FALLBACK_PROVIDER=binance`.

Use this provider as the core CMC-powered data path for Track 2. The strategy itself remains our own deterministic indicator and scoring logic.

### Binance

Variables:

- `BINANCE_BASE_URL`
- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`

Use `BINANCE_BASE_URL=https://api.binance.com` for Binance Spot mainnet public data.

To get Binance API credentials:

1. Sign in to Binance.
2. Open API Management from your Binance account.
3. Create a new API key.
4. Store the API key in `BINANCE_API_KEY`.
5. Store the secret key in `BINANCE_API_SECRET`.
6. Keep permissions minimal. Public market data does not need a key. Account data needs user-data permission, and trading must be enabled separately only if live trading is intentionally implemented.
7. Use IP restrictions where possible.

Binance API docs: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/request-security

### CoinGecko

Variable:

- `COINGECKO_API_KEY`

CoinGecko public/demo endpoints may be enough for experiments, but CoinGecko Pro requires an API key.

To get a CoinGecko key:

1. Create or sign in to a CoinGecko API account.
2. Choose the plan required for the endpoints and limits you need.
3. Copy the API key from the CoinGecko developer dashboard.
4. Store it in `COINGECKO_API_KEY`.

When implemented, the app should send this key in the `x-cg-pro-api-key` header.

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
- `TELEGRAM_CHAT_ID`

To get a Telegram bot token:

1. Open Telegram and chat with `@BotFather`.
2. Run `/newbot`.
3. Follow the prompts and copy the bot token into `TELEGRAM_BOT_TOKEN`.
4. Send a message to the bot from the target Telegram account or group.
5. Use Telegram Bot API `getUpdates` or another trusted chat-id helper to find the target chat ID.
6. Store that ID in `TELEGRAM_CHAT_ID`.

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
- `POST /analyze`
- `POST /backtest`
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

If `market_data` is empty and no provider is specified, the app uses `provider=cmc`. Without `CMC_API_KEY`, it falls back to Binance public OHLCV for local development. You can still force Binance directly with `provider=binance`.

## Optional Notifications

Telegram:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Discord:

- `DISCORD_WEBHOOK_URL`
