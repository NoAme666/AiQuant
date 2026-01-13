# AI Quant Company - 数据源基类
"""
Market Data Provider 抽象基类

定义统一的数据接入接口，支持多种数据源（加密货币、美股等）。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import pandas as pd


# ============================================
# 枚举定义
# ============================================

class DataFrequency(str, Enum):
    """数据频率"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"


class AssetType(str, Enum):
    """资产类型"""
    CRYPTO_SPOT = "crypto_spot"
    CRYPTO_PERP = "crypto_perp"  # 永续合约
    STOCK = "stock"
    ETF = "etf"
    FUTURE = "future"


# ============================================
# 数据结构
# ============================================

@dataclass
class OHLCV:
    """OHLCV K线数据"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # 可选字段
    quote_volume: Optional[float] = None  # 报价货币成交量
    trades: Optional[int] = None          # 成交笔数


@dataclass
class DataRequest:
    """数据请求"""
    symbols: list[str]
    start: datetime
    end: datetime
    frequency: DataFrequency = DataFrequency.DAY_1
    asset_type: AssetType = AssetType.CRYPTO_SPOT
    
    # 可选参数
    adjust: bool = True      # 是否调整（复权等）
    include_volume: bool = True


@dataclass
class DataResponse:
    """数据响应"""
    data: pd.DataFrame
    symbols: list[str]
    start: datetime
    end: datetime
    frequency: DataFrequency
    
    # 元数据
    provider: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    row_count: int = 0
    
    # 数据质量
    missing_count: int = 0
    missing_symbols: list[str] = field(default_factory=list)


# ============================================
# 数据源基类
# ============================================

class MarketDataProvider(ABC):
    """市场数据提供者抽象基类
    
    所有数据源都必须继承此类并实现抽象方法。
    """
    
    def __init__(self, name: str):
        """初始化数据提供者
        
        Args:
            name: 提供者名称
        """
        self.name = name
        self._cache: dict[str, pd.DataFrame] = {}
    
    @property
    @abstractmethod
    def supported_frequencies(self) -> list[DataFrequency]:
        """支持的数据频率"""
        pass
    
    @property
    @abstractmethod
    def supported_asset_types(self) -> list[AssetType]:
        """支持的资产类型"""
        pass
    
    @abstractmethod
    async def get_ohlcv(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        frequency: DataFrequency = DataFrequency.DAY_1,
    ) -> DataResponse:
        """获取 OHLCV 数据
        
        Args:
            symbols: 交易对/股票代码列表
            start: 开始时间
            end: 结束时间
            frequency: 数据频率
            
        Returns:
            包含 OHLCV 数据的 DataFrame
        """
        pass
    
    @abstractmethod
    async def get_symbols(self) -> list[str]:
        """获取可用的交易对/股票列表
        
        Returns:
            符号列表
        """
        pass
    
    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """获取最新价格
        
        Args:
            symbol: 交易对/股票代码
            
        Returns:
            最新价格
        """
        # 默认实现：获取最近一根K线的收盘价
        end = datetime.utcnow()
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
        
        response = await self.get_ohlcv(
            symbols=[symbol],
            start=start,
            end=end,
            frequency=DataFrequency.DAY_1,
        )
        
        if response.data.empty:
            return None
        
        return float(response.data["close"].iloc[-1])
    
    def validate_request(self, request: DataRequest) -> list[str]:
        """验证数据请求
        
        Args:
            request: 数据请求
            
        Returns:
            错误列表
        """
        errors = []
        
        if request.frequency not in self.supported_frequencies:
            errors.append(f"不支持的数据频率: {request.frequency}")
        
        if request.asset_type not in self.supported_asset_types:
            errors.append(f"不支持的资产类型: {request.asset_type}")
        
        if request.start >= request.end:
            errors.append("开始时间必须早于结束时间")
        
        if not request.symbols:
            errors.append("必须指定至少一个交易对")
        
        return errors
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()


# ============================================
# 数据质量检查
# ============================================

class DataQualityChecker:
    """数据质量检查器"""
    
    @staticmethod
    def check_missing_values(df: pd.DataFrame) -> dict:
        """检查缺失值
        
        Returns:
            各列的缺失值数量
        """
        return df.isnull().sum().to_dict()
    
    @staticmethod
    def check_duplicates(df: pd.DataFrame, subset: Optional[list[str]] = None) -> int:
        """检查重复行
        
        Returns:
            重复行数量
        """
        return df.duplicated(subset=subset).sum()
    
    @staticmethod
    def check_price_anomalies(
        df: pd.DataFrame,
        price_col: str = "close",
        threshold: float = 0.5,
    ) -> list[int]:
        """检查价格异常（单日涨跌幅超过阈值）
        
        Args:
            df: 数据
            price_col: 价格列名
            threshold: 异常阈值（如 0.5 表示 50%）
            
        Returns:
            异常行索引列表
        """
        returns = df[price_col].pct_change().abs()
        return list(returns[returns > threshold].index)
    
    @staticmethod
    def check_ohlc_consistency(df: pd.DataFrame) -> list[int]:
        """检查 OHLC 一致性（high >= low, open/close 在 high/low 之间）
        
        Returns:
            不一致的行索引列表
        """
        inconsistent = []
        
        for idx, row in df.iterrows():
            if row["high"] < row["low"]:
                inconsistent.append(idx)
            elif row["open"] > row["high"] or row["open"] < row["low"]:
                inconsistent.append(idx)
            elif row["close"] > row["high"] or row["close"] < row["low"]:
                inconsistent.append(idx)
        
        return inconsistent
    
    @staticmethod
    def check_time_gaps(
        df: pd.DataFrame,
        time_col: str = "timestamp",
        expected_freq: str = "1D",
    ) -> list[tuple]:
        """检查时间间隙
        
        Returns:
            (开始时间, 结束时间, 缺失数量) 的列表
        """
        if df.empty:
            return []
        
        df = df.sort_values(time_col)
        expected_delta = pd.Timedelta(expected_freq)
        
        gaps = []
        for i in range(1, len(df)):
            prev_time = df[time_col].iloc[i - 1]
            curr_time = df[time_col].iloc[i]
            delta = curr_time - prev_time
            
            if delta > expected_delta * 1.5:  # 允许 50% 容差
                missing_count = int(delta / expected_delta) - 1
                gaps.append((prev_time, curr_time, missing_count))
        
        return gaps
