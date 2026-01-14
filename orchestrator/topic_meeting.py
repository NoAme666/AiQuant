# AI Quant Company - Topic-Driven Meeting System
"""
议题驱动会议系统

提供:
- 任何 Agent 可提出议题
- 附议机制 (需要 N 个 Agent 附议才能升级)
- 自动升级会议
- 议题优先级和紧急度管理
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()


class TopicPriority(str, Enum):
    """议题优先级"""
    LOW = "low"           # 低优先级，可延后
    NORMAL = "normal"     # 正常优先级
    HIGH = "high"         # 高优先级，优先处理
    URGENT = "urgent"     # 紧急，需立即处理
    CRITICAL = "critical" # 危急，可能影响交易


class TopicStatus(str, Enum):
    """议题状态"""
    DRAFT = "draft"                     # 草稿
    PROPOSED = "proposed"               # 已提出
    SECONDING = "seconding"             # 附议中
    SCHEDULED = "scheduled"             # 已安排会议
    IN_PROGRESS = "in_progress"         # 会议进行中
    RESOLVED = "resolved"               # 已解决
    REJECTED = "rejected"               # 被拒绝
    EXPIRED = "expired"                 # 已过期


class TopicCategory(str, Enum):
    """议题类别"""
    STRATEGY = "strategy"               # 策略相关
    RISK = "risk"                       # 风险相关
    DATA = "data"                       # 数据相关
    TRADING = "trading"                 # 交易相关
    GOVERNANCE = "governance"           # 治理相关
    PROCESS = "process"                 # 流程相关
    ORGANIZATION = "organization"       # 组织相关
    EMERGENCY = "emergency"             # 紧急事件


@dataclass
class TopicSecond:
    """附议记录"""
    agent_id: str
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MeetingTopic:
    """会议议题"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    title: str = ""
    description: str = ""
    category: TopicCategory = TopicCategory.STRATEGY
    priority: TopicPriority = TopicPriority.NORMAL
    status: TopicStatus = TopicStatus.DRAFT
    
    # 提议者信息
    proposer_id: str = ""
    proposer_department: str = ""
    
    # 附议
    seconds: list[TopicSecond] = field(default_factory=list)
    required_seconds: int = 2  # 需要的附议数
    
    # 会议信息
    suggested_participants: list[str] = field(default_factory=list)
    actual_participants: list[str] = field(default_factory=list)
    scheduled_at: Optional[datetime] = None
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # 结果
    resolution: Optional[str] = None
    action_items: list[dict] = field(default_factory=list)
    
    @property
    def second_count(self) -> int:
        """附议数量"""
        return len(self.seconds)
    
    @property
    def is_seconded(self) -> bool:
        """是否达到附议要求"""
        return self.second_count >= self.required_seconds
    
    def add_second(self, agent_id: str, reason: str) -> bool:
        """添加附议"""
        # 不能自己给自己附议
        if agent_id == self.proposer_id:
            return False
        
        # 检查是否已经附议
        if any(s.agent_id == agent_id for s in self.seconds):
            return False
        
        self.seconds.append(TopicSecond(agent_id=agent_id, reason=reason))
        self.updated_at = datetime.utcnow()
        
        # 检查是否达到附议要求
        if self.is_seconded and self.status == TopicStatus.SECONDING:
            self.status = TopicStatus.SCHEDULED
        
        return True


class TopicMeetingSystem:
    """议题驱动会议系统"""
    
    # 各类别需要的附议数
    CATEGORY_SECOND_REQUIREMENTS = {
        TopicCategory.STRATEGY: 2,
        TopicCategory.RISK: 1,  # 风险议题只需1个附议
        TopicCategory.DATA: 2,
        TopicCategory.TRADING: 2,
        TopicCategory.GOVERNANCE: 3,
        TopicCategory.PROCESS: 2,
        TopicCategory.ORGANIZATION: 3,
        TopicCategory.EMERGENCY: 0,  # 紧急事件无需附议
    }
    
    # 各优先级的过期时间
    PRIORITY_EXPIRY_HOURS = {
        TopicPriority.LOW: 168,      # 7 天
        TopicPriority.NORMAL: 72,    # 3 天
        TopicPriority.HIGH: 24,      # 1 天
        TopicPriority.URGENT: 4,     # 4 小时
        TopicPriority.CRITICAL: 1,   # 1 小时
    }
    
    # 自动升级规则
    AUTO_ESCALATION_RULES = {
        # 如果 N 个高级别 Agent 附议，自动升级优先级
        "lead_seconds_to_high": 2,     # 2个组长附议 -> 升级为 HIGH
        "director_seconds_to_urgent": 1,  # 1个总监附议 -> 升级为 URGENT
    }
    
    # 各类别的默认参与者
    DEFAULT_PARTICIPANTS = {
        TopicCategory.STRATEGY: ["cio", "head_of_research", "skeptic"],
        TopicCategory.RISK: ["cro", "skeptic", "black_swan"],
        TopicCategory.DATA: ["data_quality_auditor", "data_engineering_lead"],
        TopicCategory.TRADING: ["head_trader", "cro", "pm"],
        TopicCategory.GOVERNANCE: ["cgo", "cpo", "chief_of_staff"],
        TopicCategory.PROCESS: ["chief_of_staff", "cgo"],
        TopicCategory.ORGANIZATION: ["cpo", "cgo", "chief_of_staff"],
        TopicCategory.EMERGENCY: ["cro", "cio", "head_trader", "cgo"],
    }
    
    def __init__(self):
        self._topics: dict[str, MeetingTopic] = {}
        logger.info("TopicMeetingSystem 初始化")
    
    def propose_topic(
        self,
        proposer_id: str,
        proposer_department: str,
        title: str,
        description: str,
        category: TopicCategory,
        priority: TopicPriority = TopicPriority.NORMAL,
        suggested_participants: list[str] = None,
    ) -> MeetingTopic:
        """提出议题"""
        required_seconds = self.CATEGORY_SECOND_REQUIREMENTS.get(category, 2)
        expiry_hours = self.PRIORITY_EXPIRY_HOURS.get(priority, 72)
        
        topic = MeetingTopic(
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=TopicStatus.PROPOSED if required_seconds == 0 else TopicStatus.SECONDING,
            proposer_id=proposer_id,
            proposer_department=proposer_department,
            required_seconds=required_seconds,
            suggested_participants=suggested_participants or self.DEFAULT_PARTICIPANTS.get(category, []),
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours),
        )
        
        # 如果不需要附议，直接安排
        if required_seconds == 0:
            topic.status = TopicStatus.SCHEDULED
        
        self._topics[topic.id] = topic
        
        logger.info(
            "议题已提出",
            topic_id=topic.id,
            title=title,
            category=category.value,
            priority=priority.value,
            required_seconds=required_seconds,
        )
        
        return topic
    
    def second_topic(
        self,
        topic_id: str,
        agent_id: str,
        reason: str,
        agent_level: str = "intermediate",  # 用于自动升级判断
    ) -> dict:
        """附议议题"""
        if topic_id not in self._topics:
            return {"success": False, "error": "议题不存在"}
        
        topic = self._topics[topic_id]
        
        if topic.status not in [TopicStatus.SECONDING, TopicStatus.PROPOSED]:
            return {"success": False, "error": f"议题状态不允许附议: {topic.status.value}"}
        
        if not topic.add_second(agent_id, reason):
            return {"success": False, "error": "无法附议（可能已附议过或是提议者本人）"}
        
        # 检查自动升级
        self._check_auto_escalation(topic, agent_level)
        
        result = {
            "success": True,
            "topic_id": topic_id,
            "current_seconds": topic.second_count,
            "required_seconds": topic.required_seconds,
            "is_seconded": topic.is_seconded,
            "new_status": topic.status.value,
        }
        
        if topic.is_seconded:
            result["message"] = "议题已达到附议要求，将安排会议"
            # 安排会议
            self._schedule_meeting(topic)
        
        logger.info(
            "议题已附议",
            topic_id=topic_id,
            agent_id=agent_id,
            current_seconds=topic.second_count,
        )
        
        return result
    
    def _check_auto_escalation(self, topic: MeetingTopic, agent_level: str):
        """检查是否需要自动升级优先级"""
        if agent_level in ["lead", "director"] and topic.priority == TopicPriority.NORMAL:
            lead_seconds = sum(1 for s in topic.seconds if "lead" in s.agent_id.lower())
            if lead_seconds >= self.AUTO_ESCALATION_RULES["lead_seconds_to_high"]:
                topic.priority = TopicPriority.HIGH
                topic.expires_at = datetime.utcnow() + timedelta(
                    hours=self.PRIORITY_EXPIRY_HOURS[TopicPriority.HIGH]
                )
                logger.info("议题自动升级为 HIGH", topic_id=topic.id)
        
        if agent_level == "director" and topic.priority in [TopicPriority.NORMAL, TopicPriority.HIGH]:
            topic.priority = TopicPriority.URGENT
            topic.expires_at = datetime.utcnow() + timedelta(
                hours=self.PRIORITY_EXPIRY_HOURS[TopicPriority.URGENT]
            )
            logger.info("议题自动升级为 URGENT", topic_id=topic.id)
    
    def _schedule_meeting(self, topic: MeetingTopic):
        """安排会议"""
        topic.status = TopicStatus.SCHEDULED
        
        # 根据优先级确定会议时间
        if topic.priority == TopicPriority.CRITICAL:
            topic.scheduled_at = datetime.utcnow() + timedelta(minutes=15)
        elif topic.priority == TopicPriority.URGENT:
            topic.scheduled_at = datetime.utcnow() + timedelta(hours=1)
        elif topic.priority == TopicPriority.HIGH:
            topic.scheduled_at = datetime.utcnow() + timedelta(hours=4)
        else:
            topic.scheduled_at = datetime.utcnow() + timedelta(hours=24)
        
        # 确定参与者
        participants = set(topic.suggested_participants)
        participants.add(topic.proposer_id)
        for second in topic.seconds:
            participants.add(second.agent_id)
        topic.actual_participants = list(participants)
        
        logger.info(
            "会议已安排",
            topic_id=topic.id,
            scheduled_at=topic.scheduled_at.isoformat(),
            participants=topic.actual_participants,
        )
    
    def get_active_topics(
        self,
        category: TopicCategory = None,
        status: TopicStatus = None,
        proposer_id: str = None,
    ) -> list[MeetingTopic]:
        """获取活跃议题"""
        topics = list(self._topics.values())
        
        # 过滤过期的
        now = datetime.utcnow()
        for topic in topics:
            if topic.expires_at and topic.expires_at < now:
                if topic.status in [TopicStatus.SECONDING, TopicStatus.PROPOSED]:
                    topic.status = TopicStatus.EXPIRED
        
        # 应用过滤条件
        if category:
            topics = [t for t in topics if t.category == category]
        if status:
            topics = [t for t in topics if t.status == status]
        if proposer_id:
            topics = [t for t in topics if t.proposer_id == proposer_id]
        
        # 按优先级和时间排序
        priority_order = {
            TopicPriority.CRITICAL: 0,
            TopicPriority.URGENT: 1,
            TopicPriority.HIGH: 2,
            TopicPriority.NORMAL: 3,
            TopicPriority.LOW: 4,
        }
        topics.sort(key=lambda t: (priority_order.get(t.priority, 5), t.created_at))
        
        return topics
    
    def get_topic(self, topic_id: str) -> Optional[MeetingTopic]:
        """获取议题详情"""
        return self._topics.get(topic_id)
    
    def resolve_topic(
        self,
        topic_id: str,
        resolution: str,
        action_items: list[dict] = None,
    ) -> dict:
        """解决议题"""
        if topic_id not in self._topics:
            return {"success": False, "error": "议题不存在"}
        
        topic = self._topics[topic_id]
        topic.status = TopicStatus.RESOLVED
        topic.resolution = resolution
        topic.action_items = action_items or []
        topic.updated_at = datetime.utcnow()
        
        logger.info("议题已解决", topic_id=topic_id)
        
        return {
            "success": True,
            "topic_id": topic_id,
            "resolution": resolution,
            "action_items": action_items,
        }
    
    def reject_topic(
        self,
        topic_id: str,
        reason: str,
        rejector_id: str,
    ) -> dict:
        """拒绝议题"""
        if topic_id not in self._topics:
            return {"success": False, "error": "议题不存在"}
        
        topic = self._topics[topic_id]
        topic.status = TopicStatus.REJECTED
        topic.resolution = f"被 {rejector_id} 拒绝: {reason}"
        topic.updated_at = datetime.utcnow()
        
        logger.info("议题被拒绝", topic_id=topic_id, rejector=rejector_id)
        
        return {
            "success": True,
            "topic_id": topic_id,
            "rejected_by": rejector_id,
            "reason": reason,
        }
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        topics = list(self._topics.values())
        
        status_counts = {}
        for status in TopicStatus:
            status_counts[status.value] = len([t for t in topics if t.status == status])
        
        category_counts = {}
        for category in TopicCategory:
            category_counts[category.value] = len([t for t in topics if t.category == category])
        
        priority_counts = {}
        for priority in TopicPriority:
            priority_counts[priority.value] = len([t for t in topics if t.priority == priority])
        
        return {
            "total_topics": len(topics),
            "by_status": status_counts,
            "by_category": category_counts,
            "by_priority": priority_counts,
            "pending_seconds": len([t for t in topics if t.status == TopicStatus.SECONDING]),
            "scheduled_meetings": len([t for t in topics if t.status == TopicStatus.SCHEDULED]),
        }


# 全局单例
_topic_meeting_system: Optional[TopicMeetingSystem] = None


def get_topic_meeting_system() -> TopicMeetingSystem:
    """获取 TopicMeetingSystem 单例"""
    global _topic_meeting_system
    if _topic_meeting_system is None:
        _topic_meeting_system = TopicMeetingSystem()
    return _topic_meeting_system
