# AI Quant Company - Governance System
"""
治理系统

CGO (Chief Governance Officer) 的核心功能:
- 冻结/解冻 Agent
- 审计日志分析
- 治理告警发布
- 提案审核
- 串谋/滥用检测
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class AlertSeverity(str, Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    RED_ALERT = "red_alert"


class FreezeStatus(str, Enum):
    """冻结状态"""
    ACTIVE = "active"
    LIFTED = "lifted"
    EXPIRED = "expired"


@dataclass
class GovernanceAlert:
    """治理告警"""
    id: str = field(default_factory=lambda: str(uuid4()))
    severity: AlertSeverity = AlertSeverity.INFO
    title: str = ""
    content: str = ""
    target_type: Optional[str] = None  # 'agent', 'department', 'process'
    target_id: Optional[str] = None
    category: Optional[str] = None  # 'collusion', 'budget_abuse', 'process_bypass'
    evidence: dict = field(default_factory=dict)
    recommended_action: Optional[str] = None
    issued_by: str = "cgo"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "content": self.content,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "category": self.category,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
            "issued_by": self.issued_by,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FreezeRecord:
    """冻结记录"""
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    frozen_by: str = "cgo"
    reason: str = ""
    evidence_refs: dict = field(default_factory=dict)
    duration: Optional[timedelta] = None
    expires_at: Optional[datetime] = None
    status: FreezeStatus = FreezeStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GovernanceReport:
    """治理报告"""
    period_start: datetime
    period_end: datetime
    
    # 统计
    total_agents: int = 0
    active_freezes: int = 0
    alerts_issued: int = 0
    proposals_reviewed: int = 0
    
    # 发现的问题
    collusion_suspects: list = field(default_factory=list)
    budget_abuse_suspects: list = field(default_factory=list)
    process_violations: list = field(default_factory=list)
    
    # 建议
    recommendations: list = field(default_factory=list)


class GovernanceSystem:
    """治理系统
    
    提供 CGO 的核心功能:
    - 冻结/解冻 Agent
    - 审计日志分析
    - 治理告警
    - 提案审核
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """初始化治理系统"""
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._pool = None
        
        logger.info("治理系统初始化完成")
    
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
    # 冻结/解冻功能
    # ============================================
    
    async def freeze_agent(
        self,
        agent_id: str,
        reason: str,
        duration_hours: Optional[int] = None,
        evidence_refs: Optional[dict] = None,
        termination_proposal_id: Optional[str] = None,
    ) -> FreezeRecord:
        """冻结 Agent
        
        Args:
            agent_id: 目标 Agent ID
            reason: 冻结原因
            duration_hours: 冻结时长（小时），None 表示无限期
            evidence_refs: 证据引用
            termination_proposal_id: 关联的终止提案 ID
            
        Returns:
            冻结记录
        """
        freeze_id = str(uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=duration_hours) if duration_hours else None
        
        logger.warning(
            "冻结 Agent",
            agent_id=agent_id,
            freeze_id=freeze_id,
            reason=reason,
            duration_hours=duration_hours,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 插入冻结记录
                    await conn.execute("""
                        INSERT INTO agent_freezes (
                            id, agent_id, frozen_by, reason, evidence_refs,
                            termination_proposal_id, duration, expires_at, status, created_at
                        ) VALUES ($1, $2, 'cgo', $3, $4, $5, $6, $7, 'active', $8)
                    """,
                        freeze_id, agent_id, reason, evidence_refs or {},
                        termination_proposal_id,
                        timedelta(hours=duration_hours) if duration_hours else None,
                        expires_at, created_at
                    )
                    
                    # 更新 Agent 状态
                    await conn.execute("""
                        UPDATE agents SET status = 'FROZEN', updated_at = NOW()
                        WHERE id = $1
                    """, agent_id)
                    
                    # 记录事件
                    await conn.execute("""
                        INSERT INTO events (event_type, actor, target_type, target_id, action, details)
                        VALUES ('governance', 'cgo', 'agent', $1, 'freeze', $2)
                    """, agent_id, {"reason": reason, "freeze_id": freeze_id})
                    
            except Exception as e:
                logger.error(f"冻结 Agent 失败: {e}")
        
        return FreezeRecord(
            id=freeze_id,
            agent_id=agent_id,
            frozen_by="cgo",
            reason=reason,
            evidence_refs=evidence_refs or {},
            duration=timedelta(hours=duration_hours) if duration_hours else None,
            expires_at=expires_at,
            status=FreezeStatus.ACTIVE,
            created_at=created_at,
        )
    
    async def unfreeze_agent(
        self,
        agent_id: str,
        lifted_by: str,
        reason: str,
    ) -> bool:
        """解冻 Agent
        
        Args:
            agent_id: Agent ID
            lifted_by: 解冻者
            reason: 解冻原因
            
        Returns:
            是否成功
        """
        logger.info(
            "解冻 Agent",
            agent_id=agent_id,
            lifted_by=lifted_by,
            reason=reason,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 更新冻结记录
                    await conn.execute("""
                        UPDATE agent_freezes
                        SET status = 'lifted', lifted_by = $1, lifted_reason = $2, lifted_at = NOW()
                        WHERE agent_id = $3 AND status = 'active'
                    """, lifted_by, reason, agent_id)
                    
                    # 更新 Agent 状态
                    await conn.execute("""
                        UPDATE agents SET status = 'ACTIVE', updated_at = NOW()
                        WHERE id = $1
                    """, agent_id)
                    
                    return True
                    
            except Exception as e:
                logger.error(f"解冻 Agent 失败: {e}")
        
        return False
    
    async def get_active_freezes(self) -> list[dict]:
        """获取所有活跃的冻结"""
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT * FROM active_freezes
                    """)
                    return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"获取冻结列表失败: {e}")
        return []
    
    # ============================================
    # 治理告警
    # ============================================
    
    async def issue_alert(
        self,
        severity: AlertSeverity,
        title: str,
        content: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        category: Optional[str] = None,
        evidence: Optional[dict] = None,
        recommended_action: Optional[str] = None,
    ) -> GovernanceAlert:
        """发布治理告警
        
        Args:
            severity: 严重程度
            title: 告警标题
            content: 告警内容
            target_type: 目标类型
            target_id: 目标 ID
            category: 类别
            evidence: 证据
            recommended_action: 建议行动
            
        Returns:
            告警对象
        """
        alert = GovernanceAlert(
            severity=severity,
            title=title,
            content=content,
            target_type=target_type,
            target_id=target_id,
            category=category,
            evidence=evidence or {},
            recommended_action=recommended_action,
        )
        
        logger.warning(
            "治理告警",
            severity=severity.value,
            title=title,
            category=category,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO governance_alerts (
                            id, issued_by, severity, title, content,
                            target_type, target_id, category, evidence, recommended_action
                        ) VALUES ($1, 'cgo', $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                        alert.id, severity.value, title, content,
                        target_type, target_id, category, evidence or {}, recommended_action
                    )
            except Exception as e:
                logger.error(f"保存告警失败: {e}")
        
        return alert
    
    async def get_unresolved_alerts(self) -> list[dict]:
        """获取未解决的告警"""
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT * FROM unresolved_alerts
                    """)
                    return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"获取告警失败: {e}")
        return []
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
    ) -> bool:
        """确认告警"""
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE governance_alerts
                        SET acknowledged = TRUE, acknowledged_by = $1, acknowledged_at = NOW()
                        WHERE id = $2
                    """, acknowledged_by, alert_id)
                    return True
            except Exception as e:
                logger.error(f"确认告警失败: {e}")
        return False
    
    async def resolve_alert(
        self,
        alert_id: str,
        resolution: str,
    ) -> bool:
        """解决告警"""
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE governance_alerts
                        SET resolved = TRUE, resolution = $1, resolved_at = NOW()
                        WHERE id = $2
                    """, resolution, alert_id)
                    return True
            except Exception as e:
                logger.error(f"解决告警失败: {e}")
        return False
    
    # ============================================
    # 审计分析
    # ============================================
    
    async def analyze_audit_logs(
        self,
        period_days: int = 7,
    ) -> GovernanceReport:
        """分析审计日志
        
        Args:
            period_days: 分析周期（天）
            
        Returns:
            治理报告
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        report = GovernanceReport(
            period_start=period_start,
            period_end=period_end,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 统计活跃 Agent
                    report.total_agents = await conn.fetchval(
                        "SELECT COUNT(*) FROM agents WHERE status = 'ACTIVE'"
                    ) or 0
                    
                    # 统计活跃冻结
                    report.active_freezes = await conn.fetchval(
                        "SELECT COUNT(*) FROM active_freezes"
                    ) or 0
                    
                    # 统计告警
                    report.alerts_issued = await conn.fetchval("""
                        SELECT COUNT(*) FROM governance_alerts
                        WHERE created_at >= $1
                    """, period_start) or 0
                    
                    # 检测串谋（同一团队互相高评价）
                    report.collusion_suspects = await self._detect_collusion(conn, period_start)
                    
                    # 检测预算滥用
                    report.budget_abuse_suspects = await self._detect_budget_abuse(conn, period_start)
                    
                    # 检测流程违规
                    report.process_violations = await self._detect_process_violations(conn, period_start)
                    
            except Exception as e:
                logger.error(f"审计分析失败: {e}")
        
        return report
    
    async def _detect_collusion(self, conn, since: datetime) -> list[dict]:
        """检测串谋行为"""
        # 检测同一团队成员之间的异常互相支持
        # 例如：互相给高评价、互相批准提案等
        try:
            # 检查同团队批准率是否异常高
            rows = await conn.fetch("""
                SELECT 
                    ga.approver,
                    ga.cycle_id,
                    rc.team,
                    COUNT(*) as approval_count
                FROM gate_approvals ga
                JOIN research_cycles rc ON ga.cycle_id = rc.id
                JOIN agents a ON ga.approver = a.id
                WHERE ga.decision = 'APPROVED'
                  AND ga.created_at >= $1
                  AND a.team = rc.team  -- 同团队
                GROUP BY ga.approver, ga.cycle_id, rc.team
                HAVING COUNT(*) > 3
            """, since)
            
            suspects = []
            for r in rows:
                suspects.append({
                    "type": "same_team_approval",
                    "agent": r["approver"],
                    "team": r["team"],
                    "approval_count": r["approval_count"],
                })
            return suspects
            
        except Exception:
            return []
    
    async def _detect_budget_abuse(self, conn, since: datetime) -> list[dict]:
        """检测预算滥用"""
        try:
            # 检查预算消耗异常高的 Agent
            rows = await conn.fetch("""
                SELECT 
                    tc.agent_id,
                    COUNT(*) as call_count,
                    SUM(tc.actual_cost) as total_cost,
                    AVG(tc.actual_cost) as avg_cost
                FROM tool_calls tc
                WHERE tc.created_at >= $1
                GROUP BY tc.agent_id
                HAVING SUM(tc.actual_cost) > 1000  -- 阈值
                ORDER BY total_cost DESC
            """, since)
            
            suspects = []
            for r in rows:
                suspects.append({
                    "type": "high_budget_usage",
                    "agent": r["agent_id"],
                    "call_count": r["call_count"],
                    "total_cost": r["total_cost"],
                    "avg_cost": float(r["avg_cost"]) if r["avg_cost"] else 0,
                })
            return suspects
            
        except Exception:
            return []
    
    async def _detect_process_violations(self, conn, since: datetime) -> list[dict]:
        """检测流程违规"""
        try:
            # 检查跳过审批的情况
            rows = await conn.fetch("""
                SELECT 
                    e.actor,
                    e.action,
                    e.details,
                    e.created_at
                FROM events e
                WHERE e.event_type = 'process_violation'
                  AND e.created_at >= $1
            """, since)
            
            violations = []
            for r in rows:
                violations.append({
                    "agent": r["actor"],
                    "action": r["action"],
                    "details": r["details"],
                    "at": r["created_at"].isoformat() if r["created_at"] else None,
                })
            return violations
            
        except Exception:
            return []
    
    # ============================================
    # 提案审核
    # ============================================
    
    async def review_hiring_proposal(
        self,
        proposal_id: str,
        approved: bool,
        comments: str,
    ) -> dict:
        """审核招聘提案
        
        Args:
            proposal_id: 提案 ID
            approved: 是否批准
            comments: 审核意见
            
        Returns:
            审核结果
        """
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    new_status = "pending_chairman" if approved else "rejected"
                    review = {
                        "approved": approved,
                        "comments": comments,
                        "at": datetime.utcnow().isoformat(),
                    }
                    
                    await conn.execute("""
                        UPDATE hiring_proposals
                        SET status = $1, cgo_review = $2
                        WHERE id = $3
                    """, new_status, review, proposal_id)
                    
                    return {
                        "success": True,
                        "proposal_id": proposal_id,
                        "new_status": new_status,
                    }
            except Exception as e:
                logger.error(f"审核招聘提案失败: {e}")
        
        return {"success": False, "error": "Database error"}
    
    async def review_termination_proposal(
        self,
        proposal_id: str,
        approved: bool,
        comments: str,
    ) -> dict:
        """审核终止提案
        
        Args:
            proposal_id: 提案 ID
            approved: 是否批准
            comments: 审核意见
            
        Returns:
            审核结果
        """
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 获取提案详情
                    proposal = await conn.fetchrow("""
                        SELECT * FROM termination_proposals WHERE id = $1
                    """, proposal_id)
                    
                    if not proposal:
                        return {"success": False, "error": "Proposal not found"}
                    
                    # 验证是否有足够的独立来源
                    if approved and proposal["independent_sources"] < 2:
                        return {
                            "success": False,
                            "error": "Insufficient independent sources (need >= 2)",
                        }
                    
                    new_status = "pending_chairman" if approved else "rejected"
                    review = {
                        "approved": approved,
                        "comments": comments,
                        "at": datetime.utcnow().isoformat(),
                    }
                    
                    await conn.execute("""
                        UPDATE termination_proposals
                        SET status = $1, cgo_review = $2
                        WHERE id = $3
                    """, new_status, review, proposal_id)
                    
                    return {
                        "success": True,
                        "proposal_id": proposal_id,
                        "new_status": new_status,
                    }
            except Exception as e:
                logger.error(f"审核终止提案失败: {e}")
        
        return {"success": False, "error": "Database error"}
    
    async def get_pending_proposals(self) -> list[dict]:
        """获取待审核的提案"""
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT * FROM pending_proposals
                        ORDER BY created_at
                    """)
                    return [dict(r) for r in rows]
            except Exception as e:
                logger.error(f"获取待审核提案失败: {e}")
        return []


# 单例
_governance_system: Optional[GovernanceSystem] = None


def get_governance_system() -> GovernanceSystem:
    """获取治理系统单例"""
    global _governance_system
    if _governance_system is None:
        _governance_system = GovernanceSystem()
    return _governance_system
