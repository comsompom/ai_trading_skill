from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from app.env import load_env_file
from data.cache import cache
from skill.signal_schema import Candle


class CoinGeckoProvider:
    default_base_url = "https://api.coingecko.com/api/v3"

    def get_candles(self, symbol: str, timeframe: str, limit: int = 300) -> list[Candle]:
        load_env_file()
        coin_id = _coingecko_coin_id(symbol)
        quote = _quote_currency(symbol)
        key = f"coingecko:{coin_id}:{quote}:{symbol}:{timeframe}:{limit}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        interval_seconds = _timeframe_seconds(timeframe)
        now = int(datetime.now(timezone.utc).timestamp())
        base_url = os.getenv("COINGECKO_BASE_URL", self.default_base_url).rstrip("/")
        if timeframe == "1d":
            candles = self._get_daily_candles(
                base_url=base_url,
                coin_id=coin_id,
                quote=quote,
                symbol=symbol,
                limit=limit,
            )
            cache.set(key, candles, ttl_seconds=120)
            return candles

        start = now - (interval_seconds * (limit + 4))
        params = {
            "vs_currency": quote,
            "from": _iso_minute(start),
            "to": _iso_minute(now),
            "precision": "full",
        }
        response = requests.get(
            f"{base_url}/coins/{coin_id}/market_chart/range",
            headers=_headers(base_url),
            params=params,
            timeout=20,
        )
        if response.status_code == 400:
            params.pop("precision", None)
            response = requests.get(
                f"{base_url}/coins/{coin_id}/market_chart/range",
                headers=_headers(base_url),
                params=params,
                timeout=20,
            )
        response.raise_for_status()
        candles = _prices_to_candles(
            response.json(),
            symbol=symbol.upper(),
            timeframe=timeframe,
            interval_seconds=interval_seconds,
            limit=limit,
        )
        cache.set(key, candles, ttl_seconds=120)
        return candles

    def _get_daily_candles(self, *, base_url: str, coin_id: str, quote: str, symbol: str, limit: int) -> list[Candle]:
        now = int(datetime.now(timezone.utc).timestamp())
        days = min(max(limit + 4, 2), 90)
        start = now - (days * 86400)
        params = {
            "vs_currency": quote,
            "from": _iso_minute(start),
            "to": _iso_minute(now),
            "interval": "hourly",
            "precision": "full",
        }
        response = requests.get(
            f"{base_url}/coins/{coin_id}/market_chart/range",
            headers=_headers(base_url),
            params=params,
            timeout=20,
        )
        if response.status_code == 400:
            params.pop("precision", None)
            response = requests.get(
                f"{base_url}/coins/{coin_id}/market_chart/range",
                headers=_headers(base_url),
                params=params,
                timeout=20,
            )
        response.raise_for_status()
        return _prices_to_candles(
            response.json(),
            symbol=symbol.upper(),
            timeframe="1d",
            interval_seconds=86400,
            limit=limit,
        )


def _headers(base_url: str) -> dict[str, str]:
    api_key = os.getenv("COINGECKO_API_KEY", "").strip()
    if not api_key:
        return {}
    if "pro-api.coingecko.com" in base_url:
        return {"x-cg-pro-api-key": api_key}
    return {"x-cg-demo-api-key": api_key}


def _prices_to_candles(
    payload: dict[str, Any],
    *,
    symbol: str,
    timeframe: str,
    interval_seconds: int,
    limit: int,
) -> list[Candle]:
    prices = sorted(payload.get("prices", []), key=lambda row: row[0])
    volumes = {
        int(row[0]) // 1000 // interval_seconds * interval_seconds: float(row[1])
        for row in payload.get("total_volumes", [])
        if len(row) >= 2
    }
    buckets: dict[int, list[float]] = {}
    for row in prices:
        if len(row) < 2:
            continue
        timestamp = int(row[0]) // 1000
        bucket = timestamp // interval_seconds * interval_seconds
        buckets.setdefault(bucket, []).append(float(row[1]))

    candles = [
        Candle(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            open=values[0],
            high=max(values),
            low=min(values),
            close=values[-1],
            volume=volumes.get(timestamp, 0.0),
        )
        for timestamp, values in sorted(buckets.items())
        if values
    ]
    candles = candles[-limit:]
    if len(candles) < min(limit, 60):
        raise ValueError("CoinGecko returned too few candles for this timeframe/lookback")
    return candles


def _iso_minute(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M")



def _coingecko_coin_id(symbol: str) -> str:
    base = _base_symbol(symbol)
    ids = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "AVAX": "avalanche-2",
        "DOT": "polkadot",
        "MATIC": "matic-network",
        "POL": "polygon-ecosystem-token",
        "LINK": "chainlink",
        "LTC": "litecoin",
        "BCH": "bitcoin-cash",
        "TRX": "tron",
        "UNI": "uniswap",
        "ATOM": "cosmos",
        "NEAR": "near",
        "APT": "aptos",
        "ARB": "arbitrum",
        "OP": "optimism",
    }
    try:
        return ids[base]
    except KeyError as exc:
        raise ValueError(f"unsupported CoinGecko symbol: {symbol}") from exc


def _base_symbol(symbol: str) -> str:
    normalized = symbol.upper().replace("-", "").replace("/", "")
    for quote in ("USDT", "USDC", "BUSD", "USD", "BTC", "ETH"):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)]
    return normalized


def _quote_currency(symbol: str) -> str:
    normalized = symbol.upper().replace("-", "").replace("/", "")
    if normalized.endswith("BTC"):
        return "btc"
    if normalized.endswith("ETH"):
        return "eth"
    return "usd"


def _timeframe_seconds(timeframe: str) -> int:
    unit = timeframe[-1]
    amount = int(timeframe[:-1] or "1")
    if unit == "m":
        return amount * 60
    if unit == "h":
        return amount * 3600
    if unit == "d":
        return amount * 86400
    raise ValueError(f"unsupported timeframe for CoinGecko provider: {timeframe}")
