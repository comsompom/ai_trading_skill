from __future__ import annotations

import os

import requests

from app.env import load_env_file
from data.cache import cache
from skill.signal_schema import Candle


class BinanceProvider:
    default_base_url = "https://api.binance.com"

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> list[Candle]:
        load_env_file()
        key = f"binance:{symbol}:{timeframe}:{limit}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        base_url = os.getenv("BINANCE_BASE_URL", self.default_base_url).rstrip("/")
        response = requests.get(
            f"{base_url}/api/v3/klines",
            params={"symbol": symbol.upper(), "interval": timeframe, "limit": min(limit, 1000)},
            timeout=15,
        )
        response.raise_for_status()
        candles = [
            Candle(
                symbol=symbol.upper(),
                timeframe=timeframe,
                timestamp=int(row[0]) // 1000,
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in response.json()
        ]
        cache.set(key, candles, ttl_seconds=30)
        return candles
