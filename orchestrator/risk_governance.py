# AI Quant Company - Risk Strategy Governance
"""
风险策略治理系统

提供:
- 仓位/风控规则管理
- Agent 会议决议机制
- 规则变更流程
- 决议执行与监控
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class RuleType(str, Enum):
    """规则类型"""
    POSITION_LIMIT = "position_limit"           # 仓位限制
    RISK_LIMIT = "risk_limit"                   # 风险限制
    TRADING_LIMIT = "trading_limit"             # 交易限制
    EXPOSURE_LIMIT = "exposure_limit"           # 敞口限制
    LOSS_LIMIT = "loss_limit"                   # 亏损限制
    CONCENTRATION_LIMIT = "concentration_limit" # 集中度限制
    LIQUIDITY_RULE = "liquidity_rule"           # 流动性规则
    STRATEGY_ALLOCATION = "strategy_allocation" # 策略配置


class RuleStatus(str, Enum):
    """规则状态"""
    DRAFT = "draft"           # 草稿
    PROPOSED = "proposed"     # 已提议
    VOTING = "voting"         # 投票中
    APPROVED = "approved"     # 已批准
    REJECTED = "rejected"     # 已拒绝
    ACTIVE = "active"         # 生效中
    SUSPENDED = "suspended"   # 已暂停
    EXPIRED = "expired"       # 已过期


class VoteType(str, Enum):
    """投票类型"""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """投票记录"""
    voter_id: str
    voter_name: str
    department: str
    vote: VoteType
    reason: str
    weight: float = 1.0  # 投票权重
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskRule:
    """风险规则"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    rule_type: RuleType = RuleType.RISK_LIMIT
    status: RuleStatus = RuleStatus.DRAFT
    
    # 规则参数
    parameters: dict = field(default_factory=dict)
    
    # 提议者
    proposer_id: str = ""
    proposer_name: str = ""
    
    # 投票
    votes: list[Vote] = field(default_factory=list)
    required_approval_rate: float = 0.6  # 需要 60% 同意
    required_voters: list[str] = field(default_factory=list)
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    
    # 决议
    resolution: Optional[str] = None
    
    @property
    def approval_rate(self) -> float:
        """计算同意率"""
        if not self.votes:
            return 0.0
        total_weight = sum(v.weight for v in self.votes if v.vote != VoteType.ABSTAIN)
        if total_weight == 0:
            return 0.0
        approve_weight = sum(v.weight for v in self.votes if v.vote == VoteType.APPROVE)
        return approve_weight / total_weight
    
    @property
    def is_approved(self) -> bool:
        """是否已批准"""
        return self.approval_rate >= self.required_approval_rate
    
    def add_vote(self, vote: Vote) -> bool:
        """添加投票"""
        # 检查是否已投票
        if any(v.voter_id == vote.voter_id for v in self.votes):
            return False
        self.votes.append(vote)
        self.updated_at = datetime.utcnow()
        return True


@dataclass
class GovernanceDecision:
    """治理决议"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    rule_id: str = ""
    decision_type: str = ""  # approve, reject, modify, suspend
    
    # 参与者
    participants: list[str] = field(default_factory=list)
    
    # 决议内容
    summary: str = ""
    rationale: str = ""
    conditions: list[str] = field(default_factory=list)
    
    # 时间
    decided_at: datetime = field(default_factory=datetime.utcnow)
    
    # 执行
    executed: bool = False
    executed_at: Optional[datetime] = None
    execution_result: Optional[str] = None


class RiskGovernanceSystem:
    """风险策略治理系统"""
    
    # 各规则类型需要的投票者
    REQUIRED_VOTERS_BY_TYPE = {
        RuleType.POSITION_LIMIT: ["cro", "pm", "cio"],
        RuleType.RISK_LIMIT: ["cro", "skeptic", "cio"],
        RuleType.TRADING_LIMIT: ["head_trader", "cro", "pm"],
        RuleType.EXPOSURE_LIMIT: ["cro", "pm", "black_swan"],
        RuleType.LOSS_LIMIT: ["cro", "cio", "chairman"],
        RuleType.CONCENTRATION_LIMIT: ["cro", "pm", "cio"],
        RuleType.LIQUIDITY_RULE: ["head_trader", "cro", "pm"],
        RuleType.STRATEGY_ALLOCATION: ["cio", "pm", "head_of_research"],
    }
    
    # 投票权重
    VOTE_WEIGHTS = {
        "chairman": 3.0,
        "cro": 2.0,
        "cio": 2.0,
        "pm": 1.5,
        "head_trader": 1.5,
        "skeptic": 1.5,
        "head_of_research": 1.0,
        "black_swan": 1.0,
        "default": 1.0,
    }
    
    # 默认风控规则
    DEFAULT_RULES = [
        {
            "name": "单一资产仓位上限",
            "description": "任何单一资产的仓位不得超过总资产的 30%",
            "rule_type": RuleType.CONCENTRATION_LIMIT,
            "parameters": {
                "max_single_asset_pct": 30,
                "applies_to": "all",
            },
        },
        {
            "name": "日内最大亏损限制",
            "description": "单日亏损超过 5% 时强制平仓",
            "rule_type": RuleType.LOSS_LIMIT,
            "parameters": {
                "max_daily_loss_pct": 5,
                "action": "force_close",
            },
        },
        {
            "name": "最大杠杆限制",
            "description": "总杠杆不得超过 3 倍",
            "rule_type": RuleType.RISK_LIMIT,
            "parameters": {
                "max_leverage": 3,
                "margin_call_leverage": 2.5,
            },
        },
        {
            "name": "流动性要求",
            "description": "只交易日均交易量前 50 的资产",
            "rule_type": RuleType.LIQUIDITY_RULE,
            "parameters": {
                "min_volume_rank": 50,
                "min_daily_volume_usd": 10000000,
            },
        },
    ]
    
    def __init__(self):
        self._rules: dict[str, RiskRule] = {}
        self._decisions: dict[str, GovernanceDecision] = {}
        self._active_rules: dict[str, RiskRule] = {}
        
        # 初始化默认规则
        self._init_default_rules()
        
        logger.info("RiskGovernanceSystem 初始化")
    
    def _init_default_rules(self):
        """初始化默认规则"""
        for rule_config in self.DEFAULT_RULES:
            rule = RiskRule(
                name=rule_config["name"],
                description=rule_config["description"],
                rule_type=rule_config["rule_type"],
                parameters=rule_config["parameters"],
                status=RuleStatus.ACTIVE,
                proposer_id="system",
                proposer_name="系统默认",
            )
            self._rules[rule.id] = rule
            self._active_rules[rule.id] = rule
    
    def propose_rule(
        self,
        proposer_id: str,
        proposer_name: str,
        name: str,
        description: str,
        rule_type: RuleType,
        parameters: dict,
        effective_days: int = 30,
    ) -> RiskRule:
        """提议新规则"""
        required_voters = self.REQUIRED_VOTERS_BY_TYPE.get(
            rule_type, ["cro", "cio"]
        )
        
        rule = RiskRule(
            name=name,
            description=description,
            rule_type=rule_type,
            status=RuleStatus.PROPOSED,
            parameters=parameters,
            proposer_id=proposer_id,
            proposer_name=proposer_name,
            required_voters=required_voters,
            effective_until=datetime.utcnow() + timedelta(days=effective_days),
        )
        
        self._rules[rule.id] = rule
        
        logger.info(
            "规则已提议",
            rule_id=rule.id,
            name=name,
            type=rule_type.value,
            proposer=proposer_id,
        )
        
        return rule
    
    def vote_on_rule(
        self,
        rule_id: str,
        voter_id: str,
        voter_name: str,
        department: str,
        vote_type: VoteType,
        reason: str,
    ) -> dict:
        """对规则投票"""
        if rule_id not in self._rules:
            return {"success": False, "error": "规则不存在"}
        
        rule = self._rules[rule_id]
        
        if rule.status not in [RuleStatus.PROPOSED, RuleStatus.VOTING]:
            return {"success": False, "error": f"规则状态不允许投票: {rule.status.value}"}
        
        # 设置状态为投票中
        if rule.status == RuleStatus.PROPOSED:
            rule.status = RuleStatus.VOTING
        
        # 获取投票权重
        weight = self.VOTE_WEIGHTS.get(voter_id, self.VOTE_WEIGHTS["default"])
        
        vote = Vote(
            voter_id=voter_id,
            voter_name=voter_name,
            department=department,
            vote=vote_type,
            reason=reason,
            weight=weight,
        )
        
        if not rule.add_vote(vote):
            return {"success": False, "error": "已经投过票"}
        
        # 检查是否所有必要投票者都已投票
        voted_ids = {v.voter_id for v in rule.votes}
        all_required_voted = all(r in voted_ids for r in rule.required_voters)
        
        result = {
            "success": True,
            "rule_id": rule_id,
            "current_approval_rate": round(rule.approval_rate * 100, 1),
            "required_approval_rate": round(rule.required_approval_rate * 100, 1),
            "votes_count": len(rule.votes),
            "required_voters_voted": all_required_voted,
        }
        
        # 如果所有必要投票者都已投票，确定结果
        if all_required_voted:
            if rule.is_approved:
                rule.status = RuleStatus.APPROVED
                result["final_result"] = "approved"
                self._create_decision(rule, "approve")
            else:
                rule.status = RuleStatus.REJECTED
                result["final_result"] = "rejected"
                self._create_decision(rule, "reject")
        
        logger.info(
            "规则投票",
            rule_id=rule_id,
            voter=voter_id,
            vote=vote_type.value,
            approval_rate=rule.approval_rate,
        )
        
        return result
    
    def _create_decision(self, rule: RiskRule, decision_type: str) -> GovernanceDecision:
        """创建治理决议"""
        decision = GovernanceDecision(
            rule_id=rule.id,
            decision_type=decision_type,
            participants=[v.voter_id for v in rule.votes],
            summary=f"规则 '{rule.name}' {'通过' if decision_type == 'approve' else '被拒绝'}",
            rationale=f"投票结果: {round(rule.approval_rate * 100, 1)}% 同意",
        )
        
        self._decisions[decision.id] = decision
        rule.resolution = decision.summary
        
        return decision
    
    def activate_rule(self, rule_id: str) -> dict:
        """激活规则"""
        if rule_id not in self._rules:
            return {"success": False, "error": "规则不存在"}
        
        rule = self._rules[rule_id]
        
        if rule.status != RuleStatus.APPROVED:
            return {"success": False, "error": f"规则状态不允许激活: {rule.status.value}"}
        
        rule.status = RuleStatus.ACTIVE
        rule.effective_from = datetime.utcnow()
        self._active_rules[rule.id] = rule
        
        logger.info("规则已激活", rule_id=rule_id)
        
        return {"success": True, "rule_id": rule_id, "effective_from": rule.effective_from.isoformat()}
    
    def suspend_rule(self, rule_id: str, reason: str, suspender_id: str) -> dict:
        """暂停规则"""
        if rule_id not in self._active_rules:
            return {"success": False, "error": "规则不在活跃列表中"}
        
        rule = self._active_rules[rule_id]
        rule.status = RuleStatus.SUSPENDED
        rule.resolution = f"被 {suspender_id} 暂停: {reason}"
        
        del self._active_rules[rule.id]
        
        logger.info("规则已暂停", rule_id=rule_id, reason=reason)
        
        return {"success": True, "rule_id": rule_id}
    
    def get_active_rules(self) -> list[RiskRule]:
        """获取所有生效规则"""
        return list(self._active_rules.values())
    
    def get_rule(self, rule_id: str) -> Optional[RiskRule]:
        """获取规则详情"""
        return self._rules.get(rule_id)
    
    def get_all_rules(
        self,
        rule_type: RuleType = None,
        status: RuleStatus = None,
    ) -> list[RiskRule]:
        """获取所有规则"""
        rules = list(self._rules.values())
        
        if rule_type:
            rules = [r for r in rules if r.rule_type == rule_type]
        if status:
            rules = [r for r in rules if r.status == status]
        
        return rules
    
    def check_compliance(self, position_data: dict) -> dict:
        """检查合规性"""
        violations = []
        warnings = []
        
        for rule in self._active_rules.values():
            result = self._check_rule(rule, position_data)
            if result.get("violated"):
                violations.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "message": result.get("message"),
                    "severity": result.get("severity", "high"),
                })
            elif result.get("warning"):
                warnings.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "message": result.get("message"),
                })
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "rules_checked": len(self._active_rules),
            "checked_at": datetime.utcnow().isoformat(),
        }
    
    def _check_rule(self, rule: RiskRule, position_data: dict) -> dict:
        """检查单个规则"""
        params = rule.parameters
        
        if rule.rule_type == RuleType.CONCENTRATION_LIMIT:
            max_pct = params.get("max_single_asset_pct", 30) / 100
            for asset, pct in position_data.get("asset_allocations", {}).items():
                if pct > max_pct:
                    return {
                        "violated": True,
                        "message": f"资产 {asset} 占比 {pct*100:.1f}% 超过限制 {max_pct*100}%",
                        "severity": "high",
                    }
                elif pct > max_pct * 0.9:
                    return {
                        "warning": True,
                        "message": f"资产 {asset} 占比 {pct*100:.1f}% 接近限制",
                    }
        
        elif rule.rule_type == RuleType.LOSS_LIMIT:
            max_loss = params.get("max_daily_loss_pct", 5) / 100
            daily_pnl = position_data.get("daily_pnl_pct", 0)
            if daily_pnl < -max_loss:
                return {
                    "violated": True,
                    "message": f"日内亏损 {abs(daily_pnl)*100:.1f}% 超过限制 {max_loss*100}%",
                    "severity": "critical",
                }
            elif daily_pnl < -max_loss * 0.8:
                return {
                    "warning": True,
                    "message": f"日内亏损 {abs(daily_pnl)*100:.1f}% 接近限制",
                }
        
        elif rule.rule_type == RuleType.RISK_LIMIT:
            max_leverage = params.get("max_leverage", 3)
            current_leverage = position_data.get("leverage", 1)
            if current_leverage > max_leverage:
                return {
                    "violated": True,
                    "message": f"当前杠杆 {current_leverage}x 超过限制 {max_leverage}x",
                    "severity": "high",
                }
            elif current_leverage > params.get("margin_call_leverage", max_leverage * 0.8):
                return {
                    "warning": True,
                    "message": f"当前杠杆 {current_leverage}x 接近警戒线",
                }
        
        return {"compliant": True}
    
    def get_decisions(self, rule_id: str = None) -> list[GovernanceDecision]:
        """获取治理决议"""
        decisions = list(self._decisions.values())
        if rule_id:
            decisions = [d for d in decisions if d.rule_id == rule_id]
        return decisions
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        rules = list(self._rules.values())
        
        return {
            "total_rules": len(rules),
            "active_rules": len(self._active_rules),
            "by_type": {
                t.value: len([r for r in rules if r.rule_type == t])
                for t in RuleType
            },
            "by_status": {
                s.value: len([r for r in rules if r.status == s])
                for s in RuleStatus
            },
            "pending_votes": len([r for r in rules if r.status == RuleStatus.VOTING]),
            "total_decisions": len(self._decisions),
        }


# 全局单例
_risk_governance_system: Optional[RiskGovernanceSystem] = None


def get_risk_governance_system() -> RiskGovernanceSystem:
    """获取 RiskGovernanceSystem 单例"""
    global _risk_governance_system
    if _risk_governance_system is None:
        _risk_governance_system = RiskGovernanceSystem()
    return _risk_governance_system
