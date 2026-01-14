# AI Quant Company - People System
"""
人才管理系统

CPO (Chief People Officer) 的核心功能:
- 组织负载分析
- 招聘提案
- 终止/冻结提案
- Agent 绩效记录
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class ProposalStatus(str, Enum):
    """提案状态"""
    DRAFT = "draft"
    PENDING_CGO = "pending_cgo"
    PENDING_CHAIRMAN = "pending_chairman"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass
class HiringProposal:
    """招聘提案"""
    id: str = field(default_factory=lambda: str(uuid4()))
    role_name: str = ""
    role_id: Optional[str] = None
    department: str = ""
    proposed_by: str = "cpo"
    suggested_by: Optional[str] = None  # 原始建议来源
    justification: list = field(default_factory=list)
    expected_roi: Optional[str] = None
    trial_rules: dict = field(default_factory=dict)
    job_spec: dict = field(default_factory=dict)
    estimated_weekly_budget: int = 0
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role_name": self.role_name,
            "role_id": self.role_id,
            "department": self.department,
            "proposed_by": self.proposed_by,
            "suggested_by": self.suggested_by,
            "justification": self.justification,
            "expected_roi": self.expected_roi,
            "trial_rules": self.trial_rules,
            "job_spec": self.job_spec,
            "estimated_weekly_budget": self.estimated_weekly_budget,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class TerminationProposal:
    """终止/冻结提案"""
    id: str = field(default_factory=lambda: str(uuid4()))
    target_agent: str = ""
    proposed_by: str = "cpo"
    proposal_type: str = "freeze"  # 'freeze' or 'terminate'
    evidence: list = field(default_factory=list)
    negative_feedback_count: int = 0
    independent_sources: int = 0  # 必须 >= 2
    scorecard: dict = field(default_factory=dict)
    justification: str = ""
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_agent": self.target_agent,
            "proposed_by": self.proposed_by,
            "proposal_type": self.proposal_type,
            "evidence": self.evidence,
            "negative_feedback_count": self.negative_feedback_count,
            "independent_sources": self.independent_sources,
            "scorecard": self.scorecard,
            "justification": self.justification,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentScorecard:
    """Agent 绩效记录"""
    agent_id: str
    period_start: datetime
    period_end: datetime
    
    # 产出指标
    experiments_completed: int = 0
    strategies_proposed: int = 0
    strategies_approved: int = 0
    
    # 质量指标
    avg_sharpe: Optional[float] = None
    rejection_rate: float = 0.0
    
    # 协作指标
    meetings_participated: int = 0
    feedback_received: int = 0
    negative_feedback_count: int = 0
    
    # 预算效率
    budget_used: int = 0
    budget_efficiency: float = 0.0  # 产出/预算
    
    # 声誉
    reputation_score: float = 0.5
    reputation_trend: str = "stable"  # 'up', 'down', 'stable'
    
    # 被其他部门点名的次数
    risk_mentions: int = 0
    skeptic_mentions: int = 0
    
    def overall_score(self) -> float:
        """计算综合评分 (0-1)"""
        score = 0.5  # 基础分
        
        # 产出贡献 (+0.2)
        if self.strategies_proposed > 0:
            score += 0.1 * min(self.strategies_approved / self.strategies_proposed, 1)
            score += 0.1 * min(self.experiments_completed / 10, 1)
        
        # 质量贡献 (+0.2)
        if self.avg_sharpe and self.avg_sharpe > 0:
            score += 0.1 * min(self.avg_sharpe / 2, 1)
        score -= 0.1 * min(self.rejection_rate, 1)
        
        # 协作贡献 (+0.1)
        negative_ratio = (
            self.negative_feedback_count / max(self.feedback_received, 1)
            if self.feedback_received > 0 else 0
        )
        score += 0.1 * (1 - negative_ratio)
        
        # 预算效率 (+0.1)
        score += 0.1 * min(self.budget_efficiency, 1)
        
        # 声誉 (+0.2)
        score += 0.2 * self.reputation_score
        
        return max(0, min(1, score))
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "output": {
                "experiments_completed": self.experiments_completed,
                "strategies_proposed": self.strategies_proposed,
                "strategies_approved": self.strategies_approved,
            },
            "quality": {
                "avg_sharpe": self.avg_sharpe,
                "rejection_rate": self.rejection_rate,
            },
            "collaboration": {
                "meetings_participated": self.meetings_participated,
                "feedback_received": self.feedback_received,
                "negative_feedback_count": self.negative_feedback_count,
            },
            "efficiency": {
                "budget_used": self.budget_used,
                "budget_efficiency": self.budget_efficiency,
            },
            "reputation": {
                "score": self.reputation_score,
                "trend": self.reputation_trend,
            },
            "mentions": {
                "risk": self.risk_mentions,
                "skeptic": self.skeptic_mentions,
            },
            "overall_score": self.overall_score(),
        }


@dataclass
class OrgLoadReport:
    """组织负载报告"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # 各部门负载
    department_load: dict = field(default_factory=dict)  # {dept: {agents: N, avg_load: X}}
    
    # 瓶颈分析
    bottlenecks: list = field(default_factory=list)  # [{dept, reason, severity}]
    
    # 人力缺口
    understaffed: list = field(default_factory=list)  # [{dept, shortfall, impact}]
    
    # 冗余分析
    overstaffed: list = field(default_factory=list)  # [{dept, excess, reason}]
    
    # 建议
    recommendations: list = field(default_factory=list)


class PeopleSystem:
    """人才管理系统
    
    提供 CPO 的核心功能:
    - 组织负载分析
    - 招聘提案
    - 终止提案
    - 绩效评估
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """初始化人才系统"""
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._pool = None
        
        logger.info("人才系统初始化完成")
    
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
    # 组织负载分析
    # ============================================
    
    async def analyze_org_load(self) -> OrgLoadReport:
        """分析组织负载
        
        Returns:
            组织负载报告
        """
        report = OrgLoadReport()
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 各部门 Agent 数量和状态
                    dept_stats = await conn.fetch("""
                        SELECT 
                            department,
                            COUNT(*) as agent_count,
                            COUNT(*) FILTER (WHERE status = 'ACTIVE') as active_count
                        FROM agents
                        GROUP BY department
                    """)
                    
                    for row in dept_stats:
                        dept = row["department"]
                        report.department_load[dept] = {
                            "agents": row["agent_count"],
                            "active": row["active_count"],
                            "avg_load": 0.5,  # 默认值，需要更复杂的计算
                        }
                    
                    # 分析预算使用情况
                    budget_stats = await conn.fetch("""
                        SELECT 
                            a.department,
                            SUM(ba.points_spent) as total_spent,
                            SUM(ba.current_period_points) as total_budget
                        FROM agents a
                        LEFT JOIN budget_accounts ba ON ba.id = a.id
                        GROUP BY a.department
                    """)
                    
                    for row in budget_stats:
                        dept = row["department"]
                        if dept in report.department_load:
                            total = row["total_budget"] or 0
                            spent = row["total_spent"] or 0
                            report.department_load[dept]["budget_utilization"] = (
                                spent / total if total > 0 else 0
                            )
                    
                    # 分析待处理任务（瓶颈）
                    pending_by_dept = await conn.fetch("""
                        SELECT 
                            proposer_dept as department,
                            COUNT(*) as pending_count
                        FROM research_cycles
                        WHERE current_state IN ('PENDING_DATA', 'PENDING_BACKTEST', 'PENDING_REVIEW')
                        GROUP BY proposer_dept
                        HAVING COUNT(*) > 5
                    """)
                    
                    for row in pending_by_dept:
                        report.bottlenecks.append({
                            "department": row["department"],
                            "reason": f"High pending count: {row['pending_count']}",
                            "severity": "high" if row["pending_count"] > 10 else "medium",
                        })
                    
            except Exception as e:
                logger.error(f"组织负载分析失败: {e}")
        
        return report
    
    # ============================================
    # 招聘提案
    # ============================================
    
    async def create_hiring_proposal(
        self,
        role_name: str,
        department: str,
        justification: list[str],
        suggested_by: Optional[str] = None,
        expected_roi: Optional[str] = None,
        trial_rules: Optional[dict] = None,
        job_spec: Optional[dict] = None,
        estimated_weekly_budget: int = 100,
    ) -> HiringProposal:
        """创建招聘提案
        
        Args:
            role_name: 角色名称
            department: 所属部门
            justification: 招聘理由列表
            suggested_by: 原始建议来源
            expected_roi: 预期投资回报
            trial_rules: 试用期规则
            job_spec: 岗位规格
            estimated_weekly_budget: 预估周预算
            
        Returns:
            招聘提案
        """
        proposal = HiringProposal(
            role_name=role_name,
            department=department,
            suggested_by=suggested_by,
            justification=justification,
            expected_roi=expected_roi,
            trial_rules=trial_rules or {"duration": "30 days", "success_metrics": []},
            job_spec=job_spec or {},
            estimated_weekly_budget=estimated_weekly_budget,
        )
        
        logger.info(
            "创建招聘提案",
            role=role_name,
            department=department,
            proposal_id=proposal.id,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO hiring_proposals (
                            id, role_name, department, proposed_by, suggested_by,
                            justification, expected_roi, trial_rules, job_spec,
                            estimated_weekly_budget, status
                        ) VALUES ($1, $2, $3, 'cpo', $4, $5, $6, $7, $8, $9, 'draft')
                    """,
                        proposal.id, role_name, department, suggested_by,
                        justification, expected_roi, trial_rules or {},
                        job_spec or {}, estimated_weekly_budget
                    )
            except Exception as e:
                logger.error(f"保存招聘提案失败: {e}")
        
        return proposal
    
    async def submit_hiring_proposal(self, proposal_id: str) -> bool:
        """提交招聘提案给 CGO 审核"""
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE hiring_proposals
                        SET status = 'pending_cgo', submitted_at = NOW()
                        WHERE id = $1 AND status = 'draft'
                    """, proposal_id)
                    return True
            except Exception as e:
                logger.error(f"提交招聘提案失败: {e}")
        return False
    
    # ============================================
    # 终止提案
    # ============================================
    
    async def create_termination_proposal(
        self,
        target_agent: str,
        proposal_type: str = "freeze",
        justification: str = "",
    ) -> TerminationProposal:
        """创建终止/冻结提案
        
        Args:
            target_agent: 目标 Agent ID
            proposal_type: 类型 ('freeze' or 'terminate')
            justification: 理由
            
        Returns:
            终止提案
        """
        # 自动收集证据
        evidence = []
        independent_sources = set()
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 收集负面反馈
                    feedbacks = await conn.fetch("""
                        SELECT 
                            e.actor,
                            a.department as source_dept,
                            e.details
                        FROM events e
                        JOIN agents a ON e.actor = a.id
                        WHERE e.target_id = $1
                          AND e.details->>'sentiment' = 'negative'
                    """, target_agent)
                    
                    for fb in feedbacks:
                        evidence.append({
                            "source": fb["actor"],
                            "source_dept": fb["source_dept"],
                            "type": "negative_feedback",
                            "content": fb["details"],
                        })
                        independent_sources.add(fb["source_dept"])
                    
                    # 获取 scorecard
                    scorecard = await self.get_agent_scorecard(
                        target_agent,
                        period_days=30,
                    )
                    
            except Exception as e:
                logger.error(f"收集证据失败: {e}")
                scorecard = AgentScorecard(
                    agent_id=target_agent,
                    period_start=datetime.utcnow() - timedelta(days=30),
                    period_end=datetime.utcnow(),
                )
        else:
            scorecard = AgentScorecard(
                agent_id=target_agent,
                period_start=datetime.utcnow() - timedelta(days=30),
                period_end=datetime.utcnow(),
            )
        
        proposal = TerminationProposal(
            target_agent=target_agent,
            proposal_type=proposal_type,
            evidence=evidence,
            negative_feedback_count=len(evidence),
            independent_sources=len(independent_sources),
            scorecard=scorecard.to_dict(),
            justification=justification,
        )
        
        logger.info(
            "创建终止提案",
            target=target_agent,
            type=proposal_type,
            independent_sources=len(independent_sources),
            proposal_id=proposal.id,
        )
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO termination_proposals (
                            id, target_agent, proposed_by, proposal_type,
                            evidence, negative_feedback_count, independent_sources,
                            scorecard, justification, status
                        ) VALUES ($1, $2, 'cpo', $3, $4, $5, $6, $7, $8, 'draft')
                    """,
                        proposal.id, target_agent, proposal_type,
                        evidence, len(evidence), len(independent_sources),
                        scorecard.to_dict(), justification
                    )
            except Exception as e:
                logger.error(f"保存终止提案失败: {e}")
        
        return proposal
    
    async def submit_termination_proposal(self, proposal_id: str) -> dict:
        """提交终止提案给 CGO 审核"""
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 验证独立来源数量
                    proposal = await conn.fetchrow("""
                        SELECT independent_sources FROM termination_proposals
                        WHERE id = $1
                    """, proposal_id)
                    
                    if not proposal:
                        return {"success": False, "error": "Proposal not found"}
                    
                    if proposal["independent_sources"] < 2:
                        return {
                            "success": False,
                            "error": f"Insufficient independent sources: {proposal['independent_sources']} < 2",
                        }
                    
                    await conn.execute("""
                        UPDATE termination_proposals
                        SET status = 'pending_cgo', submitted_at = NOW()
                        WHERE id = $1 AND status = 'draft'
                    """, proposal_id)
                    
                    return {"success": True}
                    
            except Exception as e:
                logger.error(f"提交终止提案失败: {e}")
        
        return {"success": False, "error": "Database error"}
    
    # ============================================
    # 绩效评估
    # ============================================
    
    async def get_agent_scorecard(
        self,
        agent_id: str,
        period_days: int = 30,
    ) -> AgentScorecard:
        """获取 Agent 绩效记录
        
        Args:
            agent_id: Agent ID
            period_days: 评估周期（天）
            
        Returns:
            绩效记录
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        scorecard = AgentScorecard(
            agent_id=agent_id,
            period_start=period_start,
            period_end=period_end,
        )
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 实验完成数
                    scorecard.experiments_completed = await conn.fetchval("""
                        SELECT COUNT(*) FROM experiments
                        WHERE owner = $1 AND created_at >= $2 AND status = 'COMPLETED'
                    """, agent_id, period_start) or 0
                    
                    # 策略提议数和批准数
                    strategy_stats = await conn.fetchrow("""
                        SELECT 
                            COUNT(*) as proposed,
                            COUNT(*) FILTER (WHERE current_state = 'APPROVED') as approved,
                            COUNT(*) FILTER (WHERE current_state = 'REJECTED') as rejected
                        FROM research_cycles
                        WHERE proposer = $1 AND created_at >= $2
                    """, agent_id, period_start)
                    
                    if strategy_stats:
                        scorecard.strategies_proposed = strategy_stats["proposed"] or 0
                        scorecard.strategies_approved = strategy_stats["approved"] or 0
                        total = strategy_stats["proposed"] or 0
                        rejected = strategy_stats["rejected"] or 0
                        scorecard.rejection_rate = rejected / total if total > 0 else 0
                    
                    # 平均 Sharpe
                    scorecard.avg_sharpe = await conn.fetchval("""
                        SELECT AVG((metrics->>'sharpe_ratio')::float)
                        FROM experiments
                        WHERE owner = $1 AND created_at >= $2
                          AND metrics->>'sharpe_ratio' IS NOT NULL
                    """, agent_id, period_start)
                    
                    # 会议参与
                    scorecard.meetings_participated = await conn.fetchval("""
                        SELECT COUNT(DISTINCT meeting_id)
                        FROM meeting_participants
                        WHERE agent_id = $1 AND joined_at >= $2
                    """, agent_id, period_start) or 0
                    
                    # 反馈统计
                    feedback_stats = await conn.fetchrow("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE details->>'sentiment' = 'negative') as negative
                        FROM events
                        WHERE target_id = $1 AND event_type = 'feedback' AND created_at >= $2
                    """, agent_id, period_start)
                    
                    if feedback_stats:
                        scorecard.feedback_received = feedback_stats["total"] or 0
                        scorecard.negative_feedback_count = feedback_stats["negative"] or 0
                    
                    # 预算使用
                    budget = await conn.fetchrow("""
                        SELECT points_spent, current_period_points
                        FROM budget_accounts WHERE id = $1
                    """, agent_id)
                    
                    if budget:
                        scorecard.budget_used = budget["points_spent"] or 0
                        total = budget["current_period_points"] or 0
                        if total > 0 and scorecard.experiments_completed > 0:
                            scorecard.budget_efficiency = (
                                scorecard.experiments_completed * 10 / scorecard.budget_used
                                if scorecard.budget_used > 0 else 1.0
                            )
                    
                    # 声誉
                    reputation = await conn.fetchrow("""
                        SELECT overall_score
                        FROM reputation_scores
                        WHERE agent_id = $1
                        ORDER BY calculated_at DESC LIMIT 1
                    """, agent_id)
                    
                    if reputation:
                        scorecard.reputation_score = reputation["overall_score"] or 0.5
                    
                    # Risk/Skeptic 提及
                    scorecard.risk_mentions = await conn.fetchval("""
                        SELECT COUNT(*) FROM events
                        WHERE target_id = $1
                          AND actor IN (SELECT id FROM agents WHERE department = 'risk_guild')
                          AND event_type = 'mention'
                          AND created_at >= $2
                    """, agent_id, period_start) or 0
                    
            except Exception as e:
                logger.error(f"获取 Agent 绩效失败: {e}")
        
        return scorecard
    
    async def get_low_performers(
        self,
        threshold: float = 0.3,
        period_days: int = 30,
    ) -> list[AgentScorecard]:
        """获取低绩效 Agent 列表
        
        Args:
            threshold: 评分阈值
            period_days: 评估周期
            
        Returns:
            低绩效 Agent 列表
        """
        low_performers = []
        
        pool = await self._get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    agents = await conn.fetch("""
                        SELECT id FROM agents WHERE status = 'ACTIVE'
                    """)
                    
                    for agent in agents:
                        scorecard = await self.get_agent_scorecard(
                            agent["id"],
                            period_days,
                        )
                        if scorecard.overall_score() < threshold:
                            low_performers.append(scorecard)
                    
            except Exception as e:
                logger.error(f"获取低绩效 Agent 失败: {e}")
        
        return sorted(low_performers, key=lambda x: x.overall_score())


# 单例
_people_system: Optional[PeopleSystem] = None


def get_people_system() -> PeopleSystem:
    """获取人才系统单例"""
    global _people_system
    if _people_system is None:
        _people_system = PeopleSystem()
    return _people_system
