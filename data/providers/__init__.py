from __future__ import annotations

from data.providers.binance import BinanceProvider
from data.providers.cmc_agent_hub import CoinMarketCapAgentHubProvider
from data.providers.coinpaprika import CoinPaprikaProvider
from data.providers.coingecko import CoinGeckoProvider
from data.providers.defillama import DefiLlamaProvider


def get_provider(name: str):
    providers = {
        "cmc": CoinMarketCapAgentHubProvider,
        "coinmarketcap": CoinMarketCapAgentHubProvider,
        "cmc_agent_hub": CoinMarketCapAgentHubProvider,
        "binance": BinanceProvider,
        "coinpaprika": CoinPaprikaProvider,
        "coingecko": CoinGeckoProvider,
        "defillama": DefiLlamaProvider,
    }
    try:
        return providers[name.lower()]()
    except KeyError as exc:
        raise ValueError(f"unsupported provider: {name}") from exc
