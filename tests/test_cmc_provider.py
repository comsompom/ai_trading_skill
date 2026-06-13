from __future__ import annotations

from data.providers import get_provider
from data.providers.cmc_agent_hub import CoinMarketCapAgentHubProvider


def test_provider_registry_resolves_cmc_aliases():
    assert isinstance(get_provider("cmc"), CoinMarketCapAgentHubProvider)
    assert isinstance(get_provider("coinmarketcap"), CoinMarketCapAgentHubProvider)
    assert isinstance(get_provider("cmc_agent_hub"), CoinMarketCapAgentHubProvider)


def test_cmc_provider_parses_ohlcv_response(monkeypatch):
    monkeypatch.setenv("CMC_CONVERT", "USD")
    payload = {
        "data": {
            "id": 1,
            "name": "Bitcoin",
            "symbol": "BTC",
            "quotes": [
                {
                    "time_open": "2026-06-13T09:00:00.000Z",
                    "time_close": "2026-06-13T10:00:00.000Z",
                    "quote": {
                        "USD": {
                            "open": 100.0,
                            "high": 105.0,
                            "low": 99.0,
                            "close": 103.0,
                            "volume": 12345.0,
                        }
                    },
                }
            ],
        }
    }

    candles = CoinMarketCapAgentHubProvider()._parse_ohlcv_response(
        payload,
        symbol="BTCUSDT",
        timeframe="1h",
        limit=300,
    )

    assert len(candles) == 1
    assert candles[0].symbol == "BTCUSDT"
    assert candles[0].timeframe == "1h"
    assert candles[0].open == 100.0
    assert candles[0].high == 105.0
    assert candles[0].low == 99.0
    assert candles[0].close == 103.0
    assert candles[0].volume == 12345.0


def test_cmc_provider_without_key_falls_back_to_binance(monkeypatch):
    class FakeBinanceProvider:
        def get_candles(self, symbol: str, timeframe: str, limit: int):
            return [(symbol, timeframe, limit)]

    monkeypatch.delenv("CMC_API_KEY", raising=False)
    monkeypatch.setenv("CMC_FALLBACK_PROVIDER", "binance")
    monkeypatch.setattr("data.providers.cmc_agent_hub.BinanceProvider", FakeBinanceProvider)

    assert CoinMarketCapAgentHubProvider().get_candles("BTCUSDT", "1h", 80) == [("BTCUSDT", "1h", 80)]

