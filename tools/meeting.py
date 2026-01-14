# AI Quant Company - Meeting Tools
"""
会议展示工具

提供:
- present: 在会议中展示卡片（指标/图表/表格/摘要）
"""

import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class MeetingTools:
    """会议展示工具"""
    
    def __init__(
        self,
        db_url: Optional[str] = None,
    ):
        """初始化会议工具
        
        Args:
            db_url: 数据库连接 URL
        """
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._pool = None
    
    async def _get_pool(self):
        """获取数据库连接池"""
        if self._pool is None:
            try:
                import asyncpg
                db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
                self._pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
            except Exception as e:
                logger.error("数据库连接失败", error=str(e))
                self._pool = None
        return self._pool
    
    async def present(
        self,
        meeting_id: str,
        presenter_id: str,
        title: str,
        cards: list[dict],
    ) -> dict:
        """在会议中展示卡片
        
        Args:
            meeting_id: 会议 ID
            presenter_id: 展示者 Agent ID
            title: 展示标题
            cards: 卡片列表
            
        Returns:
            包含创建的 artifact_ids 的字典
        """
        logger.info(
            "会议展示",
            meeting_id=meeting_id,
            presenter=presenter_id,
            title=title,
            card_count=len(cards),
        )
        
        # 验证会议状态
        pool = await self._get_pool()
        meeting_valid = False
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 检查会议是否正在进行中
                    meeting = await conn.fetchrow("""
                        SELECT id, status FROM meeting_requests
                        WHERE id = $1
                    """, meeting_id)
                    
                    if meeting and meeting["status"] == "IN_PROGRESS":
                        meeting_valid = True
                    elif not meeting:
                        return {
                            "success": False,
                            "error": f"Meeting {meeting_id} not found",
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Meeting is not in progress (status: {meeting['status']})",
                        }
            except Exception as e:
                logger.warning(f"无法验证会议状态: {e}")
                # 允许继续（可能是测试模式）
                meeting_valid = True
        else:
            meeting_valid = True  # Mock 模式
        
        artifact_ids = []
        created_at = datetime.utcnow()
        
        for i, card in enumerate(cards):
            artifact_id = str(uuid4())
            card_type = card.get("type", "summary")
            card_data = card.get("data", {})
            data_ref = card.get("data_ref", {})
            
            # 验证卡片类型
            valid_types = ["metric", "plot", "table", "summary"]
            if card_type not in valid_types:
                logger.warning(f"无效的卡片类型: {card_type}")
                continue
            
            if pool:
                try:
                    async with pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO meeting_artifacts (
                                id, meeting_id, presenter, title, card_type,
                                data, data_ref, experiment_id, data_version_hash,
                                display_order, created_at
                            ) VALUES ($1, $2, $3, $4, $5::meeting_card_type, $6, $7, $8, $9, $10, $11)
                        """,
                            artifact_id, meeting_id, presenter_id,
                            f"{title} - Card {i+1}",
                            card_type, card_data, data_ref,
                            data_ref.get("experiment_id"),
                            data_ref.get("data_version_hash"),
                            i, created_at
                        )
                except Exception as e:
                    logger.error(f"保存卡片失败: {e}")
                    continue
            
            artifact_ids.append({
                "artifact_id": artifact_id,
                "card_type": card_type,
                "display_order": i,
            })
        
        logger.info(
            "展示卡片创建完成",
            meeting_id=meeting_id,
            artifact_count=len(artifact_ids),
        )
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "title": title,
            "artifacts": artifact_ids,
            "created_at": created_at.isoformat(),
            "_mock": pool is None,
        }
    
    async def get_meeting_artifacts(
        self,
        meeting_id: str,
    ) -> dict:
        """获取会议中的所有展示卡片
        
        Args:
            meeting_id: 会议 ID
            
        Returns:
            包含所有卡片的字典
        """
        pool = await self._get_pool()
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT 
                            id, presenter, title, card_type, data, data_ref,
                            experiment_id, data_version_hash, display_order, created_at
                        FROM meeting_artifacts
                        WHERE meeting_id = $1
                        ORDER BY display_order
                    """, meeting_id)
                    
                    artifacts = [
                        {
                            "id": str(r["id"]),
                            "presenter": r["presenter"],
                            "title": r["title"],
                            "card_type": r["card_type"],
                            "data": r["data"],
                            "data_ref": r["data_ref"],
                            "experiment_id": r["experiment_id"],
                            "data_version_hash": r["data_version_hash"],
                            "display_order": r["display_order"],
                            "created_at": r["created_at"].isoformat(),
                        }
                        for r in rows
                    ]
                    
                    return {
                        "success": True,
                        "meeting_id": meeting_id,
                        "count": len(artifacts),
                        "artifacts": artifacts,
                    }
                    
            except Exception as e:
                logger.error("获取会议卡片失败", error=str(e))
                return {
                    "success": False,
                    "error": str(e),
                    "artifacts": [],
                }
        
        # Mock 模式
        return {
            "success": True,
            "meeting_id": meeting_id,
            "count": 0,
            "artifacts": [],
            "_mock": True,
        }
    
    @staticmethod
    def create_metric_card(
        title: str,
        metrics: dict,
        experiment_id: Optional[str] = None,
    ) -> dict:
        """创建指标卡片
        
        Args:
            title: 卡片标题
            metrics: 指标字典，如 {"Sharpe": 1.2, "MaxDD": -0.18}
            experiment_id: 关联的实验 ID
            
        Returns:
            卡片定义
        """
        return {
            "type": "metric",
            "data": metrics,
            "data_ref": {
                "experiment_id": experiment_id,
            } if experiment_id else {},
        }
    
    @staticmethod
    def create_plot_card(
        title: str,
        artifact_path: str,
        experiment_id: Optional[str] = None,
    ) -> dict:
        """创建图表卡片
        
        Args:
            title: 卡片标题
            artifact_path: 图表文件路径
            experiment_id: 关联的实验 ID
            
        Returns:
            卡片定义
        """
        return {
            "type": "plot",
            "data": {"title": title},
            "data_ref": {
                "artifact_path": artifact_path,
                "experiment_id": experiment_id,
            },
        }
    
    @staticmethod
    def create_table_card(
        title: str,
        parquet_path: str,
        preview_rows: int = 20,
        data_version_hash: Optional[str] = None,
    ) -> dict:
        """创建表格卡片
        
        Args:
            title: 卡片标题
            parquet_path: Parquet 文件路径
            preview_rows: 预览行数
            data_version_hash: 数据版本哈希
            
        Returns:
            卡片定义
        """
        return {
            "type": "table",
            "data": {"title": title},
            "data_ref": {
                "parquet_path": parquet_path,
                "preview_rows": preview_rows,
                "data_version_hash": data_version_hash,
            },
        }
    
    @staticmethod
    def create_summary_card(
        title: str,
        summary: str,
        refs: Optional[dict] = None,
    ) -> dict:
        """创建摘要卡片
        
        Args:
            title: 卡片标题
            summary: 摘要文本
            refs: 引用
            
        Returns:
            卡片定义
        """
        return {
            "type": "summary",
            "data": {
                "title": title,
                "summary": summary,
            },
            "data_ref": refs or {},
        }
