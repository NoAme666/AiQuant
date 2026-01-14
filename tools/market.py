# AI Quant Company - Market Tools
"""
市场数据工具

提供:
- get_ohlcv: 获取 K 线数据
- get_quote: 获取当前报价
- get_tickers: 获取所有行情
- compute_indicators: 计算技术指标
- get_balance: 获取账户余额
- get_positions: 获取持仓
"""

import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# 确保环境变量加载
from dotenv import load_dotenv
load_dotenv()

import structlog

logger = structlog.get_logger()


class ExchangeManager:
    """交易所管理器 - 支持多交易所切换和带密钥的私有API调用"""
    
    _instances: dict = {}
    
    def __init__(self, exchange_id: str = None):
        """初始化交易所管理器
        
        Args:
            exchange_id: 交易所ID (binance, okx)，默认从环境变量读取
        """
        self.exchange_id = exchange_id or os.getenv("DEFAULT_EXCHANGE", "okx")
        self._public_exchange = None
        self._private_exchange = None
    
    @classmethod
    def get_instance(cls, exchange_id: str = None) -> "ExchangeManager":
        """获取单例实例"""
        exchange_id = exchange_id or os.getenv("DEFAULT_EXCHANGE", "okx")
        if exchange_id not in cls._instances:
            cls._instances[exchange_id] = cls(exchange_id)
        return cls._instances[exchange_id]
    
    def _get_exchange_config(self, exchange_id: str) -> dict:
        """获取交易所配置"""
        configs = {
            "binance": {
                "apiKey": os.getenv("BINANCE_API_KEY"),
                "secret": os.getenv("BINANCE_API_SECRET"),
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True,
                },
            },
            "okx": {
                "apiKey": os.getenv("OKX_API_KEY"),
                "secret": os.getenv("OKX_API_SECRET"),
                "password": os.getenv("OKX_PASSPHRASE"),
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                },
            },
        }
        return configs.get(exchange_id, {})
    
    def get_public_exchange(self):
        """获取公共 API 交易所实例（无需密钥）"""
        if self._public_exchange is None:
            try:
                import ccxt
                exchange_class = getattr(ccxt, self.exchange_id)
                self._public_exchange = exchange_class({
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"},
                })
                logger.info(f"公共交易所初始化成功", exchange=self.exchange_id)
            except ImportError:
                logger.warning("ccxt 未安装")
                return None
            except Exception as e:
                logger.error(f"公共交易所初始化失败: {e}")
                return None
        return self._public_exchange
    
    def get_private_exchange(self):
        """获取私有 API 交易所实例（带密钥）"""
        if self._private_exchange is None:
            try:
                import ccxt
                config = self._get_exchange_config(self.exchange_id)
                
                if not config.get("apiKey"):
                    logger.warning(f"{self.exchange_id} API 密钥未配置")
                    return None
                
                exchange_class = getattr(ccxt, self.exchange_id)
                self._private_exchange = exchange_class(config)
                logger.info(f"私有交易所初始化成功", exchange=self.exchange_id)
            except ImportError:
                logger.warning("ccxt 未安装")
                return None
            except Exception as e:
                logger.error(f"私有交易所初始化失败: {e}")
                return None
        return self._private_exchange
    
    async def fetch_balance(self) -> dict:
        """获取账户余额"""
        exchange = self.get_private_exchange()
        if not exchange:
            return {"error": "交易所未初始化或密钥未配置", "balances": []}
        
        try:
            balance = exchange.fetch_balance()
            
            # 整理余额数据
            assets = []
            total_usd = 0.0
            
            for asset, data in balance.get("total", {}).items():
                if data and float(data) > 0:
                    free = float(balance.get("free", {}).get(asset, 0) or 0)
                    used = float(balance.get("used", {}).get(asset, 0) or 0)
                    total = float(data)
                    
                    # 估算 USD 价值
                    usd_value = 0.0
                    if asset in ["USDT", "USDC", "BUSD", "USD"]:
                        usd_value = total
                    else:
                        try:
                            ticker = exchange.fetch_ticker(f"{asset}/USDT")
                            usd_value = total * (ticker.get("last") or 0)
                        except:
                            pass
                    
                    total_usd += usd_value
                    
                    assets.append({
                        "asset": asset,
                        "free": free,
                        "locked": used,
                        "total": total,
                        "usd_value": round(usd_value, 2),
                    })
            
            # 按 USD 价值排序
            assets.sort(key=lambda x: x["usd_value"], reverse=True)
            
            return {
                "exchange": self.exchange_id,
                "total_usd": round(total_usd, 2),
                "balances": assets,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return {"error": str(e), "balances": []}
    
    async def fetch_positions(self) -> dict:
        """获取持仓（期货/合约）"""
        exchange = self.get_private_exchange()
        if not exchange:
            return {"error": "交易所未初始化或密钥未配置", "positions": []}
        
        try:
            # 尝试获取持仓（仅合约账户有持仓概念）
            positions = []
            
            if hasattr(exchange, "fetch_positions"):
                raw_positions = exchange.fetch_positions()
                for pos in raw_positions:
                    if pos.get("contracts") and float(pos["contracts"]) != 0:
                        positions.append({
                            "symbol": pos.get("symbol"),
                            "side": pos.get("side"),
                            "contracts": float(pos.get("contracts", 0)),
                            "entry_price": float(pos.get("entryPrice", 0) or 0),
                            "mark_price": float(pos.get("markPrice", 0) or 0),
                            "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
                            "leverage": pos.get("leverage"),
                        })
            
            return {
                "exchange": self.exchange_id,
                "positions": positions,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return {"error": str(e), "positions": []}
    
    async def fetch_ticker(self, symbol: str) -> dict:
        """获取单个交易对行情"""
        exchange = self.get_public_exchange()
        if not exchange:
            return self._mock_ticker(symbol)
        
        try:
            ticker = exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high_24h": ticker.get("high"),
                "low_24h": ticker.get("low"),
                "volume_24h": ticker.get("baseVolume"),
                "quote_volume_24h": ticker.get("quoteVolume"),
                "change_24h": ticker.get("percentage"),
                "change_abs": ticker.get("change"),
                "vwap": ticker.get("vwap"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning(f"获取 {symbol} 行情失败: {e}")
            return self._mock_ticker(symbol)
    
    async def fetch_tickers(self, symbols: list[str] = None) -> list[dict]:
        """获取多个交易对行情"""
        exchange = self.get_public_exchange()
        if not exchange:
            return [self._mock_ticker(s) for s in (symbols or ["BTC/USDT"])]
        
        try:
            if symbols:
                # 逐个获取
                tickers = []
                for symbol in symbols:
                    tickers.append(await self.fetch_ticker(symbol))
                return tickers
            else:
                # 获取所有
                all_tickers = exchange.fetch_tickers()
                result = []
                for symbol, ticker in all_tickers.items():
                    if "/USDT" in symbol:  # 只返回 USDT 交易对
                        result.append({
                            "symbol": symbol,
                            "last": ticker.get("last"),
                            "change_24h": ticker.get("percentage"),
                            "volume_24h": ticker.get("baseVolume"),
                            "high_24h": ticker.get("high"),
                            "low_24h": ticker.get("low"),
                        })
                return sorted(result, key=lambda x: x.get("volume_24h") or 0, reverse=True)[:50]
        except Exception as e:
            logger.warning(f"获取行情列表失败: {e}")
            return [self._mock_ticker(s) for s in (symbols or ["BTC/USDT", "ETH/USDT"])]
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: int = None,
        limit: int = 100,
    ) -> list[dict]:
        """获取 K 线数据"""
        exchange = self.get_public_exchange()
        if not exchange:
            return self._mock_ohlcv(symbol, timeframe, limit)
        
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            return [
                {
                    "timestamp": row[0],
                    "datetime": datetime.utcfromtimestamp(row[0] / 1000).isoformat(),
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                }
                for row in ohlcv
            ]
        except Exception as e:
            logger.warning(f"获取 {symbol} K线失败: {e}")
            return self._mock_ohlcv(symbol, timeframe, limit)
    
    def _mock_ticker(self, symbol: str) -> dict:
        """生成模拟行情"""
        import random
        base = 95000 if "BTC" in symbol else 3500 if "ETH" in symbol else 100
        last = base * (1 + random.uniform(-0.02, 0.02))
        change = random.uniform(-5, 5)
        return {
            "symbol": symbol,
            "last": round(last, 2),
            "bid": round(last * 0.9999, 2),
            "ask": round(last * 1.0001, 2),
            "high_24h": round(last * 1.03, 2),
            "low_24h": round(last * 0.97, 2),
            "volume_24h": round(random.uniform(10000, 100000), 2),
            "change_24h": round(change, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "_mock": True,
        }
    
    def _mock_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[dict]:
        """生成模拟 K 线数据"""
        import random
        import numpy as np
        
        base = 95000 if "BTC" in symbol else 3500 if "ETH" in symbol else 100
        
        tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
        interval_ms = tf_minutes.get(timeframe, 60) * 60 * 1000
        
        now = int(datetime.utcnow().timestamp() * 1000)
        
        result = []
        price = base
        for i in range(limit):
            ts = now - (limit - i) * interval_ms
            change = random.uniform(-0.02, 0.02)
            price = price * (1 + change)
            volatility = abs(random.gauss(0, 0.01))
            
            result.append({
                "timestamp": ts,
                "datetime": datetime.utcfromtimestamp(ts / 1000).isoformat(),
                "open": round(price * (1 - volatility/2), 2),
                "high": round(price * (1 + volatility), 2),
                "low": round(price * (1 - volatility), 2),
                "close": round(price, 2),
                "volume": round(random.uniform(100, 10000), 2),
            })
        
        return result


class MarketTools:
    """市场数据工具 - 供 Agent 调用"""
    
    def __init__(
        self,
        parquet_path: Optional[str] = None,
        exchange: Optional[str] = None,
    ):
        """初始化市场工具
        
        Args:
            parquet_path: Parquet 文件存储路径
            exchange: 交易所名称
        """
        self.parquet_path = Path(parquet_path or os.getenv("PARQUET_PATH", "./data/parquet"))
        self.parquet_path.mkdir(parents=True, exist_ok=True)
        self.exchange_manager = ExchangeManager.get_instance(exchange)
    
    def _compute_data_version_hash(
        self,
        symbols: list[str],
        timeframe: str,
        start: datetime,
        end: datetime,
        data_hash: str,
    ) -> str:
        """计算数据版本哈希"""
        content = f"{sorted(symbols)}|{timeframe}|{start.isoformat()}|{end.isoformat()}|{data_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def get_ohlcv(
        self,
        market: str,
        symbols: list[str],
        timeframe: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 500,
    ) -> dict:
        """获取 OHLCV 数据
        
        Args:
            market: 市场类型 (crypto/us_equity)
            symbols: 交易对列表
            timeframe: K线周期
            start: 开始时间
            end: 结束时间
            limit: 最大行数
            
        Returns:
            包含 data_version_hash, parquet_path, preview_rows 的字典
        """
        logger.info("获取 OHLCV 数据", market=market, symbols=symbols, timeframe=timeframe, limit=limit)
        
        now = datetime.utcnow()
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else now - timedelta(days=30)
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else now
        
        try:
            import pandas as pd
            
            all_data = []
            
            for symbol in symbols:
                if market == "crypto":
                    ohlcv_list = await self.exchange_manager.fetch_ohlcv(
                        symbol,
                        timeframe=timeframe,
                        since=int(start_dt.timestamp() * 1000),
                        limit=min(limit, 1000),
                    )
                    
                    if ohlcv_list:
                        df = pd.DataFrame(ohlcv_list)
                        df["symbol"] = symbol
                        all_data.append(df)
                else:
                    all_data.append(self._generate_mock_ohlcv(symbol, timeframe, start_dt, end_dt, limit))
            
            if all_data:
                combined = pd.concat(all_data, ignore_index=True)
            else:
                combined = pd.DataFrame(columns=["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol"])
            
            # 计算数据哈希
            data_hash = hashlib.md5(combined.to_json().encode()).hexdigest()[:8]
            version_hash = self._compute_data_version_hash(symbols, timeframe, start_dt, end_dt, data_hash)
            
            # 保存 parquet
            parquet_filename = f"ohlcv_{version_hash}.parquet"
            parquet_file = self.parquet_path / parquet_filename
            combined.to_parquet(parquet_file, index=False)
            
            preview = combined.tail(10).to_dict(orient="records")
            
            logger.info("OHLCV 数据获取完成", version_hash=version_hash, row_count=len(combined))
            
            return {
                "data_version_hash": version_hash,
                "parquet_path": str(parquet_file),
                "row_count": len(combined),
                "symbols": symbols,
                "timeframe": timeframe,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "preview_rows": preview,
            }
            
        except ImportError:
            logger.error("pandas 未安装")
            raise RuntimeError("pandas is required for OHLCV data")
    
    def _generate_mock_ohlcv(self, symbol: str, timeframe: str, start: datetime, end: datetime, limit: int):
        """生成模拟 OHLCV 数据"""
        import pandas as pd
        import numpy as np
        
        timeframe_map = {
            "1m": timedelta(minutes=1), "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15), "1h": timedelta(hours=1),
            "4h": timedelta(hours=4), "1d": timedelta(days=1),
        }
        interval = timeframe_map.get(timeframe, timedelta(hours=1))
        
        timestamps = []
        current = start
        while current < end and len(timestamps) < limit:
            timestamps.append(current)
            current += interval
        
        n = len(timestamps)
        if n == 0:
            return pd.DataFrame(columns=["timestamp", "datetime", "open", "high", "low", "close", "volume", "symbol"])
        
        np.random.seed(hash(symbol) % (2**32))
        base_price = 95000 if "BTC" in symbol else 3500 if "ETH" in symbol else 100
        
        returns = np.random.normal(0.0001, 0.02, n)
        prices = base_price * np.cumprod(1 + returns)
        volatility = np.abs(np.random.normal(0, 0.01, n))
        
        return pd.DataFrame({
            "timestamp": [int(t.timestamp() * 1000) for t in timestamps],
            "datetime": [t.isoformat() for t in timestamps],
            "open": prices * (1 - volatility/2),
            "high": prices * (1 + volatility),
            "low": prices * (1 - volatility),
            "close": prices,
            "volume": np.random.lognormal(10, 1, n),
            "symbol": symbol,
        })
    
    async def get_quote(self, symbol: str, market: str = "crypto") -> dict:
        """获取当前报价"""
        logger.info("获取报价", symbol=symbol, market=market)
        return await self.exchange_manager.fetch_ticker(symbol)
    
    async def get_tickers(self, symbols: list[str] = None) -> list[dict]:
        """获取多个交易对行情"""
        return await self.exchange_manager.fetch_tickers(symbols)
    
    async def get_balance(self) -> dict:
        """获取账户余额"""
        return await self.exchange_manager.fetch_balance()
    
    async def get_positions(self) -> dict:
        """获取持仓"""
        return await self.exchange_manager.fetch_positions()
    
    async def compute_indicators(self, data_ref: dict, indicators: list[dict]) -> dict:
        """计算技术指标
        
        Args:
            data_ref: 数据引用 (data_version_hash, parquet_path)
            indicators: 指标列表
            
        Returns:
            包含 feature_version_hash 和新 parquet_path 的字典
        """
        logger.info("计算技术指标", data_ref=data_ref, indicators=[i.get("name") for i in indicators])
        
        try:
            import pandas as pd
            import numpy as np
            
            parquet_path = data_ref.get("parquet_path")
            if not parquet_path or not Path(parquet_path).exists():
                raise ValueError(f"Parquet 文件不存在: {parquet_path}")
            
            df = pd.read_parquet(parquet_path)
            
            for indicator in indicators:
                name = indicator.get("name")
                window = indicator.get("window", 14)
                params = indicator.get("params", {})
                
                if name == "sma":
                    df[f"sma_{window}"] = df.groupby("symbol")["close"].transform(
                        lambda x: x.rolling(window=window).mean()
                    )
                elif name == "ema":
                    df[f"ema_{window}"] = df.groupby("symbol")["close"].transform(
                        lambda x: x.ewm(span=window, adjust=False).mean()
                    )
                elif name == "rsi":
                    def calc_rsi(prices, w):
                        delta = prices.diff()
                        gain = delta.where(delta > 0, 0).rolling(window=w).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=w).mean()
                        rs = gain / loss
                        return 100 - (100 / (1 + rs))
                    df[f"rsi_{window}"] = df.groupby("symbol")["close"].transform(lambda x: calc_rsi(x, window))
                elif name == "bollinger":
                    df[f"bb_mid_{window}"] = df.groupby("symbol")["close"].transform(lambda x: x.rolling(window=window).mean())
                    df[f"bb_std_{window}"] = df.groupby("symbol")["close"].transform(lambda x: x.rolling(window=window).std())
                    std_mult = params.get("std", 2)
                    df[f"bb_upper_{window}"] = df[f"bb_mid_{window}"] + std_mult * df[f"bb_std_{window}"]
                    df[f"bb_lower_{window}"] = df[f"bb_mid_{window}"] - std_mult * df[f"bb_std_{window}"]
            
            indicator_str = str(sorted([(i["name"], i.get("window", 14)) for i in indicators]))
            original_hash = data_ref.get("data_version_hash", "")
            feature_hash = hashlib.sha256(f"{original_hash}|{indicator_str}".encode()).hexdigest()[:16]
            
            new_parquet = self.parquet_path / f"features_{feature_hash}.parquet"
            df.to_parquet(new_parquet, index=False)
            
            logger.info("技术指标计算完成", feature_hash=feature_hash, indicators_added=len(indicators))
            
            return {
                "feature_version_hash": feature_hash,
                "parquet_path": str(new_parquet),
                "original_data_version_hash": original_hash,
                "indicators_computed": [i["name"] for i in indicators],
                "column_count": len(df.columns),
                "row_count": len(df),
            }
            
        except ImportError:
            logger.error("pandas/numpy 未安装")
            raise RuntimeError("pandas and numpy are required for indicator computation")


# 全局单例
_market_tools: Optional[MarketTools] = None


def get_market_tools() -> MarketTools:
    """获取 MarketTools 单例"""
    global _market_tools
    if _market_tools is None:
        _market_tools = MarketTools()
    return _market_tools
