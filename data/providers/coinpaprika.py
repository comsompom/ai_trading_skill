from __future__ import annotations


class CoinPaprikaProvider:
    def get_candles(self, symbol: str, timeframe: str, limit: int = 300):
        raise ValueError("CoinPaprika OHLCV adapter is planned; use provider='binance' or pass market_data")

