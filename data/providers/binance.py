from __future__ import annotations

import requests

from data.cache import cache
from skill.signal_schema import Candle


class BinanceProvider:
    base_url = "https://api.binance.com/api/v3/klines"

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> list[Candle]:
        key = f"binance:{symbol}:{timeframe}:{limit}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        response = requests.get(
            self.base_url,
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

