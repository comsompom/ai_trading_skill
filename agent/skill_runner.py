from __future__ import annotations

from app.env import load_env_file
from data.providers import get_provider
from skill.signal_schema import AnalyzeRequest
from skill.strategy_skill import StrategySkill


def analyze_payload(payload: dict) -> dict:
    load_env_file()
    request = AnalyzeRequest.from_payload(payload)
    candles = request.market_data
    if not candles:
        provider = get_provider(request.provider)
        candles = provider.get_candles(
            symbol=request.symbol,
            timeframe=request.timeframe,
            limit=request.lookback,
        )
    return StrategySkill().analyze(
        symbol=request.symbol,
        timeframe=request.timeframe,
        candles=candles,
        risk_profile=request.risk_profile,
    ).to_dict()
