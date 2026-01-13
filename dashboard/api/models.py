# AI Quant Company - API 数据模型
"""
Pydantic 模型定义

用于 API 请求和响应的数据验证。
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================
# 通用模型
# ============================================

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================
# Agent 模型
# ============================================

class AgentBase(BaseModel):
    """Agent 基础信息"""
    id: str
    name: str
    name_en: str
    department: str
    is_lead: bool


class AgentDetail(AgentBase):
    """Agent 详细信息"""
    capability_tier: str
    team: Optional[str] = None
    reports_to: Optional[str] = None
    veto_power: bool = False
    can_force_retest: bool = False
    status: str = "active"
    budget_remaining: int = 0
    reputation_score: float = 0.5
    current_task: Optional[str] = None
    persona_style: Optional[str] = None


class AgentStatusUpdate(BaseModel):
    """Agent 状态更新"""
    status: Optional[str] = None
    current_task: Optional[str] = None


# ============================================
# 研究周期模型
# ============================================

class ResearchCycleBase(BaseModel):
    """研究周期基础信息"""
    id: str
    name: str
    description: Optional[str] = None
    current_state: str
    team: str
    proposer: str


class ResearchCycleCreate(BaseModel):
    """创建研究周期"""
    name: str
    description: Optional[str] = None
    team: str
    proposer: str


class ResearchCycleDetail(ResearchCycleBase):
    """研究周期详细信息"""
    previous_state: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    gates_passed: dict = {}
    experiment_ids: list[str] = []
    artifact_ids: list[str] = []
    final_decision: Optional[str] = None
    decision_reason: Optional[str] = None


class GateApprovalRequest(BaseModel):
    """闸门审批请求"""
    cycle_id: str
    gate: str
    approver: str
    decision: str  # APPROVED, REJECTED, RETURNED
    comments: Optional[str] = None
    required_experiments: list[str] = []
    veto_used: bool = False
    force_retest_used: bool = False


# ============================================
# 会议模型
# ============================================

class MeetingRequestCreate(BaseModel):
    """创建会议申请"""
    title: str
    goal: str
    agenda: list[str]
    participants: list[str]
    expected_artifacts: list[str] = []
    risk_level: str = "L"
    compute_cost_estimate: int = 0
    duration_minutes: int = 20
    research_cycle_id: Optional[str] = None


class MeetingRequestDetail(BaseModel):
    """会议申请详情"""
    id: str
    title: str
    goal: str
    agenda: list[str]
    requester: str
    participants: list[str]
    expected_artifacts: list[str]
    risk_level: str
    compute_cost_estimate: int
    duration_minutes: int
    status: str
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    research_cycle_id: Optional[str] = None


class MeetingApprovalRequest(BaseModel):
    """会议审批请求"""
    meeting_id: str
    approver: str
    approved: bool
    comments: Optional[str] = None
    modifications: Optional[dict] = None


class MeetingMinutesCreate(BaseModel):
    """创建会议纪要"""
    meeting_id: str
    summary: str
    key_points: list[str]
    action_items: list[dict]  # [{agent, task, deadline}, ...]
    decisions: list[dict]  # [{decision, voters, result}, ...]
    attendees: list[str]


# ============================================
# 实验模型
# ============================================

class ExperimentBase(BaseModel):
    """实验基础信息"""
    id: str
    experiment_type: str
    status: str
    created_at: datetime


class ExperimentDetail(ExperimentBase):
    """实验详细信息"""
    research_cycle_id: Optional[str] = None
    data_version_hash: str
    code_commit: str
    config_hash: str
    random_seed: Optional[int] = None
    config: dict
    metrics: Optional[dict] = None
    artifacts_path: Optional[str] = None
    compute_points_used: int = 0
    executed_by: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExperimentCreate(BaseModel):
    """创建实验"""
    research_cycle_id: Optional[str] = None
    experiment_type: str
    config: dict
    data_version_hash: str
    executed_by: str


# ============================================
# 报告模型
# ============================================

class ReportBase(BaseModel):
    """报告基础信息"""
    id: str
    report_type: str
    title: str
    created_at: datetime


class ReportDetail(ReportBase):
    """报告详细信息"""
    research_cycle_id: Optional[str] = None
    content: str
    metrics: Optional[dict] = None
    status: str
    created_by: str


# ============================================
# 董事长指令模型
# ============================================

class DirectiveCreate(BaseModel):
    """创建董事长指令"""
    directive_type: str
    target_type: str
    target_id: Optional[str] = None
    content: str
    reason: str
    scope: str = "global"
    effective_until: Optional[datetime] = None


class DirectiveDetail(BaseModel):
    """指令详情"""
    id: str
    directive_type: str
    target_type: str
    target_id: Optional[str] = None
    content: str
    reason: str
    scope: str
    status: str
    effective_from: datetime
    effective_until: Optional[datetime] = None
    created_at: datetime


# ============================================
# 消息模型
# ============================================

class MessageCreate(BaseModel):
    """创建消息"""
    message_type: str = "dm"
    to_agent: str
    subject: Optional[str] = None
    content: str


class MessageDetail(BaseModel):
    """消息详情"""
    id: str
    message_type: str
    from_agent: str
    to_agent: Optional[str] = None
    subject: Optional[str] = None
    content: str
    created_at: datetime
    read_at: Optional[datetime] = None


# ============================================
# 事件模型
# ============================================

class EventDetail(BaseModel):
    """事件详情"""
    id: str
    event_type: str
    actor: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    action: str
    details: dict = {}
    experiment_id: Optional[str] = None
    created_at: datetime


# ============================================
# 预算模型
# ============================================

class BudgetAccountDetail(BaseModel):
    """预算账户详情"""
    id: str
    account_type: str
    base_weekly_points: int
    current_period_points: int
    points_spent: int
    points_remaining: int
    reputation_multiplier: float
    current_period_start: datetime


class BudgetTransactionCreate(BaseModel):
    """创建预算交易"""
    account_id: str
    amount: int
    operation: str
    experiment_id: Optional[str] = None
    description: Optional[str] = None


# ============================================
# 声誉模型
# ============================================

class ReputationScoreDetail(BaseModel):
    """声誉评分详情"""
    agent_id: str
    overall_score: float
    grade: str
    pass_rate: Optional[float] = None
    return_rate: Optional[float] = None
    budget_efficiency: Optional[float] = None
    post_launch_performance: Optional[float] = None
    collaboration_score: Optional[float] = None
    sample_count: int = 0
    calculated_at: datetime


class ReputationEventCreate(BaseModel):
    """创建声誉事件"""
    agent_id: str
    event_type: str
    points_change: int
    research_cycle_id: Optional[str] = None
    experiment_id: Optional[str] = None
    description: Optional[str] = None
