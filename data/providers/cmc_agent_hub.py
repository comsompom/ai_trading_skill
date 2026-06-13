from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from app.env import load_env_file
from data.cache import cache
from data.providers.binance import BinanceProvider
from data.providers.coingecko import CoinGeckoProvider
from skill.signal_schema import Candle


class CoinMarketCapAgentHubProvider:
    default_base_url = "https://pro-api.coinmarketcap.com"

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> list[Candle]:
        load_env_file()
        key = f"cmc:{symbol}:{timeframe}:{limit}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        api_key = os.getenv("CMC_API_KEY", "").strip()
        if not api_key:
            return self._fallback_candles(symbol=symbol, timeframe=timeframe, limit=limit)

        base_url = os.getenv("CMC_BASE_URL", self.default_base_url).rstrip("/")
        interval_seconds = _timeframe_seconds(timeframe)
        time_end = datetime.now(timezone.utc)
        time_start = time_end - timedelta(seconds=interval_seconds * min(limit, 1000))
        response = requests.get(
            f"{base_url}/v2/cryptocurrency/ohlcv/historical",
            headers={"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"},
            params={
                "symbol": _cmc_symbol(symbol),
                "convert": os.getenv("CMC_CONVERT", "USD"),
                "interval": timeframe,
                "time_start": time_start.isoformat().replace("+00:00", "Z"),
                "time_end": time_end.isoformat().replace("+00:00", "Z"),
                "count": min(limit, 1000),
            },
            timeout=20,
        )
        response.raise_for_status()
        candles = self._parse_ohlcv_response(response.json(), symbol=symbol.upper(), timeframe=timeframe, limit=limit)
        cache.set(key, candles, ttl_seconds=60)
        return candles

    def _fallback_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        fallback = os.getenv("CMC_FALLBACK_PROVIDER", "coingecko").strip().lower()
        if fallback == "coingecko":
            return CoinGeckoProvider().get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
        if fallback == "binance":
            return BinanceProvider().get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
        if fallback in {"", "none", "disabled"}:
            raise ValueError("CMC_API_KEY is required for provider='cmc'")
        raise ValueError(f"unsupported CMC_FALLBACK_PROVIDER: {fallback}")

    def _parse_ohlcv_response(self, payload: dict[str, Any], symbol: str, timeframe: str, limit: int) -> list[Candle]:
        quotes = _extract_quotes(payload)
        convert = os.getenv("CMC_CONVERT", "USD")
        candles = []
        for row in quotes:
            quote = row.get("quote", {})
            values = quote.get(convert) or quote.get(convert.upper()) or next(iter(quote.values()), {})
            if not values:
                continue
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=_parse_timestamp(
                        row.get("time_close")
                        or row.get("time_open")
                        or values.get("timestamp")
                        or row.get("timestamp")
                    ),
                    open=float(values["open"]),
                    high=float(values["high"]),
                    low=float(values["low"]),
                    close=float(values["close"]),
                    volume=float(values.get("volume", 0.0)),
                )
            )
        candles.sort(key=lambda candle: candle.timestamp)
        candles = candles[-limit:]
        if not candles:
            raise ValueError("CoinMarketCap returned no OHLCV candles")
        return candles


def _extract_quotes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", {})
    if isinstance(data, dict) and isinstance(data.get("quotes"), list):
        return data["quotes"]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                first = value[0]
                if isinstance(first.get("quotes"), list):
                    return first["quotes"]
            if isinstance(value, dict) and isinstance(value.get("quotes"), list):
                return value["quotes"]
    if isinstance(data, list) and data and isinstance(data[0], dict) and isinstance(data[0].get("quotes"), list):
        return data[0]["quotes"]
    return []


def _cmc_symbol(symbol: str) -> str:
    normalized = symbol.upper().replace("-", "").replace("/", "")
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)]
    return normalized


def _parse_timestamp(value: Any) -> int:
    if isinstance(value, int | float):
        return int(value)
    if not value:
        raise ValueError("missing CoinMarketCap candle timestamp")
    return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())


def _timeframe_seconds(timeframe: str) -> int:
    unit = timeframe[-1]
    amount = int(timeframe[:-1] or "1")
    if unit == "m":
        return amount * 60
    if unit == "h":
        return amount * 3600
    if unit == "d":
        return amount * 86400
    raise ValueError(f"unsupported timeframe for CoinMarketCap provider: {timeframe}")
