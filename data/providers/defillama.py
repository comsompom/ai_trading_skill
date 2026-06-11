from __future__ import annotations


class DefiLlamaProvider:
    def get_candles(self, symbol: str, timeframe: str, limit: int = 300):
        raise ValueError("DefiLlama provides context, not primary OHLCV candles in this first version")

