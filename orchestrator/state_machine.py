# AI Quant Company - ResearchCycle 状态机
"""
研究周期状态机

管理策略研究从提出到归档的完整生命周期。
每个策略必须经过所有闸门审核才能进入下一阶段。

状态流转:
IDEA_INTAKE → DATA_GATE → BACKTEST_GATE → ROBUSTNESS_GATE 
    → RISK_SKEPTIC_GATE → IC_REVIEW → BOARD_PACK → BOARD_DECISION → ARCHIVE
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()


# ============================================
# 状态定义
# ============================================

class ResearchCycleState(str, Enum):
    """研究周期状态枚举"""
    IDEA_INTAKE = "IDEA_INTAKE"           # 策略构思录入
    DATA_GATE = "DATA_GATE"               # 数据闸门
    BACKTEST_GATE = "BACKTEST_GATE"       # 回测闸门
    ROBUSTNESS_GATE = "ROBUSTNESS_GATE"   # 鲁棒性闸门
    RISK_SKEPTIC_GATE = "RISK_SKEPTIC_GATE"  # 风控/质疑闸门
    IC_REVIEW = "IC_REVIEW"               # 投委会审议
    BOARD_PACK = "BOARD_PACK"             # 董事会材料准备
    BOARD_DECISION = "BOARD_DECISION"     # 董事会决策
    ARCHIVE = "ARCHIVE"                   # 归档


class GateDecision(str, Enum):
    """闸门决策枚举"""
    PENDING = "PENDING"     # 等待审核
    APPROVED = "APPROVED"   # 通过
    REJECTED = "REJECTED"   # 否决
    RETURNED = "RETURNED"   # 退回补实验


# ============================================
# 状态转移规则
# ============================================

@dataclass
class Transition:
    """状态转移定义"""
    from_state: ResearchCycleState
    to_state: ResearchCycleState
    trigger: str  # 触发条件
    guard: Optional[Callable] = None  # 守卫条件
    on_transition: Optional[Callable] = None  # 转移时执行


# 合法的状态转移
TRANSITIONS: list[Transition] = [
    # 正向流转
    Transition(ResearchCycleState.IDEA_INTAKE, ResearchCycleState.DATA_GATE, 
               "submit_data_request"),
    Transition(ResearchCycleState.DATA_GATE, ResearchCycleState.BACKTEST_GATE, 
               "data_approved"),
    Transition(ResearchCycleState.BACKTEST_GATE, ResearchCycleState.ROBUSTNESS_GATE, 
               "backtest_passed"),
    Transition(ResearchCycleState.ROBUSTNESS_GATE, ResearchCycleState.RISK_SKEPTIC_GATE, 
               "robustness_passed"),
    Transition(ResearchCycleState.RISK_SKEPTIC_GATE, ResearchCycleState.IC_REVIEW, 
               "risk_approved"),
    Transition(ResearchCycleState.IC_REVIEW, ResearchCycleState.BOARD_PACK, 
               "ic_approved"),
    Transition(ResearchCycleState.BOARD_PACK, ResearchCycleState.BOARD_DECISION, 
               "pack_ready"),
    Transition(ResearchCycleState.BOARD_DECISION, ResearchCycleState.ARCHIVE, 
               "board_decided"),
    
    # 退回流转
    Transition(ResearchCycleState.DATA_GATE, ResearchCycleState.IDEA_INTAKE, 
               "data_rejected"),
    Transition(ResearchCycleState.BACKTEST_GATE, ResearchCycleState.DATA_GATE, 
               "backtest_needs_data"),
    Transition(ResearchCycleState.ROBUSTNESS_GATE, ResearchCycleState.BACKTEST_GATE, 
               "robustness_failed"),
    Transition(ResearchCycleState.RISK_SKEPTIC_GATE, ResearchCycleState.ROBUSTNESS_GATE, 
               "risk_returned"),
    Transition(ResearchCycleState.IC_REVIEW, ResearchCycleState.RISK_SKEPTIC_GATE, 
               "ic_returned"),
    Transition(ResearchCycleState.BOARD_DECISION, ResearchCycleState.ROBUSTNESS_GATE, 
               "board_request_more_tests"),
]

# 构建转移映射
TRANSITION_MAP: dict[tuple[ResearchCycleState, str], Transition] = {
    (t.from_state, t.trigger): t for t in TRANSITIONS
}


# ============================================
# 闸门配置
# ============================================

@dataclass
class GateConfig:
    """闸门配置"""
    state: ResearchCycleState
    approvers: list[str]  # 审批者 agent_id 列表
    veto_holders: list[str]  # 拥有否决权的 agent_id
    can_force_retest: list[str]  # 可强制退回的 agent_id
    timeout_hours: int = 24
    required_artifacts: list[str] = field(default_factory=list)


GATE_CONFIGS: dict[ResearchCycleState, GateConfig] = {
    ResearchCycleState.DATA_GATE: GateConfig(
        state=ResearchCycleState.DATA_GATE,
        approvers=["data_quality_auditor"],
        veto_holders=["data_quality_auditor"],
        can_force_retest=[],
        timeout_hours=24,
        required_artifacts=["DATA_QA_REPORT"],
    ),
    ResearchCycleState.BACKTEST_GATE: GateConfig(
        state=ResearchCycleState.BACKTEST_GATE,
        approvers=["backtest_lead"],
        veto_holders=[],
        can_force_retest=[],
        timeout_hours=48,
        required_artifacts=["BACKTEST_REPORT"],
    ),
    ResearchCycleState.ROBUSTNESS_GATE: GateConfig(
        state=ResearchCycleState.ROBUSTNESS_GATE,
        approvers=["robustness_lab", "tcost_modeler"],
        veto_holders=[],
        can_force_retest=[],
        timeout_hours=48,
        required_artifacts=["ROBUSTNESS_REPORT"],
    ),
    ResearchCycleState.RISK_SKEPTIC_GATE: GateConfig(
        state=ResearchCycleState.RISK_SKEPTIC_GATE,
        approvers=["cro", "skeptic"],
        veto_holders=["cro"],
        can_force_retest=["skeptic"],
        timeout_hours=24,
        required_artifacts=["RISK_MEMO"],
    ),
    ResearchCycleState.IC_REVIEW: GateConfig(
        state=ResearchCycleState.IC_REVIEW,
        approvers=["cio", "pm"],
        veto_holders=[],
        can_force_retest=[],
        timeout_hours=24,
        required_artifacts=["IC_MINUTES"],
    ),
    ResearchCycleState.BOARD_DECISION: GateConfig(
        state=ResearchCycleState.BOARD_DECISION,
        approvers=["chairman"],
        veto_holders=["chairman"],
        can_force_retest=["chairman"],
        timeout_hours=72,
        required_artifacts=["BOARD_PACK"],
    ),
}


# ============================================
# 研究周期实体
# ============================================

@dataclass
class ResearchCycle:
    """研究周期实体"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    
    # 状态
    current_state: ResearchCycleState = ResearchCycleState.IDEA_INTAKE
    previous_state: Optional[ResearchCycleState] = None
    
    # 归属
    proposer: str = ""  # agent_id
    team: str = ""      # team_id
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    state_entered_at: datetime = field(default_factory=datetime.utcnow)
    
    # 闸门记录
    gates_passed: dict[str, dict] = field(default_factory=dict)
    
    # 实验与产物
    experiment_ids: list[str] = field(default_factory=list)
    artifact_ids: list[UUID] = field(default_factory=list)
    
    # 最终决策
    final_decision: Optional[GateDecision] = None
    decision_reason: str = ""
    
    # 待处理的退回工单
    pending_rework: Optional[dict] = None


# ============================================
# 闸门审批记录
# ============================================

@dataclass
class GateApproval:
    """闸门审批记录"""
    id: UUID = field(default_factory=uuid4)
    cycle_id: UUID = field(default_factory=uuid4)
    gate: ResearchCycleState = ResearchCycleState.DATA_GATE
    
    approver: str = ""  # agent_id
    decision: GateDecision = GateDecision.PENDING
    
    comments: str = ""
    required_experiments: list[str] = field(default_factory=list)
    veto_used: bool = False
    force_retest_used: bool = False
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None
    deadline_at: Optional[datetime] = None


# ============================================
# 状态机
# ============================================

class ResearchCycleStateMachine:
    """研究周期状态机
    
    管理研究周期的状态转移、闸门审批和生命周期。
    """
    
    def __init__(self, cycle: ResearchCycle):
        self.cycle = cycle
        self._pending_approvals: dict[str, GateApproval] = {}
        self._callbacks: dict[str, list[Callable]] = {}
        
    @property
    def current_state(self) -> ResearchCycleState:
        """当前状态"""
        return self.cycle.current_state
    
    @property
    def is_at_gate(self) -> bool:
        """是否处于闸门状态"""
        return self.current_state in GATE_CONFIGS
    
    @property
    def gate_config(self) -> Optional[GateConfig]:
        """当前闸门配置"""
        return GATE_CONFIGS.get(self.current_state)
    
    def can_transition(self, trigger: str) -> bool:
        """检查是否可以触发转移"""
        key = (self.current_state, trigger)
        if key not in TRANSITION_MAP:
            return False
        
        transition = TRANSITION_MAP[key]
        if transition.guard and not transition.guard(self.cycle):
            return False
            
        return True
    
    def trigger(self, trigger_name: str, **context) -> bool:
        """触发状态转移
        
        Args:
            trigger_name: 触发器名称
            **context: 上下文信息（如审批者、原因等）
            
        Returns:
            是否成功转移
        """
        if not self.can_transition(trigger_name):
            logger.warning(
                "无效的状态转移",
                current_state=self.current_state,
                trigger=trigger_name,
                cycle_id=str(self.cycle.id),
            )
            return False
        
        transition = TRANSITION_MAP[(self.current_state, trigger_name)]
        
        # 记录前状态
        from_state = self.current_state
        
        # 执行转移
        self.cycle.previous_state = from_state
        self.cycle.current_state = transition.to_state
        self.cycle.updated_at = datetime.utcnow()
        self.cycle.state_entered_at = datetime.utcnow()
        
        # 执行转移回调
        if transition.on_transition:
            transition.on_transition(self.cycle, context)
        
        # 触发事件
        self._emit("state_changed", from_state, transition.to_state, context)
        
        logger.info(
            "状态转移",
            cycle_id=str(self.cycle.id),
            from_state=from_state,
            to_state=transition.to_state,
            trigger=trigger_name,
        )
        
        return True
    
    def submit_approval(self, approval: GateApproval) -> bool:
        """提交闸门审批
        
        Args:
            approval: 审批记录
            
        Returns:
            是否成功提交
        """
        if not self.is_at_gate:
            logger.warning("当前不在闸门状态", state=self.current_state)
            return False
        
        gate_config = self.gate_config
        if not gate_config:
            return False
        
        # 验证审批者资格
        if approval.approver not in gate_config.approvers:
            logger.warning(
                "无审批权限",
                approver=approval.approver,
                gate=self.current_state,
            )
            return False
        
        # 检查否决权使用
        if approval.veto_used and approval.approver not in gate_config.veto_holders:
            logger.warning(
                "无否决权",
                approver=approval.approver,
                gate=self.current_state,
            )
            return False
        
        # 检查退回权使用
        if approval.force_retest_used and approval.approver not in gate_config.can_force_retest:
            logger.warning(
                "无退回权",
                approver=approval.approver,
                gate=self.current_state,
            )
            return False
        
        # 记录审批
        approval.decided_at = datetime.utcnow()
        self._pending_approvals[approval.approver] = approval
        
        # 处理审批决策
        return self._process_approval(approval)
    
    def _process_approval(self, approval: GateApproval) -> bool:
        """处理审批决策"""
        gate_config = self.gate_config
        if not gate_config:
            return False
        
        # 否决 - 立即退回
        if approval.decision == GateDecision.REJECTED:
            if approval.veto_used:
                logger.info(
                    "一票否决",
                    approver=approval.approver,
                    gate=self.current_state,
                    reason=approval.comments,
                )
                return self._handle_rejection(approval)
        
        # 退回补实验
        if approval.decision == GateDecision.RETURNED:
            logger.info(
                "退回补实验",
                approver=approval.approver,
                gate=self.current_state,
                required_experiments=approval.required_experiments,
            )
            return self._handle_return(approval)
        
        # 通过 - 检查是否所有审批者都已通过
        if approval.decision == GateDecision.APPROVED:
            all_approved = self._check_all_approved(gate_config)
            if all_approved:
                return self._handle_gate_passed()
        
        return True
    
    def _check_all_approved(self, gate_config: GateConfig) -> bool:
        """检查是否所有必要审批都已通过"""
        for approver in gate_config.approvers:
            if approver not in self._pending_approvals:
                return False
            if self._pending_approvals[approver].decision != GateDecision.APPROVED:
                return False
        return True
    
    def _handle_gate_passed(self) -> bool:
        """处理闸门通过"""
        # 记录通过
        self.cycle.gates_passed[self.current_state.value] = {
            "passed_at": datetime.utcnow().isoformat(),
            "approvals": {
                k: v.decision.value 
                for k, v in self._pending_approvals.items()
            },
        }
        
        # 清空待处理审批
        self._pending_approvals.clear()
        
        # 触发正向转移
        trigger_map = {
            ResearchCycleState.DATA_GATE: "data_approved",
            ResearchCycleState.BACKTEST_GATE: "backtest_passed",
            ResearchCycleState.ROBUSTNESS_GATE: "robustness_passed",
            ResearchCycleState.RISK_SKEPTIC_GATE: "risk_approved",
            ResearchCycleState.IC_REVIEW: "ic_approved",
        }
        
        trigger = trigger_map.get(self.current_state)
        if trigger:
            return self.trigger(trigger)
        
        return True
    
    def _handle_rejection(self, approval: GateApproval) -> bool:
        """处理否决"""
        # 清空待处理审批
        self._pending_approvals.clear()
        
        # 触发退回转移
        trigger_map = {
            ResearchCycleState.DATA_GATE: "data_rejected",
            ResearchCycleState.RISK_SKEPTIC_GATE: "risk_returned",
        }
        
        trigger = trigger_map.get(self.current_state)
        if trigger:
            return self.trigger(
                trigger,
                reason=approval.comments,
                rejected_by=approval.approver,
            )
        
        return True
    
    def _handle_return(self, approval: GateApproval) -> bool:
        """处理退回补实验"""
        # 记录待补实验
        self.cycle.pending_rework = {
            "returned_by": approval.approver,
            "returned_at": datetime.utcnow().isoformat(),
            "required_experiments": approval.required_experiments,
            "comments": approval.comments,
        }
        
        # 清空待处理审批
        self._pending_approvals.clear()
        
        # 触发退回转移
        trigger_map = {
            ResearchCycleState.RISK_SKEPTIC_GATE: "risk_returned",
            ResearchCycleState.IC_REVIEW: "ic_returned",
            ResearchCycleState.BOARD_DECISION: "board_request_more_tests",
        }
        
        trigger = trigger_map.get(self.current_state)
        if trigger:
            return self.trigger(
                trigger,
                required_experiments=approval.required_experiments,
            )
        
        return True
    
    def check_timeout(self) -> bool:
        """检查当前闸门是否超时
        
        Returns:
            是否超时
        """
        if not self.is_at_gate:
            return False
        
        gate_config = self.gate_config
        if not gate_config:
            return False
        
        elapsed = datetime.utcnow() - self.cycle.state_entered_at
        timeout = timedelta(hours=gate_config.timeout_hours)
        
        return elapsed > timeout
    
    def get_pending_approvers(self) -> list[str]:
        """获取待审批的审批者列表"""
        if not self.is_at_gate:
            return []
        
        gate_config = self.gate_config
        if not gate_config:
            return []
        
        return [
            approver
            for approver in gate_config.approvers
            if approver not in self._pending_approvals
        ]
    
    def on(self, event: str, callback: Callable) -> None:
        """注册事件回调
        
        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def _emit(self, event: str, *args, **kwargs) -> None:
        """触发事件"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error("事件回调异常", event=event, error=str(e))


# ============================================
# 状态机工厂
# ============================================

class StateMachineFactory:
    """状态机工厂"""
    
    @staticmethod
    def create(
        name: str,
        proposer: str,
        team: str,
        description: str = "",
    ) -> ResearchCycleStateMachine:
        """创建新的研究周期状态机
        
        Args:
            name: 研究周期名称
            proposer: 提案者 agent_id
            team: 团队 id
            description: 描述
            
        Returns:
            状态机实例
        """
        cycle = ResearchCycle(
            name=name,
            description=description,
            proposer=proposer,
            team=team,
        )
        return ResearchCycleStateMachine(cycle)
    
    @staticmethod
    def from_cycle(cycle: ResearchCycle) -> ResearchCycleStateMachine:
        """从已有周期创建状态机
        
        Args:
            cycle: 研究周期实体
            
        Returns:
            状态机实例
        """
        return ResearchCycleStateMachine(cycle)


# ============================================
# 超时处理器
# ============================================

class TimeoutHandler:
    """超时处理器
    
    定期检查并处理超时的闸门审批。
    """
    
    def __init__(self, notify_callback: Optional[Callable] = None):
        self.notify_callback = notify_callback
    
    async def check_and_handle(
        self,
        state_machines: list[ResearchCycleStateMachine],
    ) -> list[ResearchCycle]:
        """检查并处理超时
        
        Args:
            state_machines: 状态机列表
            
        Returns:
            超时的研究周期列表
        """
        timed_out = []
        
        for sm in state_machines:
            if sm.check_timeout():
                timed_out.append(sm.cycle)
                
                # 发送通知
                if self.notify_callback:
                    pending = sm.get_pending_approvers()
                    await self.notify_callback(
                        cycle=sm.cycle,
                        gate=sm.current_state,
                        pending_approvers=pending,
                    )
                
                logger.warning(
                    "闸门审批超时",
                    cycle_id=str(sm.cycle.id),
                    gate=sm.current_state,
                    pending_approvers=sm.get_pending_approvers(),
                )
        
        return timed_out
