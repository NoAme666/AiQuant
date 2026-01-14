# AI Quant Company - Performance Evaluation System
"""
绩效评估系统

提供:
- Agent KPI 指标定义与追踪
- 职级体系与晋升机制
- 绩效评分计算
- 晋升/降级建议
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()


class JobLevel(str, Enum):
    """职级体系"""
    JUNIOR = "junior"           # 初级
    INTERMEDIATE = "intermediate"  # 中级
    SENIOR = "senior"           # 高级
    LEAD = "lead"              # 组长
    DIRECTOR = "director"       # 总监
    VP = "vp"                  # 副总裁
    C_LEVEL = "c_level"        # C-Level


class PerformanceRating(str, Enum):
    """绩效评级"""
    EXCEPTIONAL = "exceptional"  # 卓越 (5)
    EXCEEDS = "exceeds"         # 超出预期 (4)
    MEETS = "meets"             # 达到预期 (3)
    NEEDS_IMPROVEMENT = "needs_improvement"  # 需改进 (2)
    UNDERPERFORMING = "underperforming"      # 不合格 (1)


@dataclass
class KPIMetric:
    """KPI 指标"""
    name: str
    description: str
    weight: float  # 权重 (0-1)
    target: float  # 目标值
    actual: float = 0.0  # 实际值
    unit: str = ""
    higher_is_better: bool = True
    
    @property
    def achievement_rate(self) -> float:
        """计算达成率"""
        if self.target == 0:
            return 1.0 if self.actual >= 0 else 0.0
        
        rate = self.actual / self.target
        if not self.higher_is_better:
            rate = 2 - rate  # 反转 (如错误率,越低越好)
        return min(max(rate, 0), 2)  # 限制在 0-2 之间


@dataclass
class AgentScorecard:
    """Agent 绩效记录卡"""
    agent_id: str
    period_start: datetime
    period_end: datetime
    job_level: JobLevel
    kpis: list[KPIMetric] = field(default_factory=list)
    qualitative_feedback: list[dict] = field(default_factory=list)
    
    # 计算得出
    overall_score: float = 0.0
    rating: PerformanceRating = PerformanceRating.MEETS
    promotion_eligible: bool = False
    demotion_risk: bool = False
    
    def calculate_score(self) -> float:
        """计算总体绩效分数"""
        if not self.kpis:
            return 0.5
        
        total_weight = sum(kpi.weight for kpi in self.kpis)
        if total_weight == 0:
            return 0.5
        
        weighted_score = sum(
            kpi.weight * kpi.achievement_rate
            for kpi in self.kpis
        ) / total_weight
        
        self.overall_score = round(weighted_score, 3)
        self._determine_rating()
        return self.overall_score
    
    def _determine_rating(self):
        """确定绩效评级"""
        score = self.overall_score
        if score >= 1.5:
            self.rating = PerformanceRating.EXCEPTIONAL
            self.promotion_eligible = True
        elif score >= 1.2:
            self.rating = PerformanceRating.EXCEEDS
            self.promotion_eligible = True
        elif score >= 0.8:
            self.rating = PerformanceRating.MEETS
        elif score >= 0.5:
            self.rating = PerformanceRating.NEEDS_IMPROVEMENT
            self.demotion_risk = True
        else:
            self.rating = PerformanceRating.UNDERPERFORMING
            self.demotion_risk = True


class PerformanceSystem:
    """绩效评估系统"""
    
    # 不同角色的 KPI 模板
    KPI_TEMPLATES = {
        "researcher": [
            KPIMetric("strategy_proposals", "策略提案数量", 0.2, 3, unit="个/周期"),
            KPIMetric("backtest_sharpe_avg", "回测平均夏普", 0.25, 1.5, unit=""),
            KPIMetric("pass_rate_robustness", "鲁棒性闸门通过率", 0.2, 0.6, unit="%"),
            KPIMetric("data_quality_issues", "数据质量问题", 0.15, 0, higher_is_better=False, unit="次"),
            KPIMetric("collaboration_score", "协作评分", 0.1, 0.8, unit=""),
            KPIMetric("memory_contribution", "知识贡献", 0.1, 5, unit="条/周期"),
        ],
        "risk": [
            KPIMetric("risk_events_caught", "风险事件捕获", 0.25, 5, unit="个/周期"),
            KPIMetric("false_positive_rate", "误报率", 0.2, 0.1, higher_is_better=False, unit="%"),
            KPIMetric("veto_accuracy", "否决准确率", 0.25, 0.9, unit="%"),
            KPIMetric("stress_test_coverage", "压力测试覆盖", 0.15, 0.95, unit="%"),
            KPIMetric("response_time", "响应时间", 0.15, 1, higher_is_better=False, unit="小时"),
        ],
        "trader": [
            KPIMetric("execution_slippage", "执行滑点", 0.3, 10, higher_is_better=False, unit="bps"),
            KPIMetric("order_accuracy", "订单准确率", 0.25, 0.99, unit="%"),
            KPIMetric("risk_limit_breaches", "限额违规", 0.2, 0, higher_is_better=False, unit="次"),
            KPIMetric("execution_speed", "执行速度", 0.15, 0.5, higher_is_better=False, unit="秒"),
            KPIMetric("reporting_quality", "汇报质量", 0.1, 0.9, unit=""),
        ],
        "intelligence": [
            KPIMetric("alerts_issued", "预警发布", 0.2, 10, unit="条/周期"),
            KPIMetric("alert_accuracy", "预警准确率", 0.25, 0.7, unit="%"),
            KPIMetric("coverage", "监控覆盖", 0.2, 0.95, unit="%"),
            KPIMetric("response_time", "响应时间", 0.2, 0.5, higher_is_better=False, unit="小时"),
            KPIMetric("actionable_insights", "可操作洞察", 0.15, 5, unit="条/周期"),
        ],
        "governance": [
            KPIMetric("audits_completed", "审计完成", 0.2, 10, unit="次/周期"),
            KPIMetric("violations_detected", "违规检测", 0.2, 3, unit="次/周期"),
            KPIMetric("false_accusations", "误判", 0.2, 0, higher_is_better=False, unit="次"),
            KPIMetric("process_improvement", "流程改进建议", 0.2, 2, unit="条/周期"),
            KPIMetric("documentation_quality", "文档质量", 0.2, 0.9, unit=""),
        ],
        "default": [
            KPIMetric("task_completion", "任务完成率", 0.3, 0.9, unit="%"),
            KPIMetric("quality_score", "质量评分", 0.25, 0.8, unit=""),
            KPIMetric("collaboration", "协作评分", 0.2, 0.8, unit=""),
            KPIMetric("initiative", "主动性", 0.15, 0.7, unit=""),
            KPIMetric("communication", "沟通效率", 0.1, 0.8, unit=""),
        ],
    }
    
    # 晋升要求
    PROMOTION_REQUIREMENTS = {
        JobLevel.JUNIOR: {
            "min_tenure_months": 3,
            "min_rating": PerformanceRating.EXCEEDS,
            "consecutive_good_periods": 2,
        },
        JobLevel.INTERMEDIATE: {
            "min_tenure_months": 6,
            "min_rating": PerformanceRating.EXCEEDS,
            "consecutive_good_periods": 3,
        },
        JobLevel.SENIOR: {
            "min_tenure_months": 12,
            "min_rating": PerformanceRating.EXCEPTIONAL,
            "consecutive_good_periods": 4,
        },
        JobLevel.LEAD: {
            "min_tenure_months": 18,
            "min_rating": PerformanceRating.EXCEPTIONAL,
            "consecutive_good_periods": 4,
            "requires_leadership_demo": True,
        },
    }
    
    def __init__(self):
        self._scorecards: dict[str, list[AgentScorecard]] = {}
        self._agent_levels: dict[str, JobLevel] = {}
        logger.info("PerformanceSystem 初始化")
    
    def get_kpi_template(self, role_type: str) -> list[KPIMetric]:
        """获取角色对应的 KPI 模板"""
        template = self.KPI_TEMPLATES.get(role_type, self.KPI_TEMPLATES["default"])
        # 深拷贝模板
        return [
            KPIMetric(
                name=kpi.name,
                description=kpi.description,
                weight=kpi.weight,
                target=kpi.target,
                unit=kpi.unit,
                higher_is_better=kpi.higher_is_better,
            )
            for kpi in template
        ]
    
    def create_scorecard(
        self,
        agent_id: str,
        role_type: str,
        period_start: datetime,
        period_end: datetime,
        job_level: JobLevel = JobLevel.INTERMEDIATE,
    ) -> AgentScorecard:
        """创建绩效记录卡"""
        kpis = self.get_kpi_template(role_type)
        
        scorecard = AgentScorecard(
            agent_id=agent_id,
            period_start=period_start,
            period_end=period_end,
            job_level=job_level,
            kpis=kpis,
        )
        
        if agent_id not in self._scorecards:
            self._scorecards[agent_id] = []
        self._scorecards[agent_id].append(scorecard)
        
        logger.info("创建绩效记录卡", agent_id=agent_id, role_type=role_type)
        return scorecard
    
    def update_kpi(
        self,
        agent_id: str,
        kpi_name: str,
        actual_value: float,
    ) -> Optional[KPIMetric]:
        """更新 KPI 实际值"""
        if agent_id not in self._scorecards or not self._scorecards[agent_id]:
            logger.warning("未找到 Agent 的绩效记录", agent_id=agent_id)
            return None
        
        current_scorecard = self._scorecards[agent_id][-1]
        
        for kpi in current_scorecard.kpis:
            if kpi.name == kpi_name:
                kpi.actual = actual_value
                logger.info("更新 KPI", agent_id=agent_id, kpi=kpi_name, value=actual_value)
                return kpi
        
        logger.warning("未找到 KPI", agent_id=agent_id, kpi_name=kpi_name)
        return None
    
    def add_feedback(
        self,
        agent_id: str,
        from_agent: str,
        feedback_type: str,  # positive, negative, neutral
        content: str,
        context: Optional[str] = None,
    ):
        """添加定性反馈"""
        if agent_id not in self._scorecards or not self._scorecards[agent_id]:
            return
        
        current_scorecard = self._scorecards[agent_id][-1]
        current_scorecard.qualitative_feedback.append({
            "from_agent": from_agent,
            "type": feedback_type,
            "content": content,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info("添加反馈", agent_id=agent_id, from_agent=from_agent, type=feedback_type)
    
    def calculate_performance(self, agent_id: str) -> Optional[AgentScorecard]:
        """计算 Agent 的绩效"""
        if agent_id not in self._scorecards or not self._scorecards[agent_id]:
            return None
        
        current_scorecard = self._scorecards[agent_id][-1]
        current_scorecard.calculate_score()
        
        logger.info(
            "计算绩效",
            agent_id=agent_id,
            score=current_scorecard.overall_score,
            rating=current_scorecard.rating.value,
        )
        return current_scorecard
    
    def check_promotion_eligibility(
        self,
        agent_id: str,
    ) -> dict:
        """检查晋升资格"""
        if agent_id not in self._scorecards:
            return {"eligible": False, "reason": "无绩效记录"}
        
        scorecards = self._scorecards[agent_id]
        if not scorecards:
            return {"eligible": False, "reason": "无绩效记录"}
        
        current = scorecards[-1]
        current_level = current.job_level
        
        # 已经是最高级
        if current_level == JobLevel.C_LEVEL:
            return {"eligible": False, "reason": "已达最高职级"}
        
        # 获取晋升要求
        requirements = self.PROMOTION_REQUIREMENTS.get(current_level)
        if not requirements:
            return {"eligible": False, "reason": "无晋升路径"}
        
        # 检查连续良好表现
        good_periods = 0
        for sc in reversed(scorecards):
            if sc.rating in [PerformanceRating.EXCEEDS, PerformanceRating.EXCEPTIONAL]:
                good_periods += 1
            else:
                break
        
        required_periods = requirements.get("consecutive_good_periods", 2)
        if good_periods < required_periods:
            return {
                "eligible": False,
                "reason": f"需要连续 {required_periods} 个周期良好表现，当前 {good_periods}",
                "progress": good_periods / required_periods,
            }
        
        return {
            "eligible": True,
            "current_level": current_level.value,
            "next_level": self._get_next_level(current_level).value,
            "performance_history": [
                {"period": sc.period_end.isoformat(), "rating": sc.rating.value}
                for sc in scorecards[-4:]
            ],
        }
    
    def _get_next_level(self, current: JobLevel) -> JobLevel:
        """获取下一职级"""
        level_order = [
            JobLevel.JUNIOR,
            JobLevel.INTERMEDIATE,
            JobLevel.SENIOR,
            JobLevel.LEAD,
            JobLevel.DIRECTOR,
            JobLevel.VP,
            JobLevel.C_LEVEL,
        ]
        try:
            idx = level_order.index(current)
            return level_order[min(idx + 1, len(level_order) - 1)]
        except ValueError:
            return current
    
    def generate_performance_report(self, agent_id: str) -> dict:
        """生成绩效报告"""
        if agent_id not in self._scorecards or not self._scorecards[agent_id]:
            return {"error": "无绩效记录"}
        
        current = self._scorecards[agent_id][-1]
        history = self._scorecards[agent_id]
        
        return {
            "agent_id": agent_id,
            "current_period": {
                "start": current.period_start.isoformat(),
                "end": current.period_end.isoformat(),
                "job_level": current.job_level.value,
                "overall_score": current.overall_score,
                "rating": current.rating.value,
            },
            "kpis": [
                {
                    "name": kpi.name,
                    "description": kpi.description,
                    "target": kpi.target,
                    "actual": kpi.actual,
                    "achievement": round(kpi.achievement_rate * 100, 1),
                    "unit": kpi.unit,
                }
                for kpi in current.kpis
            ],
            "qualitative_feedback": current.qualitative_feedback,
            "history": [
                {
                    "period_end": sc.period_end.isoformat(),
                    "score": sc.overall_score,
                    "rating": sc.rating.value,
                }
                for sc in history[-6:]
            ],
            "promotion_check": self.check_promotion_eligibility(agent_id),
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def get_team_leaderboard(self, team: str = None) -> list[dict]:
        """获取团队排行榜"""
        leaderboard = []
        
        for agent_id, scorecards in self._scorecards.items():
            if not scorecards:
                continue
            current = scorecards[-1]
            leaderboard.append({
                "agent_id": agent_id,
                "job_level": current.job_level.value,
                "score": current.overall_score,
                "rating": current.rating.value,
                "trend": self._calculate_trend(scorecards),
            })
        
        # 按分数排序
        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        return leaderboard
    
    def _calculate_trend(self, scorecards: list[AgentScorecard]) -> str:
        """计算绩效趋势"""
        if len(scorecards) < 2:
            return "stable"
        
        recent = scorecards[-1].overall_score
        previous = scorecards[-2].overall_score
        
        diff = recent - previous
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"


# 全局单例
_performance_system: Optional[PerformanceSystem] = None


def get_performance_system() -> PerformanceSystem:
    """获取 PerformanceSystem 单例"""
    global _performance_system
    if _performance_system is None:
        _performance_system = PerformanceSystem()
    return _performance_system
