from __future__ import annotations

import requests

from data.providers import get_provider
from data.providers.coingecko import CoinGeckoProvider
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


def test_cmc_provider_without_key_falls_back_to_coingecko(monkeypatch):
    class FakeCoinGeckoProvider:
        def get_candles(self, symbol: str, timeframe: str, limit: int):
            return [(symbol, timeframe, limit)]

    monkeypatch.setenv("CMC_API_KEY", "")
    monkeypatch.delenv("CMC_FALLBACK_PROVIDER", raising=False)
    monkeypatch.setattr("data.providers.cmc_agent_hub.CoinGeckoProvider", FakeCoinGeckoProvider)

    assert CoinMarketCapAgentHubProvider().get_candles("BTCUSDT", "1h", 80) == [("BTCUSDT", "1h", 80)]


def test_cmc_provider_can_still_explicitly_fallback_to_binance(monkeypatch):
    class FakeBinanceProvider:
        def get_candles(self, symbol: str, timeframe: str, limit: int):
            return [(symbol, timeframe, limit)]

    monkeypatch.setenv("CMC_API_KEY", "")
    monkeypatch.setenv("CMC_FALLBACK_PROVIDER", "binance")
    monkeypatch.setenv("CMC_ALLOW_BINANCE_FALLBACK", "true")
    monkeypatch.setattr("data.providers.cmc_agent_hub.BinanceProvider", FakeBinanceProvider)

    assert CoinMarketCapAgentHubProvider().get_candles("ETHUSDT", "4h", 90) == [("ETHUSDT", "4h", 90)]


def test_cmc_provider_binance_fallback_requires_opt_in(monkeypatch):
    class FakeCoinGeckoProvider:
        def get_candles(self, symbol: str, timeframe: str, limit: int):
            return [("coingecko", symbol, timeframe, limit)]

    class FakeBinanceProvider:
        def get_candles(self, symbol: str, timeframe: str, limit: int):
            return [("binance", symbol, timeframe, limit)]

    monkeypatch.setenv("CMC_API_KEY", "")
    monkeypatch.setenv("CMC_FALLBACK_PROVIDER", "binance")
    monkeypatch.setenv("CMC_ALLOW_BINANCE_FALLBACK", "false")
    monkeypatch.setattr("data.providers.cmc_agent_hub.CoinGeckoProvider", FakeCoinGeckoProvider)
    monkeypatch.setattr("data.providers.cmc_agent_hub.BinanceProvider", FakeBinanceProvider)

    assert CoinMarketCapAgentHubProvider().get_candles("BNBUSDT", "1d", 80) == [
        ("coingecko", "BNBUSDT", "1d", 80)
    ]


def test_cmc_provider_http_error_falls_back_to_coingecko(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            response = requests.Response()
            response.status_code = 403
            raise requests.HTTPError("403 Client Error", response=response)

    class FakeCoinGeckoProvider:
        def get_candles(self, symbol: str, timeframe: str, limit: int):
            return [(symbol, timeframe, limit)]

    monkeypatch.setenv("CMC_API_KEY", "invalid-or-plan-limited")
    monkeypatch.setenv("CMC_FALLBACK_PROVIDER", "coingecko")
    monkeypatch.setattr("data.providers.cmc_agent_hub.requests.get", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("data.providers.cmc_agent_hub.CoinGeckoProvider", FakeCoinGeckoProvider)

    assert CoinMarketCapAgentHubProvider().get_candles("BNBUSDT", "1d", 140) == [("BNBUSDT", "1d", 140)]


def test_coingecko_provider_aggregates_market_chart_prices(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "prices": [
                    [1_700_000_000_000, 100.0],
                    [1_700_000_900_000, 105.0],
                    [1_700_001_800_000, 98.0],
                    [1_700_003_600_000, 102.0],
                    [1_700_004_500_000, 107.0],
                ],
                "total_volumes": [
                    [1_700_000_000_000, 1000.0],
                    [1_700_003_600_000, 2000.0],
                ],
            }

    captured = {}

    def fake_get(url, headers, params, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("COINGECKO_API_KEY", "")
    monkeypatch.setattr("data.providers.coingecko.requests.get", fake_get)

    candles = CoinGeckoProvider().get_candles("BTCUSDT", "1h", 2)

    assert captured["url"].endswith("/coins/bitcoin/market_chart/range")
    assert captured["headers"] == {}
    assert captured["params"]["vs_currency"] == "usd"
    assert captured["params"]["interval"] == "hourly"
    assert len(candles) == 2
    assert candles[0].open == 100.0
    assert candles[0].high == 105.0
    assert candles[0].low == 98.0
    assert candles[0].close == 98.0
    assert candles[0].volume == 1000.0
    assert candles[1].open == 102.0
    assert candles[1].close == 107.0
