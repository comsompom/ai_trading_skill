from __future__ import annotations

from flask import Blueprint, jsonify, request

from agent.skill_runner import analyze_payload
from backtest.engine import run_backtest
from bots.discord_bot import send_discord
from bots.telegram_bot import send_telegram
from skill.strategy_skill import strategy_spec

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ai_trading_skill"})


@api.get("/strategy/spec")
def spec():
    return jsonify(strategy_spec())


@api.post("/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    try:
        result = analyze_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


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

