# AI Quant Company - 报告生成器
"""
使用 Jinja2 模板生成报告

支持:
- 董事会报告 (Board Pack)
- 研究报告 (Research Report)
- 会议纪要 (Meeting Minutes)
- 风险备忘录 (Risk Memo)
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import structlog
from jinja2 import Environment, FileSystemLoader

logger = structlog.get_logger()


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, templates_dir: str = "reports/templates"):
        """初始化报告生成器
        
        Args:
            templates_dir: 模板目录路径
        """
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
        )
        
        # 注册自定义过滤器
        self.env.filters["yaml"] = self._yaml_filter
    
    def _yaml_filter(self, value: Any) -> str:
        """YAML 格式化过滤器"""
        import yaml
        return yaml.dump(value, allow_unicode=True, default_flow_style=False)
    
    def generate_board_pack(
        self,
        strategy_name: str,
        cycle_id: str,
        metrics: dict,
        risk: dict,
        stress_tests: list[dict],
        conclusion: str,
        recommendation: str = "",
        rejection_reason: str = "",
        additional_tests_required: str = "",
        strategy_summary: str = "",
        alpha_source: str = "",
        failure_conditions: str = "",
        kill_switch_conditions: list[str] = None,
        monitoring_items: list[dict] = None,
        decision_items: list[dict] = None,
        approval_chain: list[dict] = None,
        experiment_ids: dict = None,
        data_version_hash: str = "",
        config_hash: str = "",
        code_commit: str = "",
        backtest_period: dict = None,
        portfolio_impact: dict = None,
        risk_level: str = "M",
        risk_concerns: list[str] = None,
        initial_allocation: str = "",
        max_leverage: str = "1.0x",
        daily_stop_loss: str = "-3%",
    ) -> str:
        """生成董事会报告
        
        Args:
            strategy_name: 策略名称
            cycle_id: 研究周期 ID
            metrics: 核心指标
            risk: 风险指标
            stress_tests: 压力测试结果
            conclusion: 结论 (APPROVE/REJECT/REQUEST_MORE_TESTS)
            ... 其他参数
            
        Returns:
            生成的报告内容
        """
        template = self.env.get_template("board_pack.md.j2")
        
        report_id = f"BP-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        
        content = template.render(
            strategy_name=strategy_name,
            report_date=datetime.utcnow().strftime("%Y-%m-%d"),
            report_id=report_id,
            cycle_id=cycle_id,
            conclusion=conclusion,
            recommendation=recommendation,
            rejection_reason=rejection_reason,
            additional_tests_required=additional_tests_required,
            metrics=metrics,
            backtest_period=backtest_period or {},
            risk=risk,
            stress_tests=stress_tests,
            risk_level=risk_level,
            risk_concerns=risk_concerns or [],
            strategy_summary=strategy_summary,
            alpha_source=alpha_source,
            failure_conditions=failure_conditions,
            portfolio_impact=portfolio_impact,
            kill_switch_conditions=kill_switch_conditions or [],
            monitoring_items=monitoring_items or [],
            initial_allocation=initial_allocation,
            max_leverage=max_leverage,
            daily_stop_loss=daily_stop_loss,
            decision_items=decision_items or [],
            approval_chain=approval_chain or [],
            experiment_ids=experiment_ids or {},
            data_version_hash=data_version_hash,
            config_hash=config_hash,
            code_commit=code_commit,
            generated_at=datetime.utcnow().isoformat(),
        )
        
        logger.info(
            "生成董事会报告",
            report_id=report_id,
            strategy=strategy_name,
            conclusion=conclusion,
        )
        
        return content
    
    def generate_research_report(
        self,
        strategy_name: str,
        version: str,
        author: str,
        team: str,
        abstract: str,
        key_findings: list[str],
        core_hypothesis: str,
        hypothesis_rationale: str,
        falsifiable_conditions: list[str],
        expected_failure_scenarios: str,
        data_sources: list[dict],
        data_quality: dict,
        features: list[dict],
        backtest_config: dict,
        signal_generation_rules: str,
        position_management: str,
        sample_split: dict,
        results: dict,
        charts: dict,
        walk_forward_results: list[dict],
        walk_forward_avg_sharpe: float,
        parameter_sensitivity: list[dict],
        randomization_tests: list[dict],
        subsample_analysis: list[dict],
        cost_model_description: str,
        cost_breakdown: list[dict],
        cost_sensitivity: list[dict],
        cost_sensitivity_conclusion: str,
        capacity_estimate: str,
        capacity_limiting_factors: str,
        risk_metrics: dict,
        top_drawdowns: list[dict],
        stress_tests: list[dict],
        factor_exposures: list[dict],
        limitations: list[dict],
        potential_improvements: list[dict],
        skeptic_review: Optional[dict] = None,
        conclusion: str = "",
        recommendation: str = "",
        experiment_id: str = "",
        experiment_ids: dict = None,
        data_version_hash: str = "",
        feature_version: str = "",
        config_hash: str = "",
        code_commit: str = "",
        backtest_engine_version: str = "0.1.0",
        full_config: dict = None,
        approval_chain: list[dict] = None,
    ) -> str:
        """生成研究报告
        
        Args:
            ... 详见参数
            
        Returns:
            生成的报告内容
        """
        template = self.env.get_template("research_report.md.j2")
        
        report_id = f"RR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"
        
        content = template.render(
            strategy_name=strategy_name,
            version=version,
            author=author,
            team=team,
            report_date=datetime.utcnow().strftime("%Y-%m-%d"),
            report_id=report_id,
            abstract=abstract,
            key_findings=key_findings,
            core_hypothesis=core_hypothesis,
            hypothesis_rationale=hypothesis_rationale,
            falsifiable_conditions=falsifiable_conditions,
            expected_failure_scenarios=expected_failure_scenarios,
            data_sources=data_sources,
            data_quality=data_quality,
            features=features,
            data_version_hash=data_version_hash,
            feature_version=feature_version,
            backtest_config=backtest_config,
            signal_generation_rules=signal_generation_rules,
            position_management=position_management,
            sample_split=sample_split,
            results=results,
            charts=charts,
            walk_forward_results=walk_forward_results,
            walk_forward_avg_sharpe=walk_forward_avg_sharpe,
            parameter_sensitivity=parameter_sensitivity,
            randomization_tests=randomization_tests,
            subsample_analysis=subsample_analysis,
            cost_model_description=cost_model_description,
            cost_breakdown=cost_breakdown,
            cost_sensitivity=cost_sensitivity,
            cost_sensitivity_conclusion=cost_sensitivity_conclusion,
            capacity_estimate=capacity_estimate,
            capacity_limiting_factors=capacity_limiting_factors,
            risk_metrics=risk_metrics,
            top_drawdowns=top_drawdowns,
            stress_tests=stress_tests,
            factor_exposures=factor_exposures,
            limitations=limitations,
            potential_improvements=potential_improvements,
            skeptic_review=skeptic_review,
            conclusion=conclusion,
            recommendation=recommendation,
            experiment_id=experiment_id,
            experiment_ids=experiment_ids or {},
            config_hash=config_hash,
            code_commit=code_commit,
            backtest_engine_version=backtest_engine_version,
            full_config=full_config or {},
            approval_chain=approval_chain or [],
            generated_at=datetime.utcnow().isoformat(),
        )
        
        logger.info(
            "生成研究报告",
            report_id=report_id,
            strategy=strategy_name,
            version=version,
        )
        
        return content
    
    def save_report(
        self,
        content: str,
        filename: str,
        output_dir: str = "reports/output",
    ) -> str:
        """保存报告到文件
        
        Args:
            content: 报告内容
            filename: 文件名
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_path = output_path / filename
        file_path.write_text(content, encoding="utf-8")
        
        logger.info("保存报告", path=str(file_path))
        
        return str(file_path)


# 便捷函数
def create_report_generator() -> ReportGenerator:
    """创建报告生成器实例"""
    return ReportGenerator()
