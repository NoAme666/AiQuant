# AI Quant Company - 加密货币数据提供者
"""
Crypto Market Data Provider

支持的数据源:
- Binance API (主要)
- CoinGecko API (备用)

数据类型:
- OHLCV K线数据
- 永续合约资金费率
"""

import asyncio
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
import pandas as pd
import structlog

from data.providers.base import (
    AssetType,
    DataFrequency,
    DataResponse,
    MarketDataProvider,
)

logger = structlog.get_logger()


# ============================================
# Binance 数据提供者
# ============================================

class BinanceDataProvider(MarketDataProvider):
    """Binance 数据提供者
    
    使用 Binance 公开 API 获取加密货币数据。
    """
    
    BASE_URL = "https://api.binance.com"
    FUTURES_URL = "https://fapi.binance.com"
    
    # 频率映射
    FREQ_MAP = {
        DataFrequency.MINUTE_1: "1m",
        DataFrequency.MINUTE_5: "5m",
        DataFrequency.MINUTE_15: "15m",
        DataFrequency.MINUTE_30: "30m",
        DataFrequency.HOUR_1: "1h",
        DataFrequency.HOUR_4: "4h",
        DataFrequency.DAY_1: "1d",
        DataFrequency.WEEK_1: "1w",
    }
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """初始化 Binance 数据提供者
        
        Args:
            api_key: Binance API Key (可选，公开数据不需要)
            secret_key: Binance Secret Key (可选)
        """
        super().__init__(name="binance")
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.secret_key = secret_key or os.getenv("BINANCE_SECRET_KEY")
        
        # HTTP 客户端
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["X-MBX-APIKEY"] = self.api_key
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers=headers,
            )
        return self._client
    
    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def supported_frequencies(self) -> list[DataFrequency]:
        return list(self.FREQ_MAP.keys())
    
    @property
    def supported_asset_types(self) -> list[AssetType]:
        return [AssetType.CRYPTO_SPOT, AssetType.CRYPTO_PERP]
    
    async def get_symbols(self) -> list[str]:
        """获取可用交易对列表"""
        client = await self._get_client()
        
        try:
            response = await client.get(f"{self.BASE_URL}/api/v3/exchangeInfo")
            response.raise_for_status()
            data = response.json()
            
            symbols = [
                s["symbol"]
                for s in data["symbols"]
                if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
            ]
            
            logger.info("获取 Binance 交易对", count=len(symbols))
            return symbols
            
        except Exception as e:
            logger.error("获取交易对失败", error=str(e))
            return []
    
    async def get_ohlcv(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        frequency: DataFrequency = DataFrequency.DAY_1,
    ) -> DataResponse:
        """获取 OHLCV K线数据
        
        Args:
            symbols: 交易对列表 (如 ["BTCUSDT", "ETHUSDT"])
            start: 开始时间
            end: 结束时间
            frequency: 数据频率
            
        Returns:
            DataResponse 包含合并的 OHLCV 数据
        """
        client = await self._get_client()
        interval = self.FREQ_MAP[frequency]
        
        all_data = []
        missing_symbols = []
        
        for symbol in symbols:
            try:
                data = await self._fetch_klines(client, symbol, start, end, interval)
                if data is not None and not data.empty:
                    data["symbol"] = symbol
                    all_data.append(data)
                else:
                    missing_symbols.append(symbol)
            except Exception as e:
                logger.error("获取K线失败", symbol=symbol, error=str(e))
                missing_symbols.append(symbol)
        
        # 合并数据
        if all_data:
            df = pd.concat(all_data, ignore_index=True)
        else:
            df = pd.DataFrame()
        
        return DataResponse(
            data=df,
            symbols=symbols,
            start=start,
            end=end,
            frequency=frequency,
            provider=self.name,
            row_count=len(df),
            missing_count=len(missing_symbols),
            missing_symbols=missing_symbols,
        )
    
    async def _fetch_klines(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str,
        limit: int = 1000,
    ) -> Optional[pd.DataFrame]:
        """获取单个交易对的K线数据"""
        url = f"{self.BASE_URL}/api/v3/klines"
        
        all_klines = []
        current_start = int(start.timestamp() * 1000)
        end_ts = int(end.timestamp() * 1000)
        
        while current_start < end_ts:
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": end_ts,
                "limit": limit,
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            klines = response.json()
            
            if not klines:
                break
            
            all_klines.extend(klines)
            current_start = klines[-1][0] + 1  # 下一根K线的开始时间
            
            # 避免频率限制
            await asyncio.sleep(0.1)
        
        if not all_klines:
            return None
        
        # 转换为 DataFrame
        df = pd.DataFrame(all_klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore",
        ])
        
        # 类型转换
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open", "high", "low", "close", "volume", "quote_volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["trades"] = pd.to_numeric(df["trades"], errors="coerce").astype("Int64")
        
        # 只保留需要的列
        df = df[["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades"]]
        
        return df
    
    async def get_funding_rates(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """获取永续合约资金费率
        
        Args:
            symbols: 交易对列表
            start: 开始时间
            end: 结束时间
            
        Returns:
            资金费率 DataFrame
        """
        client = await self._get_client()
        url = f"{self.FUTURES_URL}/fapi/v1/fundingRate"
        
        all_data = []
        
        for symbol in symbols:
            try:
                params = {
                    "symbol": symbol,
                    "startTime": int(start.timestamp() * 1000),
                    "endTime": int(end.timestamp() * 1000),
                    "limit": 1000,
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data:
                    df = pd.DataFrame(data)
                    df["symbol"] = symbol
                    all_data.append(df)
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning("获取资金费率失败", symbol=symbol, error=str(e))
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.concat(all_data, ignore_index=True)
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms")
        df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
        
        return df


# ============================================
# CoinGecko 数据提供者（备用）
# ============================================

class CoinGeckoDataProvider(MarketDataProvider):
    """CoinGecko 数据提供者
    
    作为 Binance 的备用数据源，主要用于获取历史价格。
    免费 API 有请求限制。
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        super().__init__(name="coingecko")
        self._client: Optional[httpx.AsyncClient] = None
        
        # 常用代币 ID 映射
        self._symbol_to_id = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binancecoin",
            "SOLUSDT": "solana",
            "ADAUSDT": "cardano",
            "XRPUSDT": "ripple",
            "DOTUSDT": "polkadot",
            "DOGEUSDT": "dogecoin",
            "MATICUSDT": "matic-network",
            "LINKUSDT": "chainlink",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def supported_frequencies(self) -> list[DataFrequency]:
        return [DataFrequency.DAY_1]  # CoinGecko 免费 API 只支持日频
    
    @property
    def supported_asset_types(self) -> list[AssetType]:
        return [AssetType.CRYPTO_SPOT]
    
    async def get_symbols(self) -> list[str]:
        """获取支持的交易对"""
        return list(self._symbol_to_id.keys())
    
    async def get_ohlcv(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        frequency: DataFrequency = DataFrequency.DAY_1,
    ) -> DataResponse:
        """获取 OHLCV 数据"""
        client = await self._get_client()
        
        all_data = []
        missing_symbols = []
        
        for symbol in symbols:
            coin_id = self._symbol_to_id.get(symbol)
            if not coin_id:
                missing_symbols.append(symbol)
                continue
            
            try:
                data = await self._fetch_market_chart(client, coin_id, start, end)
                if data is not None and not data.empty:
                    data["symbol"] = symbol
                    all_data.append(data)
                else:
                    missing_symbols.append(symbol)
            except Exception as e:
                logger.error("获取 CoinGecko 数据失败", symbol=symbol, error=str(e))
                missing_symbols.append(symbol)
            
            # CoinGecko 免费 API 限制：10-30 requests/minute
            await asyncio.sleep(2.0)
        
        if all_data:
            df = pd.concat(all_data, ignore_index=True)
        else:
            df = pd.DataFrame()
        
        return DataResponse(
            data=df,
            symbols=symbols,
            start=start,
            end=end,
            frequency=frequency,
            provider=self.name,
            row_count=len(df),
            missing_count=len(missing_symbols),
            missing_symbols=missing_symbols,
        )
    
    async def _fetch_market_chart(
        self,
        client: httpx.AsyncClient,
        coin_id: str,
        start: datetime,
        end: datetime,
    ) -> Optional[pd.DataFrame]:
        """获取市场图表数据"""
        url = f"{self.BASE_URL}/coins/{coin_id}/market_chart/range"
        
        params = {
            "vs_currency": "usd",
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
        }
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("prices"):
            return None
        
        # 转换为 DataFrame
        df = pd.DataFrame(data["prices"], columns=["timestamp", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        
        # CoinGecko 不提供 OHLV，只有价格，我们用 close 填充
        df["open"] = df["close"]
        df["high"] = df["close"]
        df["low"] = df["close"]
        
        if data.get("total_volumes"):
            vol_df = pd.DataFrame(data["total_volumes"], columns=["ts", "volume"])
            df["volume"] = vol_df["volume"].values[:len(df)]
        else:
            df["volume"] = 0.0
        
        return df[["timestamp", "open", "high", "low", "close", "volume"]]


# ============================================
# 数据版本化
# ============================================

def compute_data_hash(df: pd.DataFrame) -> str:
    """计算数据哈希
    
    Args:
        df: 数据 DataFrame
        
    Returns:
        SHA256 哈希值
    """
    # 排序以确保一致性
    if "timestamp" in df.columns:
        df = df.sort_values(["timestamp", "symbol"] if "symbol" in df.columns else "timestamp")
    
    # 计算哈希
    data_str = df.to_csv(index=False)
    return hashlib.sha256(data_str.encode()).hexdigest()[:16]


# ============================================
# 工厂函数
# ============================================

def create_crypto_provider(
    provider: str = "binance",
    **kwargs,
) -> MarketDataProvider:
    """创建加密货币数据提供者
    
    Args:
        provider: 提供者名称 ("binance" 或 "coingecko")
        **kwargs: 提供者特定参数
        
    Returns:
        数据提供者实例
    """
    providers = {
        "binance": BinanceDataProvider,
        "coingecko": CoinGeckoDataProvider,
    }
    
    if provider not in providers:
        raise ValueError(f"不支持的提供者: {provider}")
    
    return providers[provider](**kwargs)
