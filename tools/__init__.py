# AI Quant Company - Agent Tools Package
"""
Agent 工具系统

提供 Agent 可以自主调用的工具:
- market: 市场数据获取与指标计算
- backtest: 回测执行
- memory: 记忆读写与检索
- meeting: 会议展示

所有工具调用通过 Orchestrator 的 ToolRouter 进行权限和预算控制。
"""

from tools.registry import ToolRegistry, ToolSchema, ToolResult
from tools.market import MarketTools
from tools.backtest import BacktestTools
from tools.memory import MemoryTools
from tools.meeting import MeetingTools

__all__ = [
    "ToolRegistry",
    "ToolSchema",
    "ToolResult",
    "MarketTools",
    "BacktestTools",
    "MemoryTools",
    "MeetingTools",
]
