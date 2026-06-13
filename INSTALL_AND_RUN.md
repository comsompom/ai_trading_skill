# Install, Run, and Prove the Project Works

This project is a Python Flask API for a deterministic crypto strategy Skill. It analyzes candles, returns BUY/SELL/HOLD decisions, can run a backtest, and exposes optional FastMCP tools. It is not a live trading bot and does not place orders.

## 1. Open the Project

```bash
cd /Users/olegbourdo/Development/ai_trading_skill
```

## 2. Create and Activate Python

Use Python 3.11 or newer:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

If your system uses `python` instead of `python3`, use:

```bash
python --version
python -m venv .venv
source .venv/bin/activate
```

After activation, your prompt should usually show `(.venv)`.

## 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

This installs Flask, requests, the local package, and pytest.

## 4. Create Local Environment

Create `.env` from the tracked example if it does not already exist:

```bash
cp .env.example .env
```

For a no-key local demo, these values are enough:

```env
CMC_API_KEY=
CMC_FALLBACK_PROVIDER=coingecko
COINGECKO_API_KEY=
BNB_RPC_URL=
ETHERSCAN_API_KEY=
```

Notes:

- `CMC_API_KEY` can stay empty for local testing.
- `CMC_FALLBACK_PROVIDER=coingecko` avoids Binance.
- `COINGECKO_API_KEY` can stay empty unless you need higher limits.
- `BNB_RPC_URL` and `ETHERSCAN_API_KEY` are not used by the current strategy flow, so they can stay empty.

## 5. Run Automated Tests

```bash
python -m pytest
```

Expected result:

```text
23 passed
```

This proves the strategy logic, provider adapters, Flask routes, and specs work in a deterministic test run.

## 6. Start the Flask API

On macOS, port `5000` is often used by Control Center / AirPlay Receiver. Use `5050` for the demo:

```bash
PORT=5050 python -m app.flask_app
```

Expected startup:

```text
Running on http://127.0.0.1:5050
Running on http://<your-local-ip>:5050
```

Keep this terminal open.

## 7. Check the API

Open the dashboard in your browser:

```text
http://localhost:5050/
```

You should see:

- Market setup controls for symbol, timeframe, candle count, provider, and risk profile.
- A symbol preset dropdown plus a custom symbol field.
- A candlestick chart with OHLC bodies and wicks.
- Buttons for `Generate Demo Candles`, `Load Market Data`, `Run Skill Analysis`, and `Run Backtest`.
- An `Auto Check Market` switch that refreshes live candles and runs the skill repeatedly.
- Decision, score breakdown, risk context, and activity panels.

Then open a second terminal, activate the venv, and call health:

```bash
cd /Users/olegbourdo/Development/ai_trading_skill
source .venv/bin/activate
curl http://localhost:5050/health
```

Expected response:

```json
{
  "service": "ai_trading_skill",
  "status": "ok"
}
```

Check the strategy and Skill metadata:

```bash
curl http://localhost:5050/strategy/spec
curl http://localhost:5050/skill/spec
```

These should return JSON documents describing the strategy, indicators, interfaces, and input/output schema.

You can use either the browser dashboard or the terminal smoke tests below. The dashboard is the best way to show the project working visually.

## 8. Prove Analyze Works Without Any API Key

Run this offline smoke test. It generates normalized candles locally and posts them to `/analyze`, so it does not need CoinMarketCap, CoinGecko, Binance, BNB RPC, or Etherscan.

```bash
python - <<'PY'
import json
import time
import requests

now = int(time.time()) // 3600 * 3600
candles = []
price = 100.0

for i in range(120):
    price += 0.15
    candles.append({
        "symbol": "BTCUSDT",
        "timeframe": "4h",
        "timestamp": now - (119 - i) * 3600,
        "open": price,
        "high": price + 1.2,
        "low": price - 0.8,
        "close": price + 0.4,
        "volume": 1000 + i,
    })

payload = {
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "lookback": 120,
    "risk_profile": "balanced",
    "market_data": candles,
}

response = requests.post("http://localhost:5050/analyze", json=payload, timeout=10)
print(json.dumps(response.json(), indent=2))
response.raise_for_status()
PY
```

Expected signs that it works:

- The JSON has `symbol`, `timeframe`, `decision`, `confidence`, and `probability_of_success`.
- `decision` is one of `BUY`, `SELL`, or `HOLD`.
- `risk_assumptions` contains deterministic stop/target levels.
- `indicator_values` contains the implemented indicator outputs.

## 9. Prove Backtest Works Without Any API Key

Run this offline backtest smoke test:

```bash
python - <<'PY'
import json
import time
import requests

now = int(time.time()) // 3600 * 3600
candles = []
price = 100.0

for i in range(140):
    drift = 0.2 if i < 80 else -0.1
    price += drift
    candles.append({
        "symbol": "BTCUSDT",
        "timeframe": "4h",
        "timestamp": now - (139 - i) * 3600,
        "open": price,
        "high": price + 1.5,
        "low": price - 1.0,
        "close": price + 0.3,
        "volume": 1500 + i,
    })

payload = {
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "lookback": 140,
    "risk_profile": "balanced",
    "market_data": candles,
}

response = requests.post("http://localhost:5050/backtest", json=payload, timeout=10)
result = response.json()
summary = {
    "number_of_trades": result.get("number_of_trades"),
    "candles": result.get("input_data_range", {}).get("candles"),
    "signal_history_count": len(result.get("signal_history", [])),
    "max_drawdown": result.get("max_drawdown"),
    "total_return": result.get("total_return"),
}
print(json.dumps(summary, indent=2))
response.raise_for_status()
PY
```

Expected signs that it works:

- The JSON includes `number_of_trades`, `candles`, and `signal_history_count`.
- `candles` should match the generated candle count.
- `signal_history_count` should be greater than `0`.
- No exchange account, wallet, API key, or live trading permission is needed.

## 10. Optional Live Market Data Demo

Use this only when your machine has internet access. With `CMC_API_KEY` empty and `CMC_FALLBACK_PROVIDER=coingecko`, the app will use CoinGecko as the no-key fallback.

```bash
curl -X POST http://localhost:5050/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"4h","lookback":80,"provider":"cmc","risk_profile":"balanced","market_data":[]}'
```

If CoinGecko rate limits or blocks the request, use the offline smoke test above. The offline test is the best demo path when you want a reliable proof that the project itself works.

## 11. Optional Notification Demo

Notifications are optional. Configure only the channels you want to test.

Telegram:

```bash
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export TELEGRAM_CHAT_ID="your-telegram-chat-id"
```

Discord:

```bash
export DISCORD_WEBHOOK_URL="your-discord-webhook-url"
```

Restart the Flask API after setting these values, then run:

```bash
curl -X POST http://localhost:5050/notify/test \
  -H "Content-Type: application/json" \
  -d '{"message":"AI Trading Skill notification test","channels":["telegram","discord"]}'
```

If variables are missing, the endpoint returns `sent: false` with the reason.

## 12. Optional FastMCP Server

Install the MCP extra:

```bash
pip install -e ".[mcp]"
```

Run the FastMCP server:

```bash
python -m agent.mcp_server
```

It exposes these tools:

- `get_skill_spec`
- `get_strategy_spec`
- `analyze_strategy`
- `make_trading_decision`
- `backtest_strategy`
- `get_mcp_manifest`

Resources:

- `skill://spec`
- `strategy://spec`
- `mcp://manifest`

Prompt:

- `trading_decision_request`

## 13. Stop the Server

In the terminal running Flask, press:

```text
Ctrl+C
```

## 14. Start Again Later

```bash
cd /Users/olegbourdo/Development/ai_trading_skill
source .venv/bin/activate
PORT=5050 python -m app.flask_app
```

## 15. Quick Demo Checklist

Use this checklist when showing the working project:

```bash
source .venv/bin/activate
python -m pytest
PORT=5050 python -m app.flask_app
```

In a second terminal:

```bash
open http://localhost:5050/
curl http://localhost:5050/health
curl http://localhost:5050/strategy/spec
curl http://localhost:5050/skill/spec
```

In the browser, choose a symbol, click `Load Market Data`, then `Run Skill Analysis`. Turn on `Auto Check Market` to let the app refresh live candles and update the suggestion automatically. For terminal-only proof, run the offline `/analyze` smoke test from section 8 and the offline `/backtest` smoke test from section 9.
