# AI Quant Company - Agent 意愿系统
"""
Agent 意愿系统

检测 Agent 是否需要：
- 提出议题
- 申请开会
- 请求帮助
- 发出警报
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class TopicType(str, Enum):
    """议题类型"""
    RISK_CONCERN = "risk_concern"           # 风险担忧
    STRATEGY_PROPOSAL = "strategy_proposal"  # 策略提案
    RESOURCE_REQUEST = "resource_request"    # 资源请求
    PROCESS_IMPROVEMENT = "process_improvement"  # 流程改进
    HELP_REQUEST = "help_request"            # 请求帮助
    URGENT_ALERT = "urgent_alert"            # 紧急告警


class TopicStatus(str, Enum):
    """议题状态"""
    RAISED = "raised"              # 已提出
    GATHERING_SUPPORT = "gathering_support"  # 等待附议
    ESCALATED = "escalated"        # 已升级为会议
    RESOLVED = "resolved"          # 已解决
    ARCHIVED = "archived"          # 已归档


class Urgency(str, Enum):
    """紧急程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Topic:
    """议题"""
    id: str = field(default_factory=lambda: str(uuid4()))
    topic_type: TopicType = TopicType.STRATEGY_PROPOSAL
    title: str = ""
    description: str = ""
    urgency: Urgency = Urgency.MEDIUM
    
    # 发起人
    raised_by: str = ""
    department: str = ""
    
    # 附议
    supporters: list[str] = field(default_factory=list)
    support_reasons: dict = field(default_factory=dict)  # {agent_id: reason}
    escalation_threshold: int = 2
    
    # 状态
    status: TopicStatus = TopicStatus.RAISED
    
    # 关联
    meeting_id: Optional[str] = None
    resolution_id: Optional[str] = None
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    escalated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# 意愿检测关键词
INTENTION_KEYWORDS = {
    TopicType.RISK_CONCERN: [
        "风险", "危险", "警告", "异常", "超限", "回撤", "亏损",
        "risk", "warning", "alert", "exceed", "drawdown", "loss",
        "担忧", "担心", "问题", "注意", "小心",
    ],
    TopicType.STRATEGY_PROPOSAL: [
        "策略", "想法", "假设", "发现", "机会", "alpha",
        "strategy", "idea", "hypothesis", "opportunity",
        "建议", "提案", "方案",
    ],
    TopicType.RESOURCE_REQUEST: [
        "需要", "缺少", "不够", "预算", "资源", "工具",
        "need", "lack", "budget", "resource", "tool",
        "申请", "请求",
    ],
    TopicType.PROCESS_IMPROVEMENT: [
        "流程", "效率", "改进", "优化", "问题",
        "process", "efficiency", "improve", "optimize",
        "建议调整", "可以改进",
    ],
    TopicType.HELP_REQUEST: [
        "帮助", "协助", "支持", "困难", "卡住",
        "help", "assist", "support", "stuck", "blocked",
        "不知道", "不确定", "求助",
    ],
    TopicType.URGENT_ALERT: [
        "紧急", "立即", "马上", "严重", "崩溃",
        "urgent", "immediately", "critical", "crash",
        "必须", "警报",
    ],
}


class IntentionDetector:
    """意愿检测器
    
    从 Agent 的思考和对话中检测是否有开会/讨论的意愿
    """
    
    def __init__(self):
        self._pending_topics: dict[str, Topic] = {}  # topic_id -> Topic
        
    def detect_intention(
        self,
        agent_id: str,
        department: str,
        text: str,
    ) -> Optional[Topic]:
        """检测文本中是否有意愿信号
        
        Args:
            agent_id: Agent ID
            department: 部门
            text: 待检测文本
            
        Returns:
            如果检测到意愿，返回议题提案
        """
        text_lower = text.lower()
        
        # 检测各种议题类型的关键词
        detected_type = None
        max_matches = 0
        
        for topic_type, keywords in INTENTION_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > max_matches:
                max_matches = matches
                detected_type = topic_type
        
        # 如果匹配度太低，不创建议题
        if max_matches < 2:
            return None
        
        # 判断紧急程度
        urgency = Urgency.MEDIUM
        if any(kw in text_lower for kw in ["紧急", "urgent", "立即", "immediately", "严重"]):
            urgency = Urgency.URGENT
        elif any(kw in text_lower for kw in ["重要", "important", "尽快", "soon"]):
            urgency = Urgency.HIGH
        elif any(kw in text_lower for kw in ["可以", "建议", "perhaps", "maybe"]):
            urgency = Urgency.LOW
        
        # 创建议题
        topic = Topic(
            topic_type=detected_type,
            title=self._extract_title(text, detected_type),
            description=text[:500],  # 截取前500字
            urgency=urgency,
            raised_by=agent_id,
            department=department,
            escalation_threshold=self._get_threshold(detected_type),
        )
        
        logger.info(
            "检测到意愿信号",
            agent_id=agent_id,
            topic_type=detected_type.value,
            urgency=urgency.value,
        )
        
        return topic
    
    def _extract_title(self, text: str, topic_type: TopicType) -> str:
        """从文本中提取标题"""
        # 简单实现：取第一句话
        first_sentence = text.split("。")[0].split("\n")[0]
        if len(first_sentence) > 50:
            first_sentence = first_sentence[:50] + "..."
        
        type_prefix = {
            TopicType.RISK_CONCERN: "[风险]",
            TopicType.STRATEGY_PROPOSAL: "[提案]",
            TopicType.RESOURCE_REQUEST: "[资源]",
            TopicType.PROCESS_IMPROVEMENT: "[流程]",
            TopicType.HELP_REQUEST: "[求助]",
            TopicType.URGENT_ALERT: "[紧急]",
        }
        
        return f"{type_prefix.get(topic_type, '')} {first_sentence}"
    
    def _get_threshold(self, topic_type: TopicType) -> int:
        """获取升级阈值"""
        thresholds = {
            TopicType.RISK_CONCERN: 1,       # 风险只需1人附议
            TopicType.STRATEGY_PROPOSAL: 2,  # 策略需要2人附议
            TopicType.RESOURCE_REQUEST: 1,   # 资源需要1人
            TopicType.PROCESS_IMPROVEMENT: 2,
            TopicType.HELP_REQUEST: 1,
            TopicType.URGENT_ALERT: 0,       # 紧急无需附议
        }
        return thresholds.get(topic_type, 2)
    
    def check_explicit_intention(self, text: str) -> Optional[dict]:
        """检查是否有明确的议题提出格式
        
        格式：
        [提议讨论]
        议题类型: xxx
        议题标题: xxx
        议题描述: xxx
        """
        if "[提议讨论]" not in text and "[PROPOSE_TOPIC]" not in text:
            return None
        
        # 解析结构化格式
        result = {}
        
        patterns = {
            "topic_type": r"议题类型[：:]\s*(\w+)",
            "title": r"议题标题[：:]\s*(.+)",
            "description": r"议题描述[：:]\s*(.+)",
            "participants": r"建议参与者[：:]\s*(.+)",
            "urgency": r"紧急程度[：:]\s*(\w+)",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                result[key] = match.group(1).strip()
        
        if result.get("title"):
            return result
        
        return None


class TopicManager:
    """议题管理器"""
    
    def __init__(self):
        self._topics: dict[str, Topic] = {}
        self._detector = IntentionDetector()
    
    def raise_topic(self, topic: Topic) -> str:
        """提出议题"""
        self._topics[topic.id] = topic
        logger.info(
            "议题已提出",
            topic_id=topic.id,
            title=topic.title,
            raised_by=topic.raised_by,
        )
        return topic.id
    
    def support_topic(
        self,
        topic_id: str,
        supporter: str,
        reason: str = "",
    ) -> bool:
        """附议
        
        Returns:
            是否触发升级
        """
        topic = self._topics.get(topic_id)
        if not topic:
            return False
        
        if supporter in topic.supporters:
            return False  # 已经附议过
        
        topic.supporters.append(supporter)
        topic.support_reasons[supporter] = reason
        
        logger.info(
            "议题获得附议",
            topic_id=topic_id,
            supporter=supporter,
            current_supporters=len(topic.supporters),
        )
        
        # 检查是否达到升级阈值
        if len(topic.supporters) >= topic.escalation_threshold:
            return self._escalate_topic(topic_id)
        
        return False
    
    def _escalate_topic(self, topic_id: str) -> bool:
        """升级议题为会议"""
        topic = self._topics.get(topic_id)
        if not topic:
            return False
        
        topic.status = TopicStatus.ESCALATED
        topic.escalated_at = datetime.utcnow()
        
        logger.info(
            "议题已升级为会议",
            topic_id=topic_id,
            title=topic.title,
            supporters=topic.supporters,
        )
        
        return True
    
    def get_topic(self, topic_id: str) -> Optional[Topic]:
        """获取议题"""
        return self._topics.get(topic_id)
    
    def get_pending_topics(self) -> list[Topic]:
        """获取待处理议题"""
        return [
            t for t in self._topics.values()
            if t.status in [TopicStatus.RAISED, TopicStatus.GATHERING_SUPPORT]
        ]
    
    def get_escalated_topics(self) -> list[Topic]:
        """获取已升级的议题"""
        return [
            t for t in self._topics.values()
            if t.status == TopicStatus.ESCALATED
        ]
    
    def resolve_topic(self, topic_id: str, resolution_id: str) -> bool:
        """解决议题"""
        topic = self._topics.get(topic_id)
        if not topic:
            return False
        
        topic.status = TopicStatus.RESOLVED
        topic.resolution_id = resolution_id
        topic.resolved_at = datetime.utcnow()
        
        return True


# 全局单例
_topic_manager: Optional[TopicManager] = None
_intention_detector: Optional[IntentionDetector] = None


def get_topic_manager() -> TopicManager:
    """获取议题管理器单例"""
    global _topic_manager
    if _topic_manager is None:
        _topic_manager = TopicManager()
    return _topic_manager


def get_intention_detector() -> IntentionDetector:
    """获取意愿检测器单例"""
    global _intention_detector
    if _intention_detector is None:
        _intention_detector = IntentionDetector()
    return _intention_detector
