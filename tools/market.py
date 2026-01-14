# AI Quant Company - Market Tools
"""
市场数据工具

提供:
- get_ohlcv: 获取 K 线数据
- get_quote: 获取当前报价
- compute_indicators: 计算技术指标
"""

import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class MarketTools:
    """市场数据工具"""
    
    def __init__(
        self,
        parquet_path: Optional[str] = None,
        exchange: Optional[str] = None,
    ):
        """初始化市场工具
        
        Args:
            parquet_path: Parquet 文件存储路径
            exchange: 交易所名称 (默认从环境变量 DEFAULT_EXCHANGE 读取，fallback 到 okx)
        """
        self.parquet_path = Path(parquet_path or os.getenv("PARQUET_PATH", "./data/parquet"))
        self.parquet_path.mkdir(parents=True, exist_ok=True)
        # 使用 OKX 作为默认交易所（Binance 在某些地区受限）
        self.exchange = exchange or os.getenv("DEFAULT_EXCHANGE", "okx")
        self._ccxt_exchange = None
    
    def _get_exchange(self):
        """获取 ccxt 交易所实例"""
        if self._ccxt_exchange is None:
            try:
                import ccxt
                exchange_class = getattr(ccxt, self.exchange)
                self._ccxt_exchange = exchange_class({
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',
                    },
                })
            except ImportError:
                logger.warning("ccxt 未安装，使用 Mock 数据")
                self._ccxt_exchange = None
            except Exception as e:
                logger.error("交易所初始化失败", error=str(e))
                self._ccxt_exchange = None
        return self._ccxt_exchange
    
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
        logger.info(
            "获取 OHLCV 数据",
            market=market,
            symbols=symbols,
            timeframe=timeframe,
            limit=limit,
        )
        
        # 解析时间
        now = datetime.utcnow()
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else now - timedelta(days=30)
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else now
        
        try:
            import pandas as pd
            
            all_data = []
            exchange = self._get_exchange()
            
            for symbol in symbols:
                if exchange and market == "crypto":
                    # 使用 ccxt 获取真实数据
                    try:
                        ohlcv = exchange.fetch_ohlcv(
                            symbol,
                            timeframe=timeframe,
                            since=int(start_dt.timestamp() * 1000),
                            limit=min(limit, 1000),
                        )
                        
                        df = pd.DataFrame(
                            ohlcv,
                            columns=["timestamp", "open", "high", "low", "close", "volume"],
                        )
                        df["symbol"] = symbol
                        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                        all_data.append(df)
                        
                    except Exception as e:
                        logger.warning(f"获取 {symbol} 数据失败: {e}")
                        # 生成 mock 数据
                        all_data.append(self._generate_mock_ohlcv(symbol, timeframe, start_dt, end_dt, limit))
                else:
                    # 生成 mock 数据
                    all_data.append(self._generate_mock_ohlcv(symbol, timeframe, start_dt, end_dt, limit))
            
            if all_data:
                combined = pd.concat(all_data, ignore_index=True)
            else:
                combined = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"])
            
            # 计算数据哈希
            data_hash = hashlib.md5(combined.to_json().encode()).hexdigest()[:8]
            version_hash = self._compute_data_version_hash(symbols, timeframe, start_dt, end_dt, data_hash)
            
            # 保存 parquet
            parquet_filename = f"ohlcv_{version_hash}.parquet"
            parquet_file = self.parquet_path / parquet_filename
            combined.to_parquet(parquet_file, index=False)
            
            # 预览数据
            preview = combined.head(10).to_dict(orient="records")
            
            logger.info(
                "OHLCV 数据获取完成",
                version_hash=version_hash,
                row_count=len(combined),
            )
            
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
    
    def _generate_mock_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int,
    ):
        """生成模拟 OHLCV 数据"""
        import pandas as pd
        import numpy as np
        
        # 根据 timeframe 计算间隔
        timeframe_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1),
        }
        interval = timeframe_map.get(timeframe, timedelta(hours=1))
        
        # 生成时间序列
        timestamps = []
        current = start
        while current < end and len(timestamps) < limit:
            timestamps.append(current)
            current += interval
        
        n = len(timestamps)
        if n == 0:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"])
        
        # 生成价格数据（随机漫步）
        np.random.seed(hash(symbol) % (2**32))
        base_price = 50000 if "BTC" in symbol else 3000 if "ETH" in symbol else 100
        
        returns = np.random.normal(0.0001, 0.02, n)
        prices = base_price * np.cumprod(1 + returns)
        
        volatility = np.abs(np.random.normal(0, 0.01, n))
        
        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": prices * (1 - volatility/2),
            "high": prices * (1 + volatility),
            "low": prices * (1 - volatility),
            "close": prices,
            "volume": np.random.lognormal(10, 1, n),
            "symbol": symbol,
        })
        
        return df
    
    async def get_quote(
        self,
        symbol: str,
        market: str = "crypto",
    ) -> dict:
        """获取当前报价
        
        Args:
            symbol: 交易对
            market: 市场类型
            
        Returns:
            报价信息
        """
        logger.info("获取报价", symbol=symbol, market=market)
        
        exchange = self._get_exchange()
        
        if exchange and market == "crypto":
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
                    "change_24h": ticker.get("percentage"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                logger.warning(f"获取报价失败: {e}")
        
        # Mock 数据
        import random
        base_price = 50000 if "BTC" in symbol else 3000 if "ETH" in symbol else 100
        last = base_price * (1 + random.uniform(-0.01, 0.01))
        
        return {
            "symbol": symbol,
            "last": last,
            "bid": last * 0.9999,
            "ask": last * 1.0001,
            "high_24h": last * 1.02,
            "low_24h": last * 0.98,
            "volume_24h": random.uniform(1000, 10000),
            "change_24h": random.uniform(-5, 5),
            "timestamp": datetime.utcnow().isoformat(),
            "_mock": True,
        }
    
    async def compute_indicators(
        self,
        data_ref: dict,
        indicators: list[dict],
    ) -> dict:
        """计算技术指标
        
        Args:
            data_ref: 数据引用 (data_version_hash, parquet_path)
            indicators: 指标列表
            
        Returns:
            包含 feature_version_hash 和新 parquet_path 的字典
        """
        logger.info(
            "计算技术指标",
            data_ref=data_ref,
            indicators=[i.get("name") for i in indicators],
        )
        
        try:
            import pandas as pd
            import numpy as np
            
            # 读取原始数据
            parquet_path = data_ref.get("parquet_path")
            if not parquet_path or not Path(parquet_path).exists():
                raise ValueError(f"Parquet 文件不存在: {parquet_path}")
            
            df = pd.read_parquet(parquet_path)
            
            # 计算每个指标
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
                    def calc_rsi(prices, window):
                        delta = prices.diff()
                        gain = delta.where(delta > 0, 0).rolling(window=window).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                        rs = gain / loss
                        return 100 - (100 / (1 + rs))
                    
                    df[f"rsi_{window}"] = df.groupby("symbol")["close"].transform(
                        lambda x: calc_rsi(x, window)
                    )
                
                elif name == "atr":
                    def calc_atr(group, window):
                        high = group["high"]
                        low = group["low"]
                        close = group["close"]
                        tr1 = high - low
                        tr2 = abs(high - close.shift())
                        tr3 = abs(low - close.shift())
                        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                        return tr.rolling(window=window).mean()
                    
                    df[f"atr_{window}"] = df.groupby("symbol").apply(
                        lambda x: calc_atr(x, window)
                    ).reset_index(level=0, drop=True)
                
                elif name == "volatility":
                    df[f"volatility_{window}"] = df.groupby("symbol")["close"].transform(
                        lambda x: x.pct_change().rolling(window=window).std() * np.sqrt(252)
                    )
                
                elif name == "max_drawdown":
                    def calc_max_dd(prices, window):
                        rolling_max = prices.rolling(window=window).max()
                        drawdown = (prices - rolling_max) / rolling_max
                        return drawdown.rolling(window=window).min()
                    
                    df[f"max_dd_{window}"] = df.groupby("symbol")["close"].transform(
                        lambda x: calc_max_dd(x, window)
                    )
                
                elif name == "bollinger":
                    df[f"bb_mid_{window}"] = df.groupby("symbol")["close"].transform(
                        lambda x: x.rolling(window=window).mean()
                    )
                    df[f"bb_std_{window}"] = df.groupby("symbol")["close"].transform(
                        lambda x: x.rolling(window=window).std()
                    )
                    std_mult = params.get("std", 2)
                    df[f"bb_upper_{window}"] = df[f"bb_mid_{window}"] + std_mult * df[f"bb_std_{window}"]
                    df[f"bb_lower_{window}"] = df[f"bb_mid_{window}"] - std_mult * df[f"bb_std_{window}"]
            
            # 计算新的版本哈希
            indicator_str = str(sorted([(i["name"], i.get("window", 14)) for i in indicators]))
            original_hash = data_ref.get("data_version_hash", "")
            feature_hash = hashlib.sha256(f"{original_hash}|{indicator_str}".encode()).hexdigest()[:16]
            
            # 保存新的 parquet
            new_parquet = self.parquet_path / f"features_{feature_hash}.parquet"
            df.to_parquet(new_parquet, index=False)
            
            logger.info(
                "技术指标计算完成",
                feature_hash=feature_hash,
                indicators_added=len(indicators),
            )
            
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
