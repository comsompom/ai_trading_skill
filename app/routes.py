from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from agent.skill_runner import analyze_payload
from backtest.engine import run_backtest
from bots.discord_bot import send_discord
from bots.telegram_bot import send_telegram
from data.providers import get_provider
from skill.signal_schema import AnalyzeRequest
from skill.spec import skill_spec
from skill.strategy_skill import strategy_spec

api = Blueprint("api", __name__)


@api.get("/")
def index():
    return render_template("index.html")


@api.get("/favicon.ico")
def favicon():
    return ("", 204)


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ai_trading_skill"})


@api.get("/strategy/spec")
def spec():
    return jsonify(strategy_spec())


@api.get("/skill/spec")
def skill_spec_route():
    return jsonify(skill_spec())


@api.post("/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    try:
        result = analyze_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@api.post("/market-data")
def market_data():
    payload = request.get_json(silent=True) or {}
    try:
        analyze_request = AnalyzeRequest.from_payload(payload)
        candles = analyze_request.market_data
        if not candles:
            provider = get_provider(analyze_request.provider)
            candles = provider.get_candles(
                symbol=analyze_request.symbol,
                timeframe=analyze_request.timeframe,
                limit=analyze_request.lookback,
            )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(
        {
            "symbol": analyze_request.symbol,
            "timeframe": analyze_request.timeframe,
            "provider": analyze_request.provider,
            "candles": [candle.to_dict() for candle in candles],
        }
    )


@api.post("/backtest")
def backtest():
    payload = request.get_json(silent=True) or {}
    try:
        result = run_backtest(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@api.post("/notify/test")
def notify_test():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "AI Trading Skill notification test")
    channels = payload.get("channels", ["telegram", "discord"])
    results = {}
    if "telegram" in channels:
        results["telegram"] = send_telegram(message)
    if "discord" in channels:
        results["discord"] = send_discord(message)
    return jsonify({"message": message, "results": results})
