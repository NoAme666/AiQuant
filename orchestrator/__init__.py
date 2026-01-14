# AI Quant Company - 编排器模块
"""
Orchestrator 核心模块

包含:
- state_machine: ResearchCycle 状态机
- router: 消息路由与权限检查
- meeting: 会议申请与审批系统
- budget: 预算点数管理
- reputation: 声誉系统
- audit: 审计日志

治理与组织进化模块:
- governance: CGO 治理系统（冻结、审计、告警）
- people: CPO 人才系统（招聘、终止、绩效）
- capability: CTO* 能力系统（工具注册、缺口分析）
- feedback: 反馈通道（提交、路由、统计）
"""

from orchestrator.governance import GovernanceSystem, get_governance_system
from orchestrator.people import PeopleSystem, get_people_system
from orchestrator.capability import CapabilitySystem, get_capability_system
from orchestrator.feedback import FeedbackChannel, get_feedback_channel

__all__ = [
    # 治理系统
    "GovernanceSystem",
    "get_governance_system",
    # 人才系统
    "PeopleSystem",
    "get_people_system",
    # 能力系统
    "CapabilitySystem",
    "get_capability_system",
    # 反馈通道
    "FeedbackChannel",
    "get_feedback_channel",
]
