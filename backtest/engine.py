from __future__ import annotations

from data.providers import get_provider
from skill.signal_schema import AnalyzeRequest, Candle
from skill.strategy_skill import StrategySkill


def run_backtest(payload: dict) -> dict:
    request = AnalyzeRequest.from_payload(payload)
    candles = request.market_data
    if not candles:
        candles = _fetch_candles(request)
    if len(candles) < 80:
        raise ValueError("backtest requires at least 80 candles")
    skill = StrategySkill()
    trades = []
    signal_history = []
    position = None
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for i in range(60, len(candles) - 1):
        window = candles[: i + 1]
        result = skill.analyze(request.symbol, request.timeframe, window, request.risk_profile).to_dict()
        result["timestamp"] = candles[i].timestamp
        signal_history.append(
            {
                "timestamp": candles[i].timestamp,
                "decision": result["decision"],
                "confidence": result["confidence"],
                "probability_of_success": result["probability_of_success"],
                "score_breakdown": result["score_breakdown"],
            }
        )
        next_close = candles[i + 1].close
        if position is not None:
            direction = position["direction"]
            entry = position["entry"]
            pnl = (next_close - entry) / entry if direction == "BUY" else (entry - next_close) / entry
            if abs(pnl) >= 0.02 or result["decision"] not in (direction, "HOLD"):
                equity *= 1.0 + pnl
                peak = max(peak, equity)
                max_drawdown = max(max_drawdown, (peak - equity) / peak)
                trades.append({**position, "exit_timestamp": candles[i + 1].timestamp, "exit": next_close, "return": pnl})
                position = None
        if position is None and result["decision"] in ("BUY", "SELL"):
            position = {
                "direction": result["decision"],
                "entry_timestamp": candles[i + 1].timestamp,
                "entry": next_close,
                "feature_snapshot": result["indicator_values"],
                "score_breakdown": result["score_breakdown"],
                "probability_at_entry": result["probability_of_success"],
            }
    returns = [trade["return"] for trade in trades]
    wins = [value for value in returns if value > 0]
    return {
        "symbol": request.symbol,
        "timeframe": request.timeframe,
        "total_return": round(equity - 1.0, 6),
        "win_rate": round(len(wins) / len(trades), 6) if trades else 0.0,
        "max_drawdown": round(max_drawdown, 6),
        "number_of_trades": len(trades),
        "average_trade_return": round(sum(returns) / len(returns), 6) if returns else 0.0,
        "trades": trades,
        "signal_history": signal_history,
        "probability_calibration": {"model": "heuristic", "sample_size": 0},
        "assumptions": [
            "Signals are evaluated on closed candles.",
            "Entries/exits execute at next candle close for deterministic demo backtesting.",
            "This is not a live trading agent and does not account for fees/slippage yet.",
        ],
        "input_data_range": {
            "start": candles[0].timestamp,
            "end": candles[-1].timestamp,
            "candles": len(candles),
        },
    }


def _fetch_candles(request: AnalyzeRequest) -> list[Candle]:
    provider = get_provider(request.provider)
    return provider.get_candles(request.symbol, request.timeframe, request.lookback)
