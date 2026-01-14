# AI Quant Company - Tool Registry
"""
工具注册表

提供:
- OpenAI function calling 格式的工具 schema
- 工具注册与发现
- 工具执行结果封装
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class ToolCategory(str, Enum):
    """工具类别"""
    MARKET = "market"
    BACKTEST = "backtest"
    MEMORY = "memory"
    MEETING = "meeting"


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    
    # 可追溯性
    data_version_hash: Optional[str] = None
    experiment_id: Optional[str] = None
    artifact_ids: list[str] = field(default_factory=list)
    
    # 资源消耗
    compute_points_used: int = 0
    
    # 时间
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "data_version_hash": self.data_version_hash,
            "experiment_id": self.experiment_id,
            "artifact_ids": self.artifact_ids,
            "compute_points_used": self.compute_points_used,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class ToolSchema:
    """工具 Schema（OpenAI function calling 格式）"""
    name: str
    description: str
    category: ToolCategory
    parameters: dict  # JSON Schema
    
    # 成本估算
    base_cost: int = 1  # 基础 Compute Points
    cost_per_unit: float = 0.0  # 每单位成本（如每1000行数据）
    cost_unit: Optional[str] = None  # 成本单位（如 "rows", "params"）
    
    # 权限
    requires_approval_above: Optional[int] = None  # 超过此成本需要审批
    allowed_departments: list[str] = field(default_factory=list)  # 空表示所有
    
    def to_openai_schema(self) -> dict:
        """转换为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
    
    def estimate_cost(self, args: dict) -> int:
        """估算执行成本"""
        cost = self.base_cost
        
        if self.cost_per_unit > 0 and self.cost_unit:
            # 根据参数估算
            if self.cost_unit == "rows":
                limit = args.get("limit", 500)
                cost += int(limit * self.cost_per_unit)
            elif self.cost_unit == "params":
                params_count = len(args.get("parameters", {}))
                cost += int(params_count * self.cost_per_unit)
            elif self.cost_unit == "indicators":
                indicators = args.get("indicators", [])
                cost += int(len(indicators) * self.cost_per_unit)
        
        return cost


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: dict[str, ToolSchema] = {}
        self._handlers: dict[str, Callable] = {}
        self._register_all_tools()
    
    def _register_all_tools(self) -> None:
        """注册所有工具"""
        # ============================================
        # T1: market.get_ohlcv
        # ============================================
        self.register(
            ToolSchema(
                name="market.get_ohlcv",
                description="获取价格K线数据（OHLCV），支持实时和历史数据。返回 data_version_hash 和 parquet_path。",
                category=ToolCategory.MARKET,
                parameters={
                    "type": "object",
                    "properties": {
                        "market": {
                            "type": "string",
                            "enum": ["crypto", "us_equity"],
                            "description": "市场类型",
                        },
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "交易对列表，如 ['BTC/USDT', 'ETH/USDT']",
                        },
                        "timeframe": {
                            "type": "string",
                            "enum": ["1m", "5m", "15m", "1h", "4h", "1d"],
                            "description": "K线周期",
                        },
                        "start": {
                            "type": "string",
                            "format": "date-time",
                            "description": "开始时间 (ISO 8601)",
                        },
                        "end": {
                            "type": "string",
                            "format": "date-time",
                            "description": "结束时间 (ISO 8601)",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10000,
                            "default": 500,
                            "description": "返回的最大行数",
                        },
                    },
                    "required": ["market", "symbols", "timeframe"],
                },
                base_cost=1,
                cost_per_unit=0.01,
                cost_unit="rows",
                allowed_departments=["research_guild", "data_division", "backtest_engine"],
            )
        )
        
        # ============================================
        # T2: market.get_quote
        # ============================================
        self.register(
            ToolSchema(
                name="market.get_quote",
                description="获取当前价格/盘口信息（last price, 24h stats）",
                category=ToolCategory.MARKET,
                parameters={
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "交易对，如 'BTC/USDT'",
                        },
                        "market": {
                            "type": "string",
                            "enum": ["crypto", "us_equity"],
                            "default": "crypto",
                        },
                    },
                    "required": ["symbol"],
                },
                base_cost=1,
            )
        )
        
        # ============================================
        # T3: market.compute_indicators
        # ============================================
        self.register(
            ToolSchema(
                name="market.compute_indicators",
                description="对 OHLCV 数据计算技术指标（MA/RSI/ATR/波动率/回撤等）",
                category=ToolCategory.MARKET,
                parameters={
                    "type": "object",
                    "properties": {
                        "data_ref": {
                            "type": "object",
                            "properties": {
                                "data_version_hash": {"type": "string"},
                                "parquet_path": {"type": "string"},
                            },
                            "required": ["data_version_hash"],
                            "description": "数据引用（来自 get_ohlcv）",
                        },
                        "indicators": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "enum": ["sma", "ema", "rsi", "atr", "volatility", "max_drawdown", "bollinger"],
                                    },
                                    "window": {"type": "integer", "minimum": 1},
                                    "params": {"type": "object"},
                                },
                                "required": ["name"],
                            },
                            "description": "要计算的指标列表",
                        },
                    },
                    "required": ["data_ref", "indicators"],
                },
                base_cost=2,
                cost_per_unit=1,
                cost_unit="indicators",
            )
        )
        
        # ============================================
        # T4: backtest.run
        # ============================================
        self.register(
            ToolSchema(
                name="backtest.run",
                description="执行回测，返回 experiment_id、metrics 和 artifacts。必须产生可复现的 ExperimentID。",
                category=ToolCategory.BACKTEST,
                parameters={
                    "type": "object",
                    "properties": {
                        "strategy_spec": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "universe": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "timeframe": {"type": "string"},
                                "signal_def": {"type": "string"},
                                "positioning": {"type": "object"},
                                "risk_rules": {"type": "object"},
                            },
                            "required": ["name", "universe", "timeframe", "signal_def"],
                        },
                        "data_ref": {
                            "type": "object",
                            "properties": {
                                "data_version_hash": {"type": "string"},
                            },
                            "required": ["data_version_hash"],
                        },
                        "cost_model": {
                            "type": "object",
                            "properties": {
                                "fee_bps": {"type": "number"},
                                "slippage_bps": {"type": "number"},
                            },
                        },
                        "split": {
                            "type": "object",
                            "properties": {
                                "train": {"type": "string"},
                                "test": {"type": "string"},
                            },
                        },
                        "robustness": {
                            "type": "object",
                            "properties": {
                                "walk_forward": {"type": "boolean"},
                                "param_perturb": {"type": "integer"},
                            },
                        },
                    },
                    "required": ["strategy_spec", "data_ref"],
                },
                base_cost=50,
                cost_per_unit=10,
                cost_unit="params",
                requires_approval_above=200,
                allowed_departments=["research_guild", "backtest_engine"],
            )
        )
        
        # ============================================
        # T5: memory.write
        # ============================================
        self.register(
            ToolSchema(
                name="memory.write",
                description="将关键结论/数据摘要写入 Agent 长期记忆。内容限制500字，必须包含引用。team/org 范围需要审批。",
                category=ToolCategory.MEMORY,
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Agent ID",
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["private", "team", "org"],
                            "default": "private",
                            "description": "可见范围",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "标签，用于检索",
                        },
                        "content": {
                            "type": "string",
                            "maxLength": 500,
                            "description": "结论摘要（<=500字）",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 1.0,
                            "description": "置信度",
                        },
                        "refs": {
                            "type": "object",
                            "properties": {
                                "experiment_id": {"type": "string"},
                                "data_version_hash": {"type": "string"},
                                "artifact_id": {"type": "string"},
                            },
                            "description": "引用的实验/数据/产物",
                        },
                        "ttl_days": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "记忆有效期（天）",
                        },
                    },
                    "required": ["agent_id", "tags", "content", "refs"],
                },
                base_cost=2,
            )
        )
        
        # ============================================
        # T6: memory.search
        # ============================================
        self.register(
            ToolSchema(
                name="memory.search",
                description="检索 Agent 记忆（混合搜索：标签+关键词+向量相似度）",
                category=ToolCategory.MEMORY,
                parameters={
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Agent ID",
                        },
                        "query": {
                            "type": "string",
                            "description": "搜索查询",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "过滤标签",
                        },
                        "scopes": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["private", "team", "org"],
                            },
                            "default": ["private"],
                            "description": "搜索范围",
                        },
                        "top_k": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 5,
                            "description": "返回结果数",
                        },
                    },
                    "required": ["agent_id", "query"],
                },
                base_cost=1,
            )
        )
        
        # ============================================
        # T7: meeting.present
        # ============================================
        self.register(
            ToolSchema(
                name="meeting.present",
                description="在会议中展示卡片（指标卡/图表/表格/摘要）。只能在会议上下文中调用。",
                category=ToolCategory.MEETING,
                parameters={
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "会议 ID",
                        },
                        "title": {
                            "type": "string",
                            "description": "展示标题",
                        },
                        "cards": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["metric", "plot", "table", "summary"],
                                    },
                                    "data": {
                                        "type": "object",
                                        "description": "卡片数据",
                                    },
                                    "data_ref": {
                                        "type": "object",
                                        "properties": {
                                            "artifact_path": {"type": "string"},
                                            "parquet_path": {"type": "string"},
                                            "preview_rows": {"type": "integer"},
                                        },
                                    },
                                },
                                "required": ["type"],
                            },
                            "description": "要展示的卡片列表",
                        },
                    },
                    "required": ["meeting_id", "title", "cards"],
                },
                base_cost=5,
            )
        )
        
        logger.info("工具注册完成", tool_count=len(self._tools))
    
    def register(self, schema: ToolSchema, handler: Optional[Callable] = None) -> None:
        """注册工具"""
        self._tools[schema.name] = schema
        if handler:
            self._handlers[schema.name] = handler
    
    def get(self, name: str) -> Optional[ToolSchema]:
        """获取工具 schema"""
        return self._tools.get(name)
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """获取工具处理函数"""
        return self._handlers.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> list[ToolSchema]:
        """列出工具"""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools
    
    def to_openai_tools(self, category: Optional[ToolCategory] = None) -> list[dict]:
        """转换为 OpenAI tools 格式"""
        tools = self.list_tools(category)
        return [t.to_openai_schema() for t in tools]
    
    def estimate_cost(self, name: str, args: dict) -> int:
        """估算工具调用成本"""
        schema = self.get(name)
        if not schema:
            return 0
        return schema.estimate_cost(args)


# 全局注册表实例
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表单例"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
