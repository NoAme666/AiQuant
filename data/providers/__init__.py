# AI Quant Company - 数据源适配器
"""
Market Data Providers

支持的数据源:
- crypto: Binance, CoinGecko
- (未来) stocks: Yahoo Finance, Alpha Vantage
"""

from data.providers.base import MarketDataProvider

__all__ = ["MarketDataProvider"]
