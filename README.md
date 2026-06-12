# AI Trading Skill

Track 2 CMC-style Strategy Skill for a deterministic, backtestable crypto strategy. This is not a live trading agent and does not sign transactions.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run API

```bash
python -m app.flask_app
```

Endpoints:

- `GET /health`
- `GET /strategy/spec`
- `POST /analyze`
- `POST /backtest`
- `POST /notify/test`

## Analyze With Inline Candles

```bash
curl -X POST http://localhost:5000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTCUSDT","timeframe":"1h","market_data":[]}'
```

If `market_data` is empty, the app tries Binance public OHLCV through `provider=binance`.

## Optional Notifications

Telegram:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Discord:

- `DISCORD_WEBHOOK_URL`

