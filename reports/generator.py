# AI Quant Company - 报告生成器
"""
使用 Jinja2 模板生成报告，支持 Markdown 和 PDF 输出

支持:
- 董事会报告 (Board Pack)
- 研究报告 (Research Report)
- 交易执行报告 (Trading Report)
- 合规报告 (Compliance Report)
- 周度汇报 (Weekly Report)
"""

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import structlog
from jinja2 import Environment, FileSystemLoader

logger = structlog.get_logger()


class ReportType(str, Enum):
    """报告类型"""
    BOARD_PACK = "board_pack"
    RESEARCH = "research"
    TRADING = "trading"
    COMPLIANCE = "compliance"
    WEEKLY = "weekly"
    CAPABILITY_GAP = "capability_gap"


class ReportFormat(str, Enum):
    """报告格式"""
    MARKDOWN = "md"
    HTML = "html"
    PDF = "pdf"


@dataclass
class Report:
    """报告实体"""
    id: str = field(default_factory=lambda: str(uuid4()))
    report_type: ReportType = ReportType.RESEARCH
    title: str = ""
    author: str = ""
    
    # 内容
    content_md: str = ""
    content_html: str = ""
    pdf_path: Optional[str] = None
    
    # 元数据
    metadata: dict = field(default_factory=dict)
    
    # 权限
    visibility: str = "team"  # private, team, org, chairman
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(
        self,
        templates_dir: str = "reports/templates",
        output_dir: str = "reports/output",
    ):
        """初始化报告生成器
        
        Args:
            templates_dir: 模板目录路径
            output_dir: 输出目录路径
        """
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,
        )
        
        # 注册自定义过滤器
        self.env.filters["yaml"] = self._yaml_filter
        self.env.filters["json"] = self._json_filter
        self.env.filters["number"] = self._number_filter
        self.env.filters["percent"] = self._percent_filter
        self.env.filters["datetime"] = self._datetime_filter
        
        # 报告存储
        self._reports: dict[str, Report] = {}
        
        logger.info("ReportGenerator 初始化", templates_dir=str(self.templates_dir))
    
    # ============================================
    # 过滤器
    # ============================================
    
    def _yaml_filter(self, value: Any) -> str:
        import yaml
        return yaml.dump(value, allow_unicode=True, default_flow_style=False)
    
    def _json_filter(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2)
    
    def _number_filter(self, value: float, decimals: int = 2) -> str:
        if value is None:
            return "N/A"
        return f"{value:,.{decimals}f}"
    
    def _percent_filter(self, value: float, decimals: int = 2) -> str:
        if value is None:
            return "N/A"
        return f"{value * 100:.{decimals}f}%"
    
    def _datetime_filter(self, value: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
        if value is None:
            return "N/A"
        if isinstance(value, str):
            return value
        return value.strftime(fmt)
    
    # ============================================
    # 报告生成
    # ============================================
    
    def generate(
        self,
        report_type: ReportType,
        data: dict,
        title: str = "",
        author: str = "",
        visibility: str = "team",
        output_formats: list[ReportFormat] = None,
    ) -> Report:
        """生成报告
        
        Args:
            report_type: 报告类型
            data: 报告数据
            title: 报告标题
            author: 作者
            visibility: 可见性
            output_formats: 输出格式列表
            
        Returns:
            报告对象
        """
        output_formats = output_formats or [ReportFormat.MARKDOWN, ReportFormat.HTML]
        
        # 选择模板
        template_name = self._get_template_name(report_type)
        
        try:
            template = self.env.get_template(template_name)
        except Exception as e:
            logger.warning(f"模板 {template_name} 不存在，使用默认模板")
            template = self.env.get_template("default_report.md.j2")
        
        # 生成报告 ID
        report_id = self._generate_report_id(report_type)
        
        # 准备模板数据
        template_data = {
            "report_id": report_id,
            "report_type": report_type.value,
            "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "generated_at": datetime.utcnow().isoformat(),
            "title": title,
            "author": author,
            **data,
        }
        
        # 渲染 Markdown
        content_md = template.render(**template_data)
        
        # 创建报告对象
        report = Report(
            id=report_id,
            report_type=report_type,
            title=title or f"{report_type.value} Report",
            author=author,
            content_md=content_md,
            visibility=visibility,
            metadata=data.get("metadata", {}),
        )
        
        # 保存 Markdown
        if ReportFormat.MARKDOWN in output_formats:
            md_path = self._save_markdown(report)
            report.metadata["md_path"] = md_path
        
        # 转换 HTML
        if ReportFormat.HTML in output_formats:
            report.content_html = self._markdown_to_html(content_md)
            html_path = self._save_html(report)
            report.metadata["html_path"] = html_path
        
        # 生成 PDF
        if ReportFormat.PDF in output_formats:
            pdf_path = self._generate_pdf(report)
            if pdf_path:
                report.pdf_path = pdf_path
        
        # 存储报告
        self._reports[report.id] = report
        
        logger.info(
            "报告生成完成",
            report_id=report.id,
            report_type=report_type.value,
            formats=[f.value for f in output_formats],
        )
        
        return report
    
    def _get_template_name(self, report_type: ReportType) -> str:
        """获取模板文件名"""
        template_map = {
            ReportType.BOARD_PACK: "board_pack.md.j2",
            ReportType.RESEARCH: "research_report.md.j2",
            ReportType.TRADING: "trading_report.md.j2",
            ReportType.COMPLIANCE: "compliance_report.md.j2",
            ReportType.WEEKLY: "weekly_board_report.md.j2",
            ReportType.CAPABILITY_GAP: "capability_gap_report.md.j2",
        }
        return template_map.get(report_type, "default_report.md.j2")
    
    def _generate_report_id(self, report_type: ReportType) -> str:
        """生成报告 ID"""
        prefix_map = {
            ReportType.BOARD_PACK: "BP",
            ReportType.RESEARCH: "RR",
            ReportType.TRADING: "TR",
            ReportType.COMPLIANCE: "CR",
            ReportType.WEEKLY: "WR",
            ReportType.CAPABILITY_GAP: "CG",
        }
        prefix = prefix_map.get(report_type, "RP")
        date_str = datetime.utcnow().strftime("%Y%m%d")
        random_str = uuid4().hex[:6].upper()
        return f"{prefix}-{date_str}-{random_str}"
    
    # ============================================
    # 格式转换
    # ============================================
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """Markdown 转 HTML"""
        try:
            import markdown
            from markdown.extensions.tables import TableExtension
            from markdown.extensions.fenced_code import FencedCodeExtension
            from markdown.extensions.toc import TocExtension
            
            md = markdown.Markdown(extensions=[
                TableExtension(),
                FencedCodeExtension(),
                TocExtension(),
                'markdown.extensions.meta',
            ])
            
            html_body = md.convert(markdown_content)
            
            # 包装成完整 HTML
            html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Quant Company Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #00d9ff; padding-bottom: 10px; }}
        h2 {{ color: #16213e; margin-top: 30px; }}
        h3 {{ color: #0f3460; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #1a1a2e; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        code {{ background-color: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
        pre {{ background-color: #1a1a2e; color: #fff; padding: 15px; border-radius: 8px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #00d9ff; margin: 0; padding-left: 20px; color: #666; }}
        .metric {{ font-size: 24px; font-weight: bold; color: #00d9ff; }}
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""
            return html
            
        except ImportError:
            logger.warning("markdown 库未安装")
            return f"<pre>{markdown_content}</pre>"
    
    def _generate_pdf(self, report: Report) -> Optional[str]:
        """生成 PDF
        
        使用 weasyprint 或 wkhtmltopdf 生成 PDF
        """
        if not report.content_html:
            report.content_html = self._markdown_to_html(report.content_md)
        
        pdf_filename = f"{report.id}.pdf"
        pdf_path = self.output_dir / pdf_filename
        
        # 方法 1: 使用 weasyprint
        try:
            from weasyprint import HTML
            HTML(string=report.content_html).write_pdf(str(pdf_path))
            logger.info("PDF 生成成功 (weasyprint)", path=str(pdf_path))
            return str(pdf_path)
        except ImportError:
            logger.debug("weasyprint 未安装，尝试其他方法")
        except Exception as e:
            logger.warning(f"weasyprint 生成 PDF 失败: {e}")
        
        # 方法 2: 使用 wkhtmltopdf
        try:
            html_path = self.output_dir / f"{report.id}.html"
            html_path.write_text(report.content_html, encoding="utf-8")
            
            result = subprocess.run(
                ["wkhtmltopdf", str(html_path), str(pdf_path)],
                capture_output=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                logger.info("PDF 生成成功 (wkhtmltopdf)", path=str(pdf_path))
                return str(pdf_path)
        except FileNotFoundError:
            logger.debug("wkhtmltopdf 未安装")
        except Exception as e:
            logger.warning(f"wkhtmltopdf 生成 PDF 失败: {e}")
        
        logger.warning("无法生成 PDF，请安装 weasyprint 或 wkhtmltopdf")
        return None
    
    # ============================================
    # 文件操作
    # ============================================
    
    def _save_markdown(self, report: Report) -> str:
        """保存 Markdown 文件"""
        filename = f"{report.id}.md"
        file_path = self.output_dir / filename
        file_path.write_text(report.content_md, encoding="utf-8")
        return str(file_path)
    
    def _save_html(self, report: Report) -> str:
        """保存 HTML 文件"""
        filename = f"{report.id}.html"
        file_path = self.output_dir / filename
        file_path.write_text(report.content_html, encoding="utf-8")
        return str(file_path)
    
    # ============================================
    # 报告查询
    # ============================================
    
    def get_report(self, report_id: str) -> Optional[Report]:
        """获取报告"""
        return self._reports.get(report_id)
    
    def list_reports(
        self,
        report_type: ReportType = None,
        visibility: str = None,
        limit: int = 50,
    ) -> list[Report]:
        """列出报告"""
        reports = list(self._reports.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        if visibility:
            reports = [r for r in reports if r.visibility == visibility]
        
        return sorted(reports, key=lambda r: r.created_at, reverse=True)[:limit]
    
    # ============================================
    # 便捷方法 - 特定类型报告
    # ============================================
    
    def generate_board_pack(self, **kwargs) -> Report:
        """生成董事会报告"""
        return self.generate(
            report_type=ReportType.BOARD_PACK,
            data=kwargs,
            title=kwargs.get("strategy_name", "Board Pack"),
            visibility="chairman",
            output_formats=[ReportFormat.MARKDOWN, ReportFormat.HTML, ReportFormat.PDF],
        )
    
    def generate_research_report(self, **kwargs) -> Report:
        """生成研究报告"""
        return self.generate(
            report_type=ReportType.RESEARCH,
            data=kwargs,
            title=f"{kwargs.get('strategy_name', 'Strategy')} - Research Report",
            author=kwargs.get("author", ""),
            visibility="team",
            output_formats=[ReportFormat.MARKDOWN, ReportFormat.HTML],
        )
    
    def generate_trading_report(
        self,
        plan_id: str,
        plan_name: str,
        execution_summary: dict,
        orders: list[dict],
        positions: list[dict],
        performance: dict,
        **kwargs,
    ) -> Report:
        """生成交易执行报告"""
        return self.generate(
            report_type=ReportType.TRADING,
            data={
                "plan_id": plan_id,
                "plan_name": plan_name,
                "execution_summary": execution_summary,
                "orders": orders,
                "positions": positions,
                "performance": performance,
                **kwargs,
            },
            title=f"Trading Report - {plan_name}",
            visibility="org",
            output_formats=[ReportFormat.MARKDOWN, ReportFormat.HTML],
        )
    
    def generate_compliance_report(
        self,
        date: str,
        agent_activities: list[dict],
        violations: list[dict],
        budget_usage: dict,
        audit_findings: list[dict],
        **kwargs,
    ) -> Report:
        """生成合规报告"""
        return self.generate(
            report_type=ReportType.COMPLIANCE,
            data={
                "date": date,
                "agent_activities": agent_activities,
                "violations": violations,
                "budget_usage": budget_usage,
                "audit_findings": audit_findings,
                **kwargs,
            },
            title=f"Compliance Report - {date}",
            visibility="team",
            output_formats=[ReportFormat.MARKDOWN, ReportFormat.HTML],
        )
    
    def generate_weekly_report(
        self,
        week_start: str,
        week_end: str,
        highlights: list[str],
        research_progress: list[dict],
        trading_summary: dict,
        risk_summary: dict,
        agent_performance: list[dict],
        pending_items: list[dict],
        recommendations: list[dict],
        **kwargs,
    ) -> Report:
        """生成周度汇报"""
        return self.generate(
            report_type=ReportType.WEEKLY,
            data={
                "week_start": week_start,
                "week_end": week_end,
                "highlights": highlights,
                "research_progress": research_progress,
                "trading_summary": trading_summary,
                "risk_summary": risk_summary,
                "agent_performance": agent_performance,
                "pending_items": pending_items,
                "recommendations": recommendations,
                **kwargs,
            },
            title=f"Weekly Report - {week_start} to {week_end}",
            visibility="chairman",
            output_formats=[ReportFormat.MARKDOWN, ReportFormat.HTML, ReportFormat.PDF],
        )


# ============================================
# 全局单例
# ============================================

_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """获取报告生成器单例"""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


def create_report_generator() -> ReportGenerator:
    """创建新的报告生成器实例"""
    return ReportGenerator()
