from __future__ import annotations

import requests
from flask import Blueprint, jsonify, render_template, request

from agent.skill_runner import analyze_payload
from backtest.engine import run_backtest
from bots.discord_bot import send_discord
from bots.telegram_bot import send_telegram
from data.cache import cache
from data.providers import get_provider
from skill.signal_schema import AnalyzeRequest
from skill.spec import skill_spec
from skill.strategy_skill import strategy_spec

api = Blueprint("api", __name__)


def _format_analysis_telegram_message(result: dict) -> str:
    risk = result.get("risk_assumptions") or {}
    scores = result.get("score_breakdown") or {}
    lines = [
        "AI Trading Skill Analysis",
        f"{result.get('symbol', '-')}/{result.get('timeframe', '-')}: {result.get('decision', '-')}",
        f"Confidence: {_format_percent(result.get('confidence'))}",
        f"Probability: {_format_percent(result.get('probability_of_success'))} ({result.get('probability_model', '-')})",
        f"Buy/Sell score: {_format_percent(scores.get('buy_score'))} / {_format_percent(scores.get('sell_score'))}",
        f"Risk: {risk.get('risk_profile', '-')} profile, {risk.get('reward_to_risk', '-')}R reward/risk",
        f"Long stop/target: {risk.get('long_stop', '-')} / {risk.get('long_target', '-')}",
        f"Short stop/target: {risk.get('short_stop', '-')} / {risk.get('short_target', '-')}",
        f"Reason: {result.get('explanation', '-')}",
    ]
    return "\n".join(lines)


def _format_percent(value) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "-"


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
    except requests.RequestException as exc:
        return jsonify({"error": f"market data provider error: {exc}"}), 502
    if payload.get("notify_telegram"):
        try:
            result["notifications"] = {
                "telegram": send_telegram(_format_analysis_telegram_message(result)),
            }
        except requests.RequestException as exc:
            result["notifications"] = {
                "telegram": {"sent": False, "reason": f"Telegram request failed: {exc}"},
            }
    return jsonify(result)


@api.post("/market-data")
def market_data():
    payload = request.get_json(silent=True) or {}
    try:
        analyze_request = AnalyzeRequest.from_payload(payload)
        candles = analyze_request.market_data
        if not candles:
            if payload.get("refresh"):
                cache.delete_prefix(
                    f"{analyze_request.provider}:{analyze_request.symbol}:{analyze_request.timeframe}:{analyze_request.lookback}"
                )
                if analyze_request.provider in {"cmc", "coinmarketcap", "cmc_agent_hub"}:
                    cache.delete_prefix(f"coingecko:")
                    cache.delete_prefix(f"binance:{analyze_request.symbol}:{analyze_request.timeframe}:{analyze_request.lookback}")
            provider = get_provider(analyze_request.provider)
            candles = provider.get_candles(
                symbol=analyze_request.symbol,
                timeframe=analyze_request.timeframe,
                limit=analyze_request.lookback,
            )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except requests.RequestException as exc:
        return jsonify({"error": f"market data provider error: {exc}"}), 502
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
    except requests.RequestException as exc:
        return jsonify({"error": f"market data provider error: {exc}"}), 502
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
