# How to Install and Run This Project

This project is a Python Flask API for a deterministic crypto strategy skill. It is not a live trading bot and does not place trades.

## 1. Prerequisites

Install Python 3.11 or newer.

Check your Python version:

```bash
python3 --version
```

If `python3` is not available, try:

```bash
python --version
```

## 2. Open the Project Folder

From a terminal, go to the project root:

```bash
cd /Users/olegbourdo/Development/ai_trading_skill
```

## 3. Create a Virtual Environment

Create a local virtual environment:

```bash
python3 -m venv .venv
```

If your system uses `python` instead of `python3`, run:

```bash
python -m venv .venv
```

## 4. Activate the Virtual Environment

On macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, your terminal prompt should usually show `(.venv)`.

The remaining commands assume the virtual environment is active. If you skip activation, replace `python` with `python3`.

## 5. Upgrade Pip

```bash
python -m pip install --upgrade pip
```

## 6. Install the Project

Install the project with development dependencies:

```bash
pip install -e ".[dev]"
```

This installs the Flask API, request dependencies, and `pytest`.

## 7. Run the Tests

Run the test suite:

```bash
python -m pytest
```

The tests should pass before you run or modify the API.

## 8. Start the API Server

Run:

```bash
python -m app.flask_app
```

The server starts on:

```text
http://localhost:5000
```

Keep this terminal window open while using the API.

## 9. Check That the API Is Running

Open a second terminal window and run:

```bash
curl http://localhost:5000/health
```

Expected response:

```json
{
  "service": "ai_trading_skill",
  "status": "ok"
}
```

Check the strategy specification:

```bash
curl http://localhost:5000/strategy/spec
```

Check the Skill specification used by FastMCP and agent discovery:

```bash
curl http://localhost:5000/skill/spec
```

## 10. Analyze a Symbol

Use Binance public OHLCV data:

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"1h","lookback":300,"provider":"binance","risk_profile":"balanced","market_data":[]}'
```

Notes:

- `lookback` must be at least `60`.
- If `market_data` is empty, the app fetches public candle data from Binance.
- Binance access requires an internet connection and may depend on regional availability.

## 11. Run a Backtest

Run:

```bash
curl -X POST http://localhost:5000/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","timeframe":"1h","lookback":300,"provider":"binance","risk_profile":"balanced","market_data":[]}'
```

Notes:

- Backtests require at least `80` candles.
- The backtest is deterministic.
- Entries and exits are simulated at the next candle close.
- Fees and slippage are not included yet.

## 12. Optional Notification Setup

Notifications are optional. The API can test Telegram and Discord notification delivery if environment variables are configured before starting the server.

Telegram:

```bash
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export TELEGRAM_CHAT_ID="your-telegram-chat-id"
```

Discord:

```bash
export DISCORD_WEBHOOK_URL="your-discord-webhook-url"
```

Then restart the API server:

```bash
python -m app.flask_app
```

Test notifications:

```bash
curl -X POST http://localhost:5000/notify/test \
  -H "Content-Type: application/json" \
  -d '{"message":"AI Trading Skill notification test","channels":["telegram","discord"]}'
```

If variables are not configured, the endpoint returns `sent: false` with the missing configuration reason.

## 13. Optional FastMCP Server

Install the optional MCP dependency:

```bash
pip install -e ".[mcp]"
```

Run the FastMCP server:

```bash
python3 -m agent.mcp_server
```

It exposes:

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

## 14. Stop the API Server

In the terminal running the server, press:

```text
Ctrl+C
```

## 15. Run Again Later

Each time you return to the project:

```bash
cd /Users/olegbourdo/Development/ai_trading_skill
source .venv/bin/activate
python -m app.flask_app
```
