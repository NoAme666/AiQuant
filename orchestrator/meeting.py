# AI Quant Company - 会议申请与审批系统
"""
会议系统

实现:
- 会议申请创建
- 多级审批链
- 会议生命周期管理
- 会议产物归档

审批链:
申请 → Chief of Staff 初审 → CRO 复审(涉及风险时) → CIO 终审 → Chairman(High风险)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import structlog
import yaml

logger = structlog.get_logger()


# ============================================
# 枚举定义
# ============================================

class MeetingStatus(str, Enum):
    """会议状态"""
    DRAFT = "DRAFT"                     # 草稿
    PENDING_APPROVAL = "PENDING_APPROVAL"  # 待审批
    APPROVED = "APPROVED"               # 已批准
    REJECTED = "REJECTED"               # 已拒绝
    SCHEDULED = "SCHEDULED"             # 已排期
    IN_PROGRESS = "IN_PROGRESS"         # 进行中
    COMPLETED = "COMPLETED"             # 已完成
    CANCELLED = "CANCELLED"             # 已取消


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "L"
    MEDIUM = "M"
    HIGH = "H"


class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"  # 条件不满足，跳过


# ============================================
# 数据类定义
# ============================================

@dataclass
class MeetingRequest:
    """会议申请"""
    id: UUID = field(default_factory=uuid4)
    
    # 基本信息
    title: str = ""
    goal: str = ""  # 一句话目标
    agenda: list[str] = field(default_factory=list)  # 3-5 条议程
    
    # 参与者
    requester: str = ""  # agent_id
    participants: list[str] = field(default_factory=list)
    
    # 预期产物
    expected_artifacts: list[str] = field(default_factory=list)
    
    # 风险与资源
    risk_level: RiskLevel = RiskLevel.LOW
    compute_cost_estimate: int = 0
    duration_minutes: int = 20
    
    # 状态
    status: MeetingStatus = MeetingStatus.DRAFT
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # 关联
    research_cycle_id: Optional[UUID] = None
    
    # 审批进度
    current_approval_step: int = 0
    
    def validate(self) -> list[str]:
        """验证会议申请完整性
        
        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []
        
        if not self.title:
            errors.append("会议标题不能为空")
        if not self.goal:
            errors.append("会议目标不能为空")
        if len(self.agenda) < 1:
            errors.append("至少需要 1 条议程")
        if len(self.agenda) > 5:
            errors.append("议程不能超过 5 条")
        if not self.requester:
            errors.append("申请人不能为空")
        if len(self.participants) < 2:
            errors.append("参与者至少需要 2 人")
        if self.duration_minutes < 10:
            errors.append("会议时长至少 10 分钟")
        if self.duration_minutes > 120:
            errors.append("会议时长不能超过 120 分钟")
            
        return errors


@dataclass
class MeetingApproval:
    """会议审批记录"""
    id: UUID = field(default_factory=uuid4)
    meeting_id: UUID = field(default_factory=uuid4)
    
    # 审批步骤
    step: int = 0
    approver: str = ""  # agent_id
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # 详情
    comments: str = ""
    modifications: dict = field(default_factory=dict)  # 对会议申请的修改建议
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None


@dataclass
class MeetingMinutes:
    """会议纪要"""
    id: UUID = field(default_factory=uuid4)
    meeting_id: UUID = field(default_factory=uuid4)
    
    # 内容
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    action_items: list[dict] = field(default_factory=list)  # [{agent, task, deadline}, ...]
    decisions: list[dict] = field(default_factory=list)  # [{decision, voters, result}, ...]
    
    # 参与者签名
    attendees: list[str] = field(default_factory=list)
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)


# ============================================
# 审批链配置
# ============================================

@dataclass
class ApprovalStepConfig:
    """审批步骤配置"""
    step: int
    approver: str  # agent_id
    condition: Optional[str] = None  # 触发条件
    trigger_keywords: list[str] = field(default_factory=list)
    timeout_hours: int = 4
    can_modify: bool = True


# 默认审批链配置
DEFAULT_APPROVAL_CHAIN: list[ApprovalStepConfig] = [
    ApprovalStepConfig(
        step=1,
        approver="chief_of_staff",
        timeout_hours=4,
        can_modify=True,
    ),
    ApprovalStepConfig(
        step=2,
        approver="cro",
        condition="涉及风险/资金/上线/生产",
        trigger_keywords=["risk", "production", "launch", "capital", "live", "风险", "上线", "生产"],
        timeout_hours=4,
        can_modify=False,
    ),
    ApprovalStepConfig(
        step=3,
        approver="cio",
        timeout_hours=8,
        can_modify=False,
    ),
    ApprovalStepConfig(
        step=4,
        approver="chairman",
        condition="risk_level == 'H' OR meeting_type == 'board'",
        timeout_hours=24,
        can_modify=False,
    ),
]


# ============================================
# 会议系统
# ============================================

class MeetingSystem:
    """会议系统
    
    管理会议的完整生命周期，包括申请、审批、执行和归档。
    """
    
    def __init__(self, permissions_config: Optional[dict] = None):
        """初始化会议系统
        
        Args:
            permissions_config: 权限配置（从 permissions.yaml 加载）
        """
        self.permissions = permissions_config or {}
        self.approval_chain = DEFAULT_APPROVAL_CHAIN
        
        # 内存存储（实际应用中应使用数据库）
        self._meetings: dict[UUID, MeetingRequest] = {}
        self._approvals: dict[UUID, list[MeetingApproval]] = {}
        self._minutes: dict[UUID, MeetingMinutes] = {}
        
    def load_permissions(self, config_path: str) -> None:
        """从配置文件加载权限配置"""
        with open(config_path) as f:
            self.permissions = yaml.safe_load(f)
    
    def can_request_meeting(self, agent_id: str, is_lead: bool = False) -> bool:
        """检查 Agent 是否有权申请会议
        
        Args:
            agent_id: Agent ID
            is_lead: 是否为 Lead
            
        Returns:
            是否有权限
        """
        # Lead 可以申请会议
        if is_lead:
            return True
        
        # 特殊角色（审计/CRO）可以申请紧急会议
        special_agents = ["audit_compliance", "cro"]
        if agent_id in special_agents:
            return True
        
        return False
    
    def create_request(self, request: MeetingRequest) -> tuple[bool, list[str]]:
        """创建会议申请
        
        Args:
            request: 会议申请
            
        Returns:
            (是否成功, 错误列表)
        """
        # 验证申请
        errors = request.validate()
        if errors:
            return False, errors
        
        # 检查申请人权限
        # 注：实际应用中需要查询 agent 信息
        # 这里简化处理
        
        # 保存申请
        request.status = MeetingStatus.DRAFT
        self._meetings[request.id] = request
        self._approvals[request.id] = []
        
        logger.info(
            "创建会议申请",
            meeting_id=str(request.id),
            title=request.title,
            requester=request.requester,
        )
        
        return True, []
    
    def submit_for_approval(self, meeting_id: UUID) -> tuple[bool, str]:
        """提交会议申请进入审批流程
        
        Args:
            meeting_id: 会议 ID
            
        Returns:
            (是否成功, 消息)
        """
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False, "会议申请不存在"
        
        if meeting.status != MeetingStatus.DRAFT:
            return False, f"会议状态不正确: {meeting.status}"
        
        # 验证
        errors = meeting.validate()
        if errors:
            return False, f"验证失败: {'; '.join(errors)}"
        
        # 更新状态
        meeting.status = MeetingStatus.PENDING_APPROVAL
        meeting.current_approval_step = 1
        
        # 创建第一步审批
        first_step = self.approval_chain[0]
        approval = MeetingApproval(
            meeting_id=meeting_id,
            step=first_step.step,
            approver=first_step.approver,
            deadline_at=datetime.utcnow() + timedelta(hours=first_step.timeout_hours),
        )
        self._approvals[meeting_id].append(approval)
        
        logger.info(
            "提交会议审批",
            meeting_id=str(meeting_id),
            first_approver=first_step.approver,
        )
        
        return True, f"已提交审批，等待 {first_step.approver} 审核"
    
    def process_approval(
        self,
        meeting_id: UUID,
        approver: str,
        approved: bool,
        comments: str = "",
        modifications: Optional[dict] = None,
    ) -> tuple[bool, str]:
        """处理审批决策
        
        Args:
            meeting_id: 会议 ID
            approver: 审批者 agent_id
            approved: 是否批准
            comments: 审批意见
            modifications: 修改建议
            
        Returns:
            (是否成功, 消息)
        """
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False, "会议申请不存在"
        
        if meeting.status != MeetingStatus.PENDING_APPROVAL:
            return False, f"会议状态不正确: {meeting.status}"
        
        # 找到当前审批步骤
        approvals = self._approvals.get(meeting_id, [])
        current_approval = None
        for a in approvals:
            if a.approver == approver and a.status == ApprovalStatus.PENDING:
                current_approval = a
                break
        
        if not current_approval:
            return False, f"未找到 {approver} 的待处理审批"
        
        # 更新审批记录
        current_approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        current_approval.comments = comments
        current_approval.modifications = modifications or {}
        current_approval.decided_at = datetime.utcnow()
        
        logger.info(
            "处理会议审批",
            meeting_id=str(meeting_id),
            approver=approver,
            approved=approved,
        )
        
        if not approved:
            # 拒绝 - 终止审批流程
            meeting.status = MeetingStatus.REJECTED
            return True, f"会议申请已被 {approver} 拒绝: {comments}"
        
        # 批准 - 检查是否需要下一步审批
        next_step = self._get_next_approval_step(meeting, current_approval.step)
        
        if next_step:
            # 继续下一步审批
            meeting.current_approval_step = next_step.step
            approval = MeetingApproval(
                meeting_id=meeting_id,
                step=next_step.step,
                approver=next_step.approver,
                deadline_at=datetime.utcnow() + timedelta(hours=next_step.timeout_hours),
            )
            self._approvals[meeting_id].append(approval)
            return True, f"已进入下一审批步骤，等待 {next_step.approver} 审核"
        else:
            # 审批完成
            meeting.status = MeetingStatus.APPROVED
            return True, "会议申请已通过所有审批"
    
    def _get_next_approval_step(
        self,
        meeting: MeetingRequest,
        current_step: int,
    ) -> Optional[ApprovalStepConfig]:
        """获取下一个需要的审批步骤
        
        Args:
            meeting: 会议申请
            current_step: 当前步骤
            
        Returns:
            下一步骤配置，如果没有则返回 None
        """
        for step_config in self.approval_chain:
            if step_config.step <= current_step:
                continue
            
            # 检查条件
            if step_config.condition:
                if not self._check_step_condition(meeting, step_config):
                    continue
            
            return step_config
        
        return None
    
    def _check_step_condition(
        self,
        meeting: MeetingRequest,
        step_config: ApprovalStepConfig,
    ) -> bool:
        """检查审批步骤条件是否满足
        
        Args:
            meeting: 会议申请
            step_config: 步骤配置
            
        Returns:
            条件是否满足
        """
        # 检查关键词触发
        if step_config.trigger_keywords:
            text = f"{meeting.title} {meeting.goal} {' '.join(meeting.agenda)}".lower()
            for keyword in step_config.trigger_keywords:
                if keyword.lower() in text:
                    return True
        
        # 检查风险等级
        if "risk_level == 'H'" in (step_config.condition or ""):
            if meeting.risk_level == RiskLevel.HIGH:
                return True
        
        return False
    
    def schedule_meeting(
        self,
        meeting_id: UUID,
        scheduled_at: datetime,
    ) -> tuple[bool, str]:
        """安排会议时间
        
        Args:
            meeting_id: 会议 ID
            scheduled_at: 安排时间
            
        Returns:
            (是否成功, 消息)
        """
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False, "会议申请不存在"
        
        if meeting.status != MeetingStatus.APPROVED:
            return False, f"会议状态不正确: {meeting.status}"
        
        if scheduled_at <= datetime.utcnow():
            return False, "安排时间必须在未来"
        
        meeting.scheduled_at = scheduled_at
        meeting.status = MeetingStatus.SCHEDULED
        
        logger.info(
            "安排会议",
            meeting_id=str(meeting_id),
            scheduled_at=scheduled_at.isoformat(),
        )
        
        return True, f"会议已安排在 {scheduled_at.isoformat()}"
    
    def start_meeting(self, meeting_id: UUID) -> tuple[bool, str]:
        """开始会议
        
        Args:
            meeting_id: 会议 ID
            
        Returns:
            (是否成功, 消息)
        """
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False, "会议不存在"
        
        if meeting.status not in [MeetingStatus.SCHEDULED, MeetingStatus.APPROVED]:
            return False, f"会议状态不正确: {meeting.status}"
        
        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.started_at = datetime.utcnow()
        
        logger.info("开始会议", meeting_id=str(meeting_id))
        
        return True, "会议已开始"
    
    def end_meeting(
        self,
        meeting_id: UUID,
        minutes: MeetingMinutes,
    ) -> tuple[bool, str]:
        """结束会议并保存纪要
        
        Args:
            meeting_id: 会议 ID
            minutes: 会议纪要
            
        Returns:
            (是否成功, 消息)
        """
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False, "会议不存在"
        
        if meeting.status != MeetingStatus.IN_PROGRESS:
            return False, f"会议状态不正确: {meeting.status}"
        
        # 保存纪要
        minutes.meeting_id = meeting_id
        self._minutes[meeting_id] = minutes
        
        # 更新会议状态
        meeting.status = MeetingStatus.COMPLETED
        meeting.ended_at = datetime.utcnow()
        
        logger.info(
            "结束会议",
            meeting_id=str(meeting_id),
            duration_minutes=(meeting.ended_at - meeting.started_at).seconds // 60,
            action_items_count=len(minutes.action_items),
        )
        
        return True, "会议已结束，纪要已保存"
    
    def cancel_meeting(
        self,
        meeting_id: UUID,
        reason: str,
    ) -> tuple[bool, str]:
        """取消会议
        
        Args:
            meeting_id: 会议 ID
            reason: 取消原因
            
        Returns:
            (是否成功, 消息)
        """
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return False, "会议不存在"
        
        if meeting.status in [MeetingStatus.COMPLETED, MeetingStatus.CANCELLED]:
            return False, f"会议状态不正确: {meeting.status}"
        
        meeting.status = MeetingStatus.CANCELLED
        
        logger.info(
            "取消会议",
            meeting_id=str(meeting_id),
            reason=reason,
        )
        
        return True, f"会议已取消: {reason}"
    
    def get_meeting(self, meeting_id: UUID) -> Optional[MeetingRequest]:
        """获取会议详情"""
        return self._meetings.get(meeting_id)
    
    def get_approvals(self, meeting_id: UUID) -> list[MeetingApproval]:
        """获取会议审批记录"""
        return self._approvals.get(meeting_id, [])
    
    def get_minutes(self, meeting_id: UUID) -> Optional[MeetingMinutes]:
        """获取会议纪要"""
        return self._minutes.get(meeting_id)
    
    def get_pending_meetings(self, approver: str) -> list[MeetingRequest]:
        """获取待某人审批的会议列表
        
        Args:
            approver: 审批者 agent_id
            
        Returns:
            待审批会议列表
        """
        pending = []
        for meeting in self._meetings.values():
            if meeting.status != MeetingStatus.PENDING_APPROVAL:
                continue
            
            approvals = self._approvals.get(meeting.id, [])
            for a in approvals:
                if a.approver == approver and a.status == ApprovalStatus.PENDING:
                    pending.append(meeting)
                    break
        
        return pending
    
    def get_scheduled_meetings(
        self,
        start: datetime,
        end: datetime,
    ) -> list[MeetingRequest]:
        """获取指定时间范围内的已排期会议
        
        Args:
            start: 开始时间
            end: 结束时间
            
        Returns:
            会议列表
        """
        return [
            m for m in self._meetings.values()
            if m.status == MeetingStatus.SCHEDULED
            and m.scheduled_at
            and start <= m.scheduled_at <= end
        ]


# ============================================
# 会议系统工厂
# ============================================

def create_meeting_system(config_path: Optional[str] = None) -> MeetingSystem:
    """创建会议系统实例
    
    Args:
        config_path: 权限配置文件路径
        
    Returns:
        会议系统实例
    """
    system = MeetingSystem()
    if config_path:
        system.load_permissions(config_path)
    return system
