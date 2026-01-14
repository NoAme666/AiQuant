# AI Quant Company - Agent Intention System
"""
Agent 意愿系统

提供:
- 开会意愿检测
- 风险发现触发
- 自主决策机制
- 意愿优先级管理
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class IntentionType(str, Enum):
    """意愿类型"""
    MEETING_REQUEST = "meeting_request"       # 请求开会
    RISK_ALERT = "risk_alert"                 # 风险预警
    STRATEGY_PROPOSAL = "strategy_proposal"   # 策略提案
    DATA_REQUEST = "data_request"             # 数据请求
    TOOL_REQUEST = "tool_request"             # 工具请求
    FEEDBACK = "feedback"                     # 反馈意见
    ESCALATION = "escalation"                 # 升级请求
    COLLABORATION = "collaboration"           # 协作请求
    AUTONOMOUS_ACTION = "autonomous_action"   # 自主行动


class IntentionPriority(str, Enum):
    """意愿优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class IntentionStatus(str, Enum):
    """意愿状态"""
    PENDING = "pending"           # 待处理
    ACKNOWLEDGED = "acknowledged" # 已确认
    IN_PROGRESS = "in_progress"   # 处理中
    APPROVED = "approved"         # 已批准
    REJECTED = "rejected"         # 已拒绝
    COMPLETED = "completed"       # 已完成
    EXPIRED = "expired"           # 已过期


@dataclass
class AgentIntention:
    """Agent 意愿"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    agent_id: str = ""
    agent_name: str = ""
    department: str = ""
    
    intention_type: IntentionType = IntentionType.FEEDBACK
    priority: IntentionPriority = IntentionPriority.NORMAL
    status: IntentionStatus = IntentionStatus.PENDING
    
    title: str = ""
    description: str = ""
    context: dict = field(default_factory=dict)
    
    # 触发条件
    trigger_type: str = ""  # manual, automatic, threshold, schedule
    trigger_data: dict = field(default_factory=dict)
    
    # 目标
    target_agents: list[str] = field(default_factory=list)
    required_approvers: list[str] = field(default_factory=list)
    
    # 自主行动相关
    autonomous_scope: str = ""  # 自主决策范围
    autonomous_approved: bool = False
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # 结果
    response: Optional[str] = None
    action_taken: Optional[str] = None


@dataclass
class RiskTrigger:
    """风险触发器"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    
    # 触发条件
    metric: str = ""  # 监控的指标
    operator: str = ""  # >, <, ==, !=, >=, <=
    threshold: float = 0.0
    
    # 触发后的动作
    action_type: str = ""  # alert, meeting, escalation, autonomous
    target_agents: list[str] = field(default_factory=list)
    priority: IntentionPriority = IntentionPriority.HIGH
    
    # 状态
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


class IntentionSystem:
    """Agent 意愿系统"""
    
    # 不同类型意愿的默认过期时间（小时）
    DEFAULT_EXPIRY = {
        IntentionType.MEETING_REQUEST: 72,
        IntentionType.RISK_ALERT: 4,
        IntentionType.STRATEGY_PROPOSAL: 168,
        IntentionType.DATA_REQUEST: 48,
        IntentionType.TOOL_REQUEST: 168,
        IntentionType.FEEDBACK: 168,
        IntentionType.ESCALATION: 24,
        IntentionType.COLLABORATION: 72,
        IntentionType.AUTONOMOUS_ACTION: 1,
    }
    
    # 自主决策范围定义
    AUTONOMOUS_SCOPES = {
        "research": {
            "description": "研究相关的自主决策",
            "allowed_actions": [
                "request_data",
                "run_backtest",
                "write_memo",
                "propose_strategy",
            ],
            "budget_limit_cp": 100,  # Compute Points 限制
        },
        "risk_monitoring": {
            "description": "风险监控的自主决策",
            "allowed_actions": [
                "issue_alert",
                "request_meeting",
                "pause_strategy",
            ],
            "can_pause_trading": True,
        },
        "trading_execution": {
            "description": "交易执行的自主决策",
            "allowed_actions": [
                "adjust_order",
                "cancel_order",
                "report_anomaly",
            ],
            "max_position_change_pct": 5,
        },
        "intelligence": {
            "description": "情报收集的自主决策",
            "allowed_actions": [
                "issue_alert",
                "update_sentiment",
                "flag_news",
            ],
        },
    }
    
    # 风险触发器预设
    DEFAULT_RISK_TRIGGERS = [
        RiskTrigger(
            name="大额亏损预警",
            description="单日亏损超过阈值时触发",
            metric="daily_pnl_pct",
            operator="<",
            threshold=-5.0,
            action_type="alert",
            target_agents=["cro", "head_trader", "chairman"],
            priority=IntentionPriority.CRITICAL,
        ),
        RiskTrigger(
            name="波动率飙升",
            description="市场波动率异常升高时触发",
            metric="volatility_zscore",
            operator=">",
            threshold=2.5,
            action_type="meeting",
            target_agents=["cro", "cio", "pm"],
            priority=IntentionPriority.HIGH,
        ),
        RiskTrigger(
            name="持仓集中度过高",
            description="单一资产持仓占比过高",
            metric="position_concentration",
            operator=">",
            threshold=0.3,
            action_type="escalation",
            target_agents=["cro", "pm"],
            priority=IntentionPriority.HIGH,
        ),
        RiskTrigger(
            name="恐惧指数极端",
            description="恐惧贪婪指数达到极端值",
            metric="fear_greed_index",
            operator="<",
            threshold=20,
            action_type="alert",
            target_agents=["head_of_intelligence", "cio"],
            priority=IntentionPriority.NORMAL,
        ),
    ]
    
    def __init__(self):
        self._intentions: dict[str, AgentIntention] = {}
        self._triggers: dict[str, RiskTrigger] = {}
        self._agent_intentions: dict[str, list[str]] = {}  # agent_id -> intention_ids
        
        # 初始化默认触发器
        for trigger in self.DEFAULT_RISK_TRIGGERS:
            self._triggers[trigger.id] = trigger
        
        logger.info("IntentionSystem 初始化")
    
    def express_intention(
        self,
        agent_id: str,
        agent_name: str,
        department: str,
        intention_type: IntentionType,
        title: str,
        description: str,
        priority: IntentionPriority = IntentionPriority.NORMAL,
        context: dict = None,
        target_agents: list[str] = None,
        trigger_type: str = "manual",
        autonomous_scope: str = None,
    ) -> AgentIntention:
        """表达意愿"""
        expiry_hours = self.DEFAULT_EXPIRY.get(intention_type, 72)
        
        intention = AgentIntention(
            agent_id=agent_id,
            agent_name=agent_name,
            department=department,
            intention_type=intention_type,
            priority=priority,
            title=title,
            description=description,
            context=context or {},
            target_agents=target_agents or [],
            trigger_type=trigger_type,
            autonomous_scope=autonomous_scope or "",
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours),
        )
        
        # 检查是否可以自主行动
        if intention_type == IntentionType.AUTONOMOUS_ACTION and autonomous_scope:
            intention.autonomous_approved = self._check_autonomous_approval(
                agent_id, autonomous_scope, context
            )
        
        self._intentions[intention.id] = intention
        
        if agent_id not in self._agent_intentions:
            self._agent_intentions[agent_id] = []
        self._agent_intentions[agent_id].append(intention.id)
        
        logger.info(
            "意愿已表达",
            intention_id=intention.id,
            agent_id=agent_id,
            type=intention_type.value,
            priority=priority.value,
        )
        
        return intention
    
    def _check_autonomous_approval(
        self,
        agent_id: str,
        scope: str,
        context: dict,
    ) -> bool:
        """检查是否可以自主批准"""
        if scope not in self.AUTONOMOUS_SCOPES:
            return False
        
        scope_config = self.AUTONOMOUS_SCOPES[scope]
        action = context.get("action")
        
        if action not in scope_config.get("allowed_actions", []):
            return False
        
        # 检查预算限制
        if "budget_limit_cp" in scope_config:
            requested_cp = context.get("compute_points", 0)
            if requested_cp > scope_config["budget_limit_cp"]:
                return False
        
        # 检查持仓变化限制
        if "max_position_change_pct" in scope_config:
            position_change = context.get("position_change_pct", 0)
            if abs(position_change) > scope_config["max_position_change_pct"]:
                return False
        
        return True
    
    def check_risk_triggers(self, metrics: dict) -> list[AgentIntention]:
        """检查风险触发器"""
        triggered_intentions = []
        
        for trigger in self._triggers.values():
            if not trigger.enabled:
                continue
            
            metric_value = metrics.get(trigger.metric)
            if metric_value is None:
                continue
            
            # 检查是否触发
            triggered = False
            if trigger.operator == ">" and metric_value > trigger.threshold:
                triggered = True
            elif trigger.operator == "<" and metric_value < trigger.threshold:
                triggered = True
            elif trigger.operator == ">=" and metric_value >= trigger.threshold:
                triggered = True
            elif trigger.operator == "<=" and metric_value <= trigger.threshold:
                triggered = True
            elif trigger.operator == "==" and metric_value == trigger.threshold:
                triggered = True
            elif trigger.operator == "!=" and metric_value != trigger.threshold:
                triggered = True
            
            if triggered:
                trigger.last_triggered = datetime.utcnow()
                trigger.trigger_count += 1
                
                # 创建风险预警意愿
                intention = self.express_intention(
                    agent_id="system",
                    agent_name="风险监控系统",
                    department="risk_guild",
                    intention_type=IntentionType.RISK_ALERT,
                    title=trigger.name,
                    description=f"{trigger.description}\n当前值: {metric_value}, 阈值: {trigger.threshold}",
                    priority=trigger.priority,
                    context={
                        "trigger_id": trigger.id,
                        "metric": trigger.metric,
                        "value": metric_value,
                        "threshold": trigger.threshold,
                    },
                    target_agents=trigger.target_agents,
                    trigger_type="automatic",
                )
                
                triggered_intentions.append(intention)
                
                logger.warning(
                    "风险触发器触发",
                    trigger_name=trigger.name,
                    metric=trigger.metric,
                    value=metric_value,
                    threshold=trigger.threshold,
                )
        
        return triggered_intentions
    
    def get_intention(self, intention_id: str) -> Optional[AgentIntention]:
        """获取意愿详情"""
        return self._intentions.get(intention_id)
    
    def get_agent_intentions(
        self,
        agent_id: str = None,
        intention_type: IntentionType = None,
        status: IntentionStatus = None,
        priority: IntentionPriority = None,
    ) -> list[AgentIntention]:
        """获取意愿列表"""
        intentions = list(self._intentions.values())
        
        # 更新过期状态
        now = datetime.utcnow()
        for i in intentions:
            if i.expires_at and i.expires_at < now and i.status == IntentionStatus.PENDING:
                i.status = IntentionStatus.EXPIRED
        
        # 应用过滤
        if agent_id:
            intentions = [i for i in intentions if i.agent_id == agent_id]
        if intention_type:
            intentions = [i for i in intentions if i.intention_type == intention_type]
        if status:
            intentions = [i for i in intentions if i.status == status]
        if priority:
            intentions = [i for i in intentions if i.priority == priority]
        
        # 按优先级和时间排序
        priority_order = {
            IntentionPriority.CRITICAL: 0,
            IntentionPriority.URGENT: 1,
            IntentionPriority.HIGH: 2,
            IntentionPriority.NORMAL: 3,
            IntentionPriority.LOW: 4,
        }
        intentions.sort(key=lambda x: (priority_order.get(x.priority, 5), x.created_at))
        
        return intentions
    
    def respond_to_intention(
        self,
        intention_id: str,
        responder_id: str,
        action: str,  # approve, reject, acknowledge
        response: str = None,
    ) -> dict:
        """回应意愿"""
        if intention_id not in self._intentions:
            return {"success": False, "error": "意愿不存在"}
        
        intention = self._intentions[intention_id]
        
        if action == "approve":
            intention.status = IntentionStatus.APPROVED
        elif action == "reject":
            intention.status = IntentionStatus.REJECTED
        elif action == "acknowledge":
            intention.status = IntentionStatus.ACKNOWLEDGED
        else:
            return {"success": False, "error": f"未知操作: {action}"}
        
        intention.response = response
        intention.updated_at = datetime.utcnow()
        
        logger.info(
            "意愿已回应",
            intention_id=intention_id,
            responder=responder_id,
            action=action,
        )
        
        return {
            "success": True,
            "intention_id": intention_id,
            "new_status": intention.status.value,
        }
    
    def complete_intention(
        self,
        intention_id: str,
        action_taken: str,
    ) -> dict:
        """完成意愿"""
        if intention_id not in self._intentions:
            return {"success": False, "error": "意愿不存在"}
        
        intention = self._intentions[intention_id]
        intention.status = IntentionStatus.COMPLETED
        intention.action_taken = action_taken
        intention.updated_at = datetime.utcnow()
        
        return {
            "success": True,
            "intention_id": intention_id,
        }
    
    def get_triggers(self) -> list[RiskTrigger]:
        """获取所有风险触发器"""
        return list(self._triggers.values())
    
    def add_trigger(
        self,
        name: str,
        description: str,
        metric: str,
        operator: str,
        threshold: float,
        action_type: str,
        target_agents: list[str],
        priority: IntentionPriority = IntentionPriority.HIGH,
    ) -> RiskTrigger:
        """添加风险触发器"""
        trigger = RiskTrigger(
            name=name,
            description=description,
            metric=metric,
            operator=operator,
            threshold=threshold,
            action_type=action_type,
            target_agents=target_agents,
            priority=priority,
        )
        
        self._triggers[trigger.id] = trigger
        logger.info("添加风险触发器", trigger_id=trigger.id, name=name)
        
        return trigger
    
    def toggle_trigger(self, trigger_id: str, enabled: bool) -> dict:
        """启用/禁用触发器"""
        if trigger_id not in self._triggers:
            return {"success": False, "error": "触发器不存在"}
        
        self._triggers[trigger_id].enabled = enabled
        return {"success": True, "trigger_id": trigger_id, "enabled": enabled}
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        intentions = list(self._intentions.values())
        triggers = list(self._triggers.values())
        
        return {
            "total_intentions": len(intentions),
            "by_type": {
                t.value: len([i for i in intentions if i.intention_type == t])
                for t in IntentionType
            },
            "by_status": {
                s.value: len([i for i in intentions if i.status == s])
                for s in IntentionStatus
            },
            "by_priority": {
                p.value: len([i for i in intentions if i.priority == p])
                for p in IntentionPriority
            },
            "triggers": {
                "total": len(triggers),
                "enabled": len([t for t in triggers if t.enabled]),
                "total_trigger_count": sum(t.trigger_count for t in triggers),
            },
            "autonomous_approved": len([i for i in intentions if i.autonomous_approved]),
        }


# 全局单例
_intention_system: Optional[IntentionSystem] = None


def get_intention_system() -> IntentionSystem:
    """获取 IntentionSystem 单例"""
    global _intention_system
    if _intention_system is None:
        _intention_system = IntentionSystem()
    return _intention_system
