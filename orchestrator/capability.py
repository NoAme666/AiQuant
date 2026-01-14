# AI Quant Company - Capability System
"""
能力建设系统

CTO* (Capability & Tooling Officer) 的核心功能:
- 工具注册表管理
- 工具使用统计
- 能力缺口分析
- 工具需求提取与优先级排序
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


# 自动提取工具需求的模式
TOOL_REQUEST_PATTERNS = [
    # 中文模式
    r"无法做到[^。]*",
    r"缺乏[^。]*工具",
    r"如果有[^。]*工具[^。]*",
    r"需要[^。]*工具",
    r"目前做不了[^。]*",
    r"能力缺口[^。]*",
    # 英文模式
    r"cannot\s+(?:do|perform|execute)[^.]*",
    r"if\s+we\s+had\s+[^.]*tool[^.]*",
    r"need\s+[^.]*tool",
    r"missing\s+capability[^.]*",
    r"blocked\s+by[^.]*",
    r"limitation[s]?[:\s][^.]*",
]


@dataclass
class ToolUsageStats:
    """工具使用统计"""
    tool_name: str
    period_start: datetime
    period_end: datetime
    
    # 使用量
    total_calls: int = 0
    unique_agents: int = 0
    
    # 成本
    total_cost: int = 0
    avg_cost: float = 0.0
    
    # 成功率
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 1.0
    
    # 频率
    calls_per_day: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "usage": {
                "total_calls": self.total_calls,
                "unique_agents": self.unique_agents,
                "calls_per_day": round(self.calls_per_day, 2),
            },
            "cost": {
                "total": self.total_cost,
                "average": round(self.avg_cost, 2),
            },
            "reliability": {
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "success_rate": round(self.success_rate, 3),
            },
        }


@dataclass
class ToolMention:
    """从对话中提取的工具需求"""
    id: str = field(default_factory=lambda: str(uuid4()))
    source_agent: str = ""
    source_type: str = "conversation"  # 'conversation', 'report', 'feedback'
    source_ref: Optional[str] = None
    
    # 提取的内容
    extracted_text: str = ""
    tool_type: Optional[str] = None  # 推断的工具类型
    
    # 分析
    urgency: str = "medium"
    confidence: float = 0.5
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": {
                "agent": self.source_agent,
                "type": self.source_type,
                "ref": self.source_ref,
            },
            "content": {
                "text": self.extracted_text,
                "tool_type": self.tool_type,
            },
            "analysis": {
                "urgency": self.urgency,
                "confidence": self.confidence,
            },
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ToolRequest:
    """结构化工具需求"""
    id: str = field(default_factory=lambda: str(uuid4()))
    tool_name: str = ""
    tool_description: str = ""
    requested_by: str = ""
    
    # 需求描述
    expected_benefit: str = ""
    use_case: str = ""
    urgency: str = "medium"
    
    # 技术评估
    feasibility_score: Optional[float] = None
    estimated_effort: Optional[str] = None  # 'small', 'medium', 'large', 'epic'
    technical_notes: Optional[str] = None
    
    # 优先级
    priority_score: float = 0.0
    request_count: int = 1  # 被请求次数
    
    # 状态
    status: str = "requested"
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "tool_description": self.tool_description,
            "requested_by": self.requested_by,
            "benefit": self.expected_benefit,
            "use_case": self.use_case,
            "urgency": self.urgency,
            "evaluation": {
                "feasibility": self.feasibility_score,
                "effort": self.estimated_effort,
                "notes": self.technical_notes,
            },
            "priority_score": round(self.priority_score, 2),
            "request_count": self.request_count,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CapabilityGapReport:
    """能力缺口报告"""
    id: str = field(default_factory=lambda: str(uuid4()))
    reported_by: str = "cto_capability"
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    
    # 摘要
    summary: str = ""
    
    # 工具使用统计
    tool_usage_stats: list = field(default_factory=list)
    
    # 最常请求的工具
    most_requested_tools: list = field(default_factory=list)
    
    # 能力缺口
    capability_gaps: list = field(default_factory=list)
    
    # 淘汰候选
    deprecation_candidates: list = field(default_factory=list)
    
    # 招聘建议
    hiring_recommendations: list = field(default_factory=list)
    
    # 开发优先级
    development_priorities: list = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reported_by": self.reported_by,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "summary": self.summary,
            "tool_usage_stats": self.tool_usage_stats,
            "most_requested_tools": self.most_requested_tools,
            "capability_gaps": self.capability_gaps,
            "deprecation_candidates": self.deprecation_candidates,
            "hiring_recommendations": self.hiring_recommendations,
            "development_priorities": self.development_priorities,
            "created_at": self.created_at.isoformat(),
        }


class CapabilitySystem:
    """能力建设系统
    
    提供 CTO* 的核心功能:
    - 工具使用统计
    - 能力缺口分析
    - 工具需求提取
    - 优先级排序
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """初始化能力系统"""
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._pool = None
        
        # 编译正则模式
        self._patterns = [re.compile(p, re.IGNORECASE) for p in TOOL_REQUEST_PATTERNS]
        
        logger.info("能力系统初始化完成")
    
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
    # 工具使用统计
    # ============================================
    
    async def get_tool_usage_stats(
        self,
        period_days: int = 7,
    ) -> list[ToolUsageStats]:
        """获取工具使用统计
        
        Args:
            period_days: 统计周期（天）
            
        Returns:
            各工具的使用统计
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        stats_list = []
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT 
                            tool_name,
                            COUNT(*) as total_calls,
                            COUNT(DISTINCT agent_id) as unique_agents,
                            SUM(actual_cost) as total_cost,
                            AVG(actual_cost) as avg_cost,
                            COUNT(*) FILTER (WHERE status = 'EXECUTED') as success_count,
                            COUNT(*) FILTER (WHERE status = 'FAILED') as failure_count
                        FROM tool_calls
                        WHERE created_at >= $1
                        GROUP BY tool_name
                        ORDER BY total_calls DESC
                    """, period_start)
                    
                    for row in rows:
                        total = row["total_calls"] or 0
                        success = row["success_count"] or 0
                        
                        stats = ToolUsageStats(
                            tool_name=row["tool_name"],
                            period_start=period_start,
                            period_end=period_end,
                            total_calls=total,
                            unique_agents=row["unique_agents"] or 0,
                            total_cost=row["total_cost"] or 0,
                            avg_cost=float(row["avg_cost"]) if row["avg_cost"] else 0,
                            success_count=success,
                            failure_count=row["failure_count"] or 0,
                            success_rate=success / total if total > 0 else 1.0,
                            calls_per_day=total / period_days,
                        )
                        stats_list.append(stats)
                        
            except Exception as e:
                logger.error(f"获取工具统计失败: {e}")
        
        return stats_list
    
    async def get_low_usage_tools(
        self,
        threshold_calls_per_day: float = 0.1,
        period_days: int = 30,
    ) -> list[dict]:
        """获取低使用率工具（淘汰候选）
        
        Args:
            threshold_calls_per_day: 每日调用阈值
            period_days: 统计周期
            
        Returns:
            低使用率工具列表
        """
        stats = await self.get_tool_usage_stats(period_days)
        
        low_usage = []
        for s in stats:
            if s.calls_per_day < threshold_calls_per_day:
                low_usage.append({
                    "tool_name": s.tool_name,
                    "calls_per_day": s.calls_per_day,
                    "total_calls": s.total_calls,
                    "reason": f"Usage below threshold: {s.calls_per_day:.2f} < {threshold_calls_per_day}",
                })
        
        return low_usage
    
    # ============================================
    # 工具需求提取
    # ============================================
    
    def extract_tool_mentions_from_text(
        self,
        text: str,
        source_agent: str,
        source_type: str = "conversation",
        source_ref: Optional[str] = None,
    ) -> list[ToolMention]:
        """从文本中提取工具需求
        
        Args:
            text: 要分析的文本
            source_agent: 来源 Agent
            source_type: 来源类型
            source_ref: 来源引用
            
        Returns:
            提取的工具需求列表
        """
        mentions = []
        
        for pattern in self._patterns:
            for match in pattern.finditer(text):
                extracted = match.group(0).strip()
                
                # 推断工具类型
                tool_type = self._infer_tool_type(extracted)
                
                # 推断紧急程度
                urgency = "high" if any(kw in extracted.lower() for kw in [
                    "urgent", "critical", "blocking", "紧急", "关键", "阻塞"
                ]) else "medium"
                
                mention = ToolMention(
                    source_agent=source_agent,
                    source_type=source_type,
                    source_ref=source_ref,
                    extracted_text=extracted,
                    tool_type=tool_type,
                    urgency=urgency,
                    confidence=0.7,  # 自动提取的置信度
                )
                mentions.append(mention)
        
        return mentions
    
    def _infer_tool_type(self, text: str) -> Optional[str]:
        """推断工具类型"""
        text_lower = text.lower()
        
        # 数据类
        if any(kw in text_lower for kw in ["数据", "data", "行情", "价格", "ohlcv"]):
            return "data"
        
        # 回测类
        if any(kw in text_lower for kw in ["回测", "backtest", "测试"]):
            return "backtest"
        
        # 分析类
        if any(kw in text_lower for kw in ["分析", "指标", "indicator", "analyze"]):
            return "analytics"
        
        # 可视化类
        if any(kw in text_lower for kw in ["可视化", "图表", "plot", "chart", "展示"]):
            return "visualization"
        
        # 监控类
        if any(kw in text_lower for kw in ["监控", "monitor", "告警", "alert"]):
            return "monitoring"
        
        return None
    
    async def extract_tool_mentions_from_conversations(
        self,
        since: Optional[datetime] = None,
    ) -> list[ToolMention]:
        """从对话记录中提取工具需求
        
        Args:
            since: 起始时间
            
        Returns:
            提取的工具需求列表
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        all_mentions = []
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 从消息记录中提取
                    rows = await conn.fetch("""
                        SELECT 
                            m.id,
                            m.sender,
                            m.content
                        FROM messages m
                        WHERE m.created_at >= $1
                          AND m.content IS NOT NULL
                    """, since)
                    
                    for row in rows:
                        mentions = self.extract_tool_mentions_from_text(
                            text=row["content"],
                            source_agent=row["sender"],
                            source_type="conversation",
                            source_ref=str(row["id"]),
                        )
                        all_mentions.extend(mentions)
                    
                    # 保存提取的需求
                    for mention in all_mentions:
                        await conn.execute("""
                            INSERT INTO feedback_entries (
                                id, submitted_by, category, content,
                                urgency, source, extraction_context
                            ) VALUES ($1, $2, 'tool_request', $3, $4, 'auto_extracted', $5)
                        """,
                            mention.id, mention.source_agent, mention.extracted_text,
                            mention.urgency, {
                                "source_type": mention.source_type,
                                "source_ref": mention.source_ref,
                                "confidence": mention.confidence,
                            }
                        )
                    
            except Exception as e:
                logger.error(f"提取工具需求失败: {e}")
        
        logger.info(f"提取了 {len(all_mentions)} 条工具需求")
        return all_mentions
    
    async def extract_tool_mentions_from_reports(
        self,
        since: Optional[datetime] = None,
    ) -> list[ToolMention]:
        """从报告中提取工具需求
        
        主要关注 Limitations 和 Future Work 章节
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        all_mentions = []
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 从实验报告中提取
                    rows = await conn.fetch("""
                        SELECT 
                            e.id,
                            e.owner,
                            e.report
                        FROM experiments e
                        WHERE e.created_at >= $1
                          AND e.report IS NOT NULL
                    """, since)
                    
                    for row in rows:
                        report = row["report"] or {}
                        
                        # 检查 limitations 章节
                        limitations = report.get("limitations", "")
                        if limitations:
                            mentions = self.extract_tool_mentions_from_text(
                                text=str(limitations),
                                source_agent=row["owner"],
                                source_type="report",
                                source_ref=str(row["id"]),
                            )
                            all_mentions.extend(mentions)
                        
                        # 检查 future_work 章节
                        future_work = report.get("future_work", "")
                        if future_work:
                            mentions = self.extract_tool_mentions_from_text(
                                text=str(future_work),
                                source_agent=row["owner"],
                                source_type="report",
                                source_ref=str(row["id"]),
                            )
                            all_mentions.extend(mentions)
                    
            except Exception as e:
                logger.error(f"从报告提取工具需求失败: {e}")
        
        return all_mentions
    
    # ============================================
    # 工具需求管理
    # ============================================
    
    async def submit_tool_request(
        self,
        tool_name: str,
        tool_description: str,
        requested_by: str,
        expected_benefit: str = "",
        use_case: str = "",
        urgency: str = "medium",
    ) -> ToolRequest:
        """提交工具需求
        
        Args:
            tool_name: 工具名称
            tool_description: 工具描述
            requested_by: 请求者
            expected_benefit: 预期收益
            use_case: 使用场景
            urgency: 紧急程度
            
        Returns:
            工具需求
        """
        request = ToolRequest(
            tool_name=tool_name,
            tool_description=tool_description,
            requested_by=requested_by,
            expected_benefit=expected_benefit,
            use_case=use_case,
            urgency=urgency,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 检查是否已有类似请求
                    existing = await conn.fetchrow("""
                        SELECT id, request_count FROM tool_requests
                        WHERE tool_name = $1 AND status != 'deployed'
                    """, tool_name)
                    
                    if existing:
                        # 增加请求计数
                        await conn.execute("""
                            UPDATE tool_requests
                            SET request_count = request_count + 1
                            WHERE id = $1
                        """, existing["id"])
                        request.id = str(existing["id"])
                        request.request_count = existing["request_count"] + 1
                    else:
                        # 创建新请求
                        await conn.execute("""
                            INSERT INTO tool_requests (
                                id, tool_name, tool_description, requested_by,
                                expected_benefit, use_case, urgency
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                            request.id, tool_name, tool_description, requested_by,
                            expected_benefit, use_case, urgency
                        )
                    
            except Exception as e:
                logger.error(f"提交工具需求失败: {e}")
        
        return request
    
    async def evaluate_tool_request(
        self,
        request_id: str,
        feasibility_score: float,
        estimated_effort: str,
        technical_notes: str = "",
    ) -> bool:
        """评估工具需求
        
        Args:
            request_id: 需求 ID
            feasibility_score: 可行性评分 (0-1)
            estimated_effort: 工作量估计
            technical_notes: 技术备注
            
        Returns:
            是否成功
        """
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE tool_requests
                        SET feasibility_score = $1,
                            estimated_effort = $2,
                            technical_notes = $3,
                            status = 'evaluated',
                            evaluated_at = NOW()
                        WHERE id = $4
                    """, feasibility_score, estimated_effort, technical_notes, request_id)
                    return True
            except Exception as e:
                logger.error(f"评估工具需求失败: {e}")
        return False
    
    async def prioritize_tool_requests(self) -> list[ToolRequest]:
        """计算并排序工具需求优先级
        
        优先级公式:
        priority = request_count * 0.3 + urgency_score * 0.3 + feasibility * 0.4
        """
        urgency_scores = {"low": 0.3, "medium": 0.5, "high": 0.8, "critical": 1.0}
        
        requests = []
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT * FROM tool_requests
                        WHERE status IN ('requested', 'evaluated')
                        ORDER BY created_at DESC
                    """)
                    
                    for row in rows:
                        request_count = row["request_count"] or 1
                        urgency = row["urgency"] or "medium"
                        feasibility = row["feasibility_score"] or 0.5
                        
                        # 计算优先级
                        priority = (
                            min(request_count / 10, 1) * 0.3 +
                            urgency_scores.get(urgency, 0.5) * 0.3 +
                            feasibility * 0.4
                        )
                        
                        # 更新优先级
                        await conn.execute("""
                            UPDATE tool_requests SET priority_score = $1 WHERE id = $2
                        """, priority, row["id"])
                        
                        req = ToolRequest(
                            id=str(row["id"]),
                            tool_name=row["tool_name"],
                            tool_description=row["tool_description"],
                            requested_by=row["requested_by"],
                            expected_benefit=row["expected_benefit"] or "",
                            use_case=row["use_case"] or "",
                            urgency=urgency,
                            feasibility_score=feasibility,
                            estimated_effort=row["estimated_effort"],
                            priority_score=priority,
                            request_count=request_count,
                            status=row["status"],
                        )
                        requests.append(req)
                    
            except Exception as e:
                logger.error(f"优先级排序失败: {e}")
        
        # 按优先级排序
        return sorted(requests, key=lambda x: x.priority_score, reverse=True)
    
    # ============================================
    # 能力缺口报告
    # ============================================
    
    async def generate_capability_gap_report(
        self,
        period_days: int = 7,
    ) -> CapabilityGapReport:
        """生成能力缺口报告
        
        Args:
            period_days: 报告周期（天）
            
        Returns:
            能力缺口报告
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        report = CapabilityGapReport(
            period_start=period_start,
            period_end=period_end,
        )
        
        # 1. 获取工具使用统计
        tool_stats = await self.get_tool_usage_stats(period_days)
        report.tool_usage_stats = [s.to_dict() for s in tool_stats]
        
        # 2. 获取最常请求的工具
        prioritized = await self.prioritize_tool_requests()
        report.most_requested_tools = [
            {
                "name": r.tool_name,
                "request_count": r.request_count,
                "urgency": r.urgency,
                "priority_score": r.priority_score,
            }
            for r in prioritized[:10]
        ]
        
        # 3. 获取低使用率工具
        low_usage = await self.get_low_usage_tools(period_days=period_days)
        report.deprecation_candidates = low_usage
        
        # 4. 分析能力缺口
        for req in prioritized[:5]:
            gap = {
                "gap": f"缺乏 {req.tool_name}",
                "impact": req.expected_benefit or "未说明",
                "recommended_action": (
                    f"开发 {req.tool_name}"
                    if req.feasibility_score and req.feasibility_score > 0.5
                    else "需要进一步技术评估"
                ),
            }
            report.capability_gaps.append(gap)
        
        # 5. 生成开发优先级
        for i, req in enumerate(prioritized[:5]):
            report.development_priorities.append({
                "priority": i + 1,
                "item": req.tool_name,
                "justification": f"请求次数: {req.request_count}, 紧急程度: {req.urgency}",
                "effort": req.estimated_effort or "未评估",
            })
        
        # 6. 生成摘要
        report.summary = (
            f"本周期 ({period_start.strftime('%Y-%m-%d')} - {period_end.strftime('%Y-%m-%d')}) "
            f"共有 {len(tool_stats)} 个工具被使用，"
            f"收到 {len(prioritized)} 个工具需求。"
            f"建议优先开发: {', '.join([r.tool_name for r in prioritized[:3]])}。"
            f"建议淘汰: {', '.join([t['tool_name'] for t in low_usage[:3]])}。"
            if low_usage else ""
        )
        
        # 保存报告
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO capability_gap_reports (
                            id, reported_by, period_start, period_end,
                            summary, tool_usage_stats, most_requested_tools,
                            capability_gaps, deprecation_candidates,
                            development_priorities
                        ) VALUES ($1, 'cto_capability', $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                        report.id, period_start, period_end, report.summary,
                        report.tool_usage_stats, report.most_requested_tools,
                        report.capability_gaps, report.deprecation_candidates,
                        report.development_priorities
                    )
            except Exception as e:
                logger.error(f"保存能力缺口报告失败: {e}")
        
        return report


# 单例
_capability_system: Optional[CapabilitySystem] = None


def get_capability_system() -> CapabilitySystem:
    """获取能力系统单例"""
    global _capability_system
    if _capability_system is None:
        _capability_system = CapabilitySystem()
    return _capability_system
