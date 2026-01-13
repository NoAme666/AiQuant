# AI Quant Company - 数据版本化
"""
数据版本管理

确保实验可复现性，通过 DataVersionHash 追踪数据版本。
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import structlog

logger = structlog.get_logger()


@dataclass
class DataVersion:
    """数据版本记录"""
    hash: str
    symbols: list[str]
    start_date: datetime
    end_date: datetime
    frequency: str
    provider: str
    row_count: int
    file_path: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


class DataVersionManager:
    """数据版本管理器
    
    管理数据的版本化存储和检索。
    """
    
    def __init__(self, storage_path: str = "./data/parquet"):
        """初始化版本管理器
        
        Args:
            storage_path: 数据存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 版本索引
        self._index_path = self.storage_path / "versions.json"
        self._versions: dict[str, DataVersion] = {}
        self._load_index()
    
    def _load_index(self) -> None:
        """加载版本索引"""
        if self._index_path.exists():
            with open(self._index_path) as f:
                data = json.load(f)
                for hash_id, v in data.items():
                    self._versions[hash_id] = DataVersion(
                        hash=v["hash"],
                        symbols=v["symbols"],
                        start_date=datetime.fromisoformat(v["start_date"]),
                        end_date=datetime.fromisoformat(v["end_date"]),
                        frequency=v["frequency"],
                        provider=v["provider"],
                        row_count=v["row_count"],
                        file_path=v["file_path"],
                        created_at=datetime.fromisoformat(v["created_at"]),
                        metadata=v.get("metadata", {}),
                    )
            logger.info("加载数据版本索引", count=len(self._versions))
    
    def _save_index(self) -> None:
        """保存版本索引"""
        data = {}
        for hash_id, v in self._versions.items():
            data[hash_id] = {
                "hash": v.hash,
                "symbols": v.symbols,
                "start_date": v.start_date.isoformat(),
                "end_date": v.end_date.isoformat(),
                "frequency": v.frequency,
                "provider": v.provider,
                "row_count": v.row_count,
                "file_path": v.file_path,
                "created_at": v.created_at.isoformat(),
                "metadata": v.metadata,
            }
        
        with open(self._index_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def compute_hash(
        self,
        df: pd.DataFrame,
        symbols: list[str],
        start: datetime,
        end: datetime,
        frequency: str,
    ) -> str:
        """计算数据版本哈希
        
        基于数据内容和元信息生成唯一哈希。
        
        Args:
            df: 数据 DataFrame
            symbols: 交易对列表
            start: 开始时间
            end: 结束时间
            frequency: 数据频率
            
        Returns:
            16位哈希字符串
        """
        # 组合哈希内容
        content = {
            "symbols": sorted(symbols),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "frequency": frequency,
            "row_count": len(df),
            "columns": list(df.columns),
        }
        
        # 添加数据统计（避免直接哈希大量数据）
        if not df.empty:
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    content[f"{col}_sum"] = float(df[col].sum())
                    content[f"{col}_mean"] = float(df[col].mean())
        
        # 计算哈希
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]
    
    def save(
        self,
        df: pd.DataFrame,
        symbols: list[str],
        start: datetime,
        end: datetime,
        frequency: str,
        provider: str,
        metadata: Optional[dict] = None,
    ) -> DataVersion:
        """保存数据并版本化
        
        Args:
            df: 数据 DataFrame
            symbols: 交易对列表
            start: 开始时间
            end: 结束时间
            frequency: 数据频率
            provider: 数据提供者
            metadata: 额外元数据
            
        Returns:
            数据版本记录
        """
        # 计算哈希
        hash_id = self.compute_hash(df, symbols, start, end, frequency)
        
        # 检查是否已存在
        if hash_id in self._versions:
            logger.info("数据版本已存在", hash=hash_id)
            return self._versions[hash_id]
        
        # 保存文件
        file_name = f"{hash_id}.parquet"
        file_path = self.storage_path / file_name
        df.to_parquet(file_path, index=False)
        
        # 创建版本记录
        version = DataVersion(
            hash=hash_id,
            symbols=symbols,
            start_date=start,
            end_date=end,
            frequency=frequency,
            provider=provider,
            row_count=len(df),
            file_path=str(file_path),
            metadata=metadata or {},
        )
        
        # 更新索引
        self._versions[hash_id] = version
        self._save_index()
        
        logger.info(
            "保存数据版本",
            hash=hash_id,
            symbols=symbols,
            rows=len(df),
        )
        
        return version
    
    def load(self, hash_id: str) -> Optional[pd.DataFrame]:
        """加载指定版本的数据
        
        Args:
            hash_id: 数据版本哈希
            
        Returns:
            数据 DataFrame，不存在则返回 None
        """
        if hash_id not in self._versions:
            logger.warning("数据版本不存在", hash=hash_id)
            return None
        
        version = self._versions[hash_id]
        file_path = Path(version.file_path)
        
        if not file_path.exists():
            logger.error("数据文件不存在", path=str(file_path))
            return None
        
        df = pd.read_parquet(file_path)
        logger.info("加载数据版本", hash=hash_id, rows=len(df))
        
        return df
    
    def get_version(self, hash_id: str) -> Optional[DataVersion]:
        """获取版本信息"""
        return self._versions.get(hash_id)
    
    def list_versions(
        self,
        symbols: Optional[list[str]] = None,
        provider: Optional[str] = None,
        limit: int = 100,
    ) -> list[DataVersion]:
        """列出数据版本
        
        Args:
            symbols: 过滤交易对
            provider: 过滤提供者
            limit: 最大数量
            
        Returns:
            版本列表
        """
        versions = list(self._versions.values())
        
        # 过滤
        if symbols:
            symbol_set = set(symbols)
            versions = [v for v in versions if set(v.symbols) & symbol_set]
        
        if provider:
            versions = [v for v in versions if v.provider == provider]
        
        # 按时间排序
        versions.sort(key=lambda x: x.created_at, reverse=True)
        
        return versions[:limit]
    
    def delete(self, hash_id: str) -> bool:
        """删除数据版本
        
        Args:
            hash_id: 数据版本哈希
            
        Returns:
            是否成功删除
        """
        if hash_id not in self._versions:
            return False
        
        version = self._versions[hash_id]
        file_path = Path(version.file_path)
        
        # 删除文件
        if file_path.exists():
            file_path.unlink()
        
        # 更新索引
        del self._versions[hash_id]
        self._save_index()
        
        logger.info("删除数据版本", hash=hash_id)
        
        return True


# ============================================
# 配置版本化
# ============================================

def compute_config_hash(config: dict[str, Any]) -> str:
    """计算配置哈希
    
    Args:
        config: 配置字典
        
    Returns:
        16位哈希字符串
    """
    config_str = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def compute_feature_hash(
    feature_config: dict,
    data_hash: str,
) -> str:
    """计算特征版本哈希
    
    Args:
        feature_config: 特征配置
        data_hash: 原始数据哈希
        
    Returns:
        16位哈希字符串
    """
    content = {
        "feature_config": feature_config,
        "data_hash": data_hash,
    }
    content_str = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(content_str.encode()).hexdigest()[:16]
