# AI Quant Company - Feedback Channel System
"""
反馈通道系统

提供:
- 反馈提交（工具需求、流程改进、组织问题）
- 自动提取反馈信号
- 反馈路由与处理
- 反馈统计与报告
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class FeedbackCategory(str, Enum):
    """反馈类别"""
    TOOL_REQUEST = "tool_request"
    PROCESS_IMPROVEMENT = "process_improvement"
    ORG_ISSUE = "org_issue"
    COLLABORATION = "collaboration"
    CAPABILITY_GAP = "capability_gap"


class FeedbackUrgency(str, Enum):
    """紧急程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FeedbackStatus(str, Enum):
    """反馈状态"""
    OPEN = "open"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


@dataclass
class FeedbackEntry:
    """反馈条目"""
    id: str = field(default_factory=lambda: str(uuid4()))
    submitted_by: str = ""
    category: FeedbackCategory = FeedbackCategory.PROCESS_IMPROVEMENT
    
    title: Optional[str] = None
    content: str = ""
    urgency: FeedbackUrgency = FeedbackUrgency.MEDIUM
    
    # 引用
    refs: dict = field(default_factory=dict)  # {"experiment_id": "...", "conversation_id": "..."}
    
    # 来源
    source: str = "manual"  # 'manual', 'auto_extracted'
    extraction_context: Optional[dict] = None
    
    # 处理状态
    status: FeedbackStatus = FeedbackStatus.OPEN
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "submitted_by": self.submitted_by,
            "category": self.category.value,
            "title": self.title,
            "content": self.content,
            "urgency": self.urgency.value,
            "refs": self.refs,
            "source": self.source,
            "status": self.status.value,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


@dataclass
class FeedbackStats:
    """反馈统计"""
    period_start: datetime
    period_end: datetime
    
    # 总量统计
    total_count: int = 0
    by_category: dict = field(default_factory=dict)
    by_urgency: dict = field(default_factory=dict)
    by_status: dict = field(default_factory=dict)
    
    # 来源统计
    manual_count: int = 0
    auto_extracted_count: int = 0
    
    # 处理效率
    avg_resolution_hours: float = 0.0
    open_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "total_count": self.total_count,
            "by_category": self.by_category,
            "by_urgency": self.by_urgency,
            "by_status": self.by_status,
            "source": {
                "manual": self.manual_count,
                "auto_extracted": self.auto_extracted_count,
            },
            "efficiency": {
                "avg_resolution_hours": round(self.avg_resolution_hours, 1),
                "open_count": self.open_count,
            },
        }


class FeedbackChannel:
    """反馈通道
    
    功能:
    - 接收和存储反馈
    - 路由反馈到正确的处理者
    - 统计反馈数据
    """
    
    # 类别到处理者的映射
    CATEGORY_HANDLERS = {
        FeedbackCategory.TOOL_REQUEST: "cto_capability",
        FeedbackCategory.PROCESS_IMPROVEMENT: "chief_of_staff",
        FeedbackCategory.ORG_ISSUE: "cpo",
        FeedbackCategory.COLLABORATION: "chief_of_staff",
        FeedbackCategory.CAPABILITY_GAP: "cto_capability",
    }
    
    def __init__(self, db_url: Optional[str] = None):
        """初始化反馈通道"""
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._pool = None
        
        logger.info("反馈通道初始化完成")
    
    async def _get_pool(self):
        """获取数据库连接池"""
        if self._pool is None:
            try:
                import asyncpg
                db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
                self._pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
            except Exception as e:
                logger.warning(f"数据库连接失败: {e}")
                self._pool = None
        return self._pool
    
    # ============================================
    # 反馈提交
    # ============================================
    
    async def submit_feedback(
        self,
        submitted_by: str,
        category: FeedbackCategory,
        content: str,
        title: Optional[str] = None,
        urgency: FeedbackUrgency = FeedbackUrgency.MEDIUM,
        refs: Optional[dict] = None,
    ) -> FeedbackEntry:
        """提交反馈
        
        Args:
            submitted_by: 提交者 Agent ID
            category: 反馈类别
            content: 反馈内容
            title: 标题（可选）
            urgency: 紧急程度
            refs: 引用（证据）
            
        Returns:
            反馈条目
        """
        entry = FeedbackEntry(
            submitted_by=submitted_by,
            category=category,
            title=title,
            content=content,
            urgency=urgency,
            refs=refs or {},
            source="manual",
        )
        
        logger.info(
            "收到反馈",
            id=entry.id,
            category=category.value,
            submitted_by=submitted_by,
            urgency=urgency.value,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO feedback_entries (
                            id, submitted_by, category, title, content,
                            urgency, refs, source, status
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'manual', 'open')
                    """,
                        entry.id, submitted_by, category.value, title, content,
                        urgency.value, refs or {}
                    )
                    
                    # 记录事件
                    await conn.execute("""
                        INSERT INTO events (event_type, actor, action, details)
                        VALUES ('feedback', $1, 'submit', $2)
                    """, submitted_by, {
                        "feedback_id": entry.id,
                        "category": category.value,
                        "urgency": urgency.value,
                    })
                    
            except Exception as e:
                logger.error(f"保存反馈失败: {e}")
        
        return entry
    
    async def submit_tool_request(
        self,
        submitted_by: str,
        tool_name: str,
        reason: str,
        expected_benefit: str,
        urgency: FeedbackUrgency = FeedbackUrgency.MEDIUM,
    ) -> FeedbackEntry:
        """提交工具需求（简化接口）
        
        这是 Agent 提交工具需求的主要方式
        
        Args:
            submitted_by: 提交者
            tool_name: 工具名称
            reason: 原因
            expected_benefit: 预期收益
            urgency: 紧急程度
            
        Returns:
            反馈条目
        """
        content = f"工具需求: {tool_name}\n原因: {reason}\n预期收益: {expected_benefit}"
        
        return await self.submit_feedback(
            submitted_by=submitted_by,
            category=FeedbackCategory.TOOL_REQUEST,
            title=f"工具需求: {tool_name}",
            content=content,
            urgency=urgency,
            refs={"tool_name": tool_name},
        )
    
    async def submit_process_improvement(
        self,
        submitted_by: str,
        process_name: str,
        issue: str,
        suggestion: str,
        urgency: FeedbackUrgency = FeedbackUrgency.MEDIUM,
    ) -> FeedbackEntry:
        """提交流程改进建议
        
        Args:
            submitted_by: 提交者
            process_name: 流程名称
            issue: 问题描述
            suggestion: 改进建议
            urgency: 紧急程度
            
        Returns:
            反馈条目
        """
        content = f"流程: {process_name}\n问题: {issue}\n建议: {suggestion}"
        
        return await self.submit_feedback(
            submitted_by=submitted_by,
            category=FeedbackCategory.PROCESS_IMPROVEMENT,
            title=f"流程改进: {process_name}",
            content=content,
            urgency=urgency,
            refs={"process_name": process_name},
        )
    
    async def submit_org_issue(
        self,
        submitted_by: str,
        issue_type: str,
        description: str,
        affected_parties: list[str],
        urgency: FeedbackUrgency = FeedbackUrgency.MEDIUM,
    ) -> FeedbackEntry:
        """提交组织问题
        
        Args:
            submitted_by: 提交者
            issue_type: 问题类型
            description: 问题描述
            affected_parties: 受影响方
            urgency: 紧急程度
            
        Returns:
            反馈条目
        """
        content = f"问题类型: {issue_type}\n描述: {description}\n受影响方: {', '.join(affected_parties)}"
        
        return await self.submit_feedback(
            submitted_by=submitted_by,
            category=FeedbackCategory.ORG_ISSUE,
            title=f"组织问题: {issue_type}",
            content=content,
            urgency=urgency,
            refs={"issue_type": issue_type, "affected_parties": affected_parties},
        )
    
    # ============================================
    # 反馈处理
    # ============================================
    
    async def get_pending_feedback(
        self,
        category: Optional[FeedbackCategory] = None,
        handler: Optional[str] = None,
    ) -> list[FeedbackEntry]:
        """获取待处理的反馈
        
        Args:
            category: 按类别筛选
            handler: 按处理者筛选
            
        Returns:
            反馈列表
        """
        pool = await self._get_pool()
        if not pool:
            return []
        
        try:
            async with pool.acquire() as conn:
                query = """
                    SELECT * FROM feedback_entries
                    WHERE status IN ('open', 'in_review')
                """
                params = []
                
                if category:
                    query += f" AND category = ${len(params) + 1}"
                    params.append(category.value)
                
                query += " ORDER BY urgency DESC, created_at ASC"
                
                rows = await conn.fetch(query, *params)
                
                entries = []
                for row in rows:
                    # 如果指定了 handler，筛选对应类别
                    if handler:
                        expected_handler = self.CATEGORY_HANDLERS.get(
                            FeedbackCategory(row["category"])
                        )
                        if expected_handler != handler:
                            continue
                    
                    entry = FeedbackEntry(
                        id=str(row["id"]),
                        submitted_by=row["submitted_by"],
                        category=FeedbackCategory(row["category"]),
                        title=row["title"],
                        content=row["content"],
                        urgency=FeedbackUrgency(row["urgency"]),
                        refs=row["refs"] or {},
                        source=row["source"],
                        status=FeedbackStatus(row["status"]),
                        created_at=row["created_at"],
                    )
                    entries.append(entry)
                
                return entries
                
        except Exception as e:
            logger.error(f"获取待处理反馈失败: {e}")
            return []
    
    async def review_feedback(
        self,
        feedback_id: str,
        reviewed_by: str,
        status: FeedbackStatus,
        notes: str = "",
    ) -> bool:
        """审核反馈
        
        Args:
            feedback_id: 反馈 ID
            reviewed_by: 审核者
            status: 新状态
            notes: 审核备注
            
        Returns:
            是否成功
        """
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE feedback_entries
                        SET status = $1,
                            reviewed_by = $2,
                            review_notes = $3,
                            reviewed_at = NOW()
                        WHERE id = $4
                    """, status.value, reviewed_by, notes, feedback_id)
                    
                    logger.info(
                        "反馈已审核",
                        feedback_id=feedback_id,
                        reviewed_by=reviewed_by,
                        status=status.value,
                    )
                    return True
                    
            except Exception as e:
                logger.error(f"审核反馈失败: {e}")
        return False
    
    # ============================================
    # 反馈路由
    # ============================================
    
    def get_handler_for_category(self, category: FeedbackCategory) -> str:
        """获取类别对应的处理者"""
        return self.CATEGORY_HANDLERS.get(category, "chief_of_staff")
    
    async def route_feedback_to_handler(self, feedback_id: str) -> Optional[str]:
        """将反馈路由到处理者
        
        Args:
            feedback_id: 反馈 ID
            
        Returns:
            处理者 Agent ID
        """
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT category FROM feedback_entries WHERE id = $1
                    """, feedback_id)
                    
                    if row:
                        category = FeedbackCategory(row["category"])
                        handler = self.get_handler_for_category(category)
                        
                        # 更新状态
                        await conn.execute("""
                            UPDATE feedback_entries
                            SET status = 'in_review'
                            WHERE id = $1
                        """, feedback_id)
                        
                        # 通知处理者（发送消息）
                        await conn.execute("""
                            INSERT INTO messages (sender, recipients, content, message_type)
                            VALUES ('system', ARRAY[$1], $2, 'notification')
                        """, handler, f"您有新的反馈需要处理: {feedback_id}")
                        
                        return handler
                        
            except Exception as e:
                logger.error(f"路由反馈失败: {e}")
        
        return None
    
    # ============================================
    # 反馈统计
    # ============================================
    
    async def get_feedback_stats(
        self,
        period_days: int = 7,
    ) -> FeedbackStats:
        """获取反馈统计
        
        Args:
            period_days: 统计周期（天）
            
        Returns:
            反馈统计
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        stats = FeedbackStats(
            period_start=period_start,
            period_end=period_end,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 总量
                    stats.total_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM feedback_entries
                        WHERE created_at >= $1
                    """, period_start) or 0
                    
                    # 按类别统计
                    category_rows = await conn.fetch("""
                        SELECT category, COUNT(*) as count
                        FROM feedback_entries
                        WHERE created_at >= $1
                        GROUP BY category
                    """, period_start)
                    stats.by_category = {r["category"]: r["count"] for r in category_rows}
                    
                    # 按紧急程度统计
                    urgency_rows = await conn.fetch("""
                        SELECT urgency, COUNT(*) as count
                        FROM feedback_entries
                        WHERE created_at >= $1
                        GROUP BY urgency
                    """, period_start)
                    stats.by_urgency = {r["urgency"]: r["count"] for r in urgency_rows}
                    
                    # 按状态统计
                    status_rows = await conn.fetch("""
                        SELECT status, COUNT(*) as count
                        FROM feedback_entries
                        WHERE created_at >= $1
                        GROUP BY status
                    """, period_start)
                    stats.by_status = {r["status"]: r["count"] for r in status_rows}
                    
                    # 来源统计
                    stats.manual_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM feedback_entries
                        WHERE created_at >= $1 AND source = 'manual'
                    """, period_start) or 0
                    
                    stats.auto_extracted_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM feedback_entries
                        WHERE created_at >= $1 AND source = 'auto_extracted'
                    """, period_start) or 0
                    
                    # 未处理数量
                    stats.open_count = await conn.fetchval("""
                        SELECT COUNT(*) FROM feedback_entries
                        WHERE status IN ('open', 'in_review')
                    """) or 0
                    
                    # 平均处理时间
                    avg_hours = await conn.fetchval("""
                        SELECT AVG(EXTRACT(EPOCH FROM (reviewed_at - created_at)) / 3600)
                        FROM feedback_entries
                        WHERE reviewed_at IS NOT NULL AND created_at >= $1
                    """, period_start)
                    stats.avg_resolution_hours = float(avg_hours) if avg_hours else 0.0
                    
            except Exception as e:
                logger.error(f"获取反馈统计失败: {e}")
        
        return stats
    
    # ============================================
    # Agent 义务提醒
    # ============================================
    
    async def remind_support_needs(
        self,
        agent_id: str,
    ) -> dict:
        """提醒 Agent 回答"还有什么需要公司支持的吗？"
        
        返回可选的回答模板
        
        Args:
            agent_id: Agent ID
            
        Returns:
            提醒信息和选项
        """
        return {
            "prompt": "还有什么需要公司支持的吗？请选择以下选项之一回答:",
            "options": [
                {"id": "none", "text": "不需要"},
                {"id": "tool", "text": "需要工具", "follow_up": "请列出需要的工具"},
                {"id": "people", "text": "需要人", "follow_up": "请列出需要的岗位"},
                {"id": "process", "text": "需要制度调整", "follow_up": "请说明需要调整的制度"},
            ],
            "required": True,
            "obligation": "所有 Agent 在与董事长对话时必须回答此问题",
        }


# 单例
_feedback_channel: Optional[FeedbackChannel] = None


def get_feedback_channel() -> FeedbackChannel:
    """获取反馈通道单例"""
    global _feedback_channel
    if _feedback_channel is None:
        _feedback_channel = FeedbackChannel()
    return _feedback_channel
