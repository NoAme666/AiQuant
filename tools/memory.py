# AI Quant Company - Memory Tools
"""
Agent 记忆工具

提供:
- write: 写入记忆
- search: 混合搜索记忆（标签+关键词+向量）
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class MemoryTools:
    """Agent 记忆工具"""
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        llm_client = None,
    ):
        """初始化记忆工具
        
        Args:
            db_url: 数据库连接 URL
            llm_client: LLM 客户端（用于生成嵌入向量）
        """
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.llm_client = llm_client
        self._pool = None
    
    async def _get_pool(self):
        """获取数据库连接池"""
        if self._pool is None:
            try:
                import asyncpg
                # 从 DATABASE_URL 提取连接信息
                db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
                self._pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)
            except Exception as e:
                logger.error("数据库连接失败", error=str(e))
                self._pool = None
        return self._pool
    
    async def _get_embedding(self, text: str) -> list[float]:
        """获取文本嵌入向量"""
        if self.llm_client:
            try:
                return await self.llm_client.embed(text)
            except Exception as e:
                logger.warning(f"获取嵌入失败: {e}")
        
        # Mock 嵌入（1536维）
        import hashlib
        import random
        random.seed(hashlib.md5(text.encode()).hexdigest())
        return [random.uniform(-1, 1) for _ in range(1536)]
    
    async def write(
        self,
        agent_id: str,
        content: str,
        tags: list[str],
        refs: dict,
        scope: str = "private",
        confidence: float = 1.0,
        ttl_days: Optional[int] = None,
    ) -> dict:
        """写入记忆
        
        Args:
            agent_id: Agent ID
            content: 内容（限制500字）
            tags: 标签列表
            refs: 引用（experiment_id, data_version_hash, artifact_id）
            scope: 范围 (private/team/org)
            confidence: 置信度 (0-1)
            ttl_days: 有效期（天）
            
        Returns:
            包含 memory_id 和状态的字典
        """
        # 验证内容长度
        if len(content) > 500:
            return {
                "success": False,
                "error": f"Content exceeds 500 chars (got {len(content)})",
            }
        
        # 验证必须有引用
        if not refs or not any(refs.values()):
            return {
                "success": False,
                "error": "refs must contain at least one valid reference (experiment_id, data_version_hash, or artifact_id)",
            }
        
        memory_id = str(uuid4())
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=ttl_days) if ttl_days else None
        
        # 确定审批状态
        approval_status = "APPROVED" if scope == "private" else "PENDING"
        
        logger.info(
            "写入记忆",
            agent_id=agent_id,
            memory_id=memory_id,
            scope=scope,
            tags=tags,
            approval_status=approval_status,
        )
        
        # 获取嵌入向量
        embedding = await self._get_embedding(content)
        
        pool = await self._get_pool()
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 插入记忆
                    await conn.execute("""
                        INSERT INTO agent_memory (
                            id, agent_id, content, tags, scope, confidence,
                            expires_at, embedding, refs, approval_status, created_at
                        ) VALUES ($1, $2, $3, $4, $5::memory_scope, $6, $7, $8, $9, $10::approval_status, $11)
                    """,
                        memory_id, agent_id, content, tags, scope, confidence,
                        expires_at, str(embedding), refs, approval_status, created_at
                    )
                    
                    # 如果需要审批，创建审批记录
                    if approval_status == "PENDING":
                        approvers = self._get_approvers_for_scope(scope)
                        for step, approver in enumerate(approvers, 1):
                            await conn.execute("""
                                INSERT INTO memory_approvals (memory_id, step, approver, status)
                                VALUES ($1, $2, $3, 'PENDING')
                            """, memory_id, step, approver)
                    
                    return {
                        "success": True,
                        "memory_id": memory_id,
                        "scope": scope,
                        "approval_status": approval_status,
                        "requires_approval": approval_status == "PENDING",
                        "created_at": created_at.isoformat(),
                    }
                    
            except Exception as e:
                logger.error("写入记忆失败", error=str(e))
                return {
                    "success": False,
                    "error": str(e),
                }
        
        # Mock 模式（无数据库连接）
        return {
            "success": True,
            "memory_id": memory_id,
            "scope": scope,
            "approval_status": approval_status,
            "requires_approval": approval_status == "PENDING",
            "created_at": created_at.isoformat(),
            "_mock": True,
        }
    
    def _get_approvers_for_scope(self, scope: str) -> list[str]:
        """获取指定范围的审批者列表"""
        if scope == "team":
            return ["team_lead"]  # 由组长审批
        elif scope == "org":
            return ["chief_of_staff", "cro"]  # 需要办公室主任和 CRO 审批
        return []
    
    async def search(
        self,
        agent_id: str,
        query: str,
        tags: Optional[list[str]] = None,
        scopes: Optional[list[str]] = None,
        top_k: int = 5,
    ) -> dict:
        """搜索记忆
        
        Args:
            agent_id: Agent ID
            query: 搜索查询
            tags: 过滤标签
            scopes: 搜索范围
            top_k: 返回结果数
            
        Returns:
            包含搜索结果的字典
        """
        scopes = scopes or ["private"]
        
        logger.info(
            "搜索记忆",
            agent_id=agent_id,
            query=query[:50],
            scopes=scopes,
            top_k=top_k,
        )
        
        # 获取查询嵌入
        query_embedding = await self._get_embedding(query)
        
        pool = await self._get_pool()
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 使用混合搜索函数
                    results = await conn.fetch("""
                        SELECT 
                            memory_id,
                            content,
                            tags,
                            scope,
                            confidence,
                            refs,
                            rrf_score,
                            created_at
                        FROM search_agent_memory(
                            $1, $2, $3, $4, $5, $6
                        )
                    """,
                        agent_id,
                        str(query_embedding),
                        query,
                        tags,
                        scopes,
                        top_k
                    )
                    
                    memories = [
                        {
                            "memory_id": str(r["memory_id"]),
                            "content": r["content"],
                            "tags": r["tags"],
                            "scope": r["scope"],
                            "confidence": r["confidence"],
                            "refs": r["refs"],
                            "relevance_score": r["rrf_score"],
                            "created_at": r["created_at"].isoformat(),
                        }
                        for r in results
                    ]
                    
                    return {
                        "success": True,
                        "query": query,
                        "agent_id": agent_id,
                        "count": len(memories),
                        "results": memories,
                    }
                    
            except Exception as e:
                logger.error("搜索记忆失败", error=str(e))
                return {
                    "success": False,
                    "error": str(e),
                    "results": [],
                }
        
        # Mock 模式（无数据库连接）
        mock_results = [
            {
                "memory_id": str(uuid4()),
                "content": f"[Mock] 关于 {query} 的记忆内容示例 {i+1}",
                "tags": tags or ["mock"],
                "scope": scopes[0] if scopes else "private",
                "confidence": 0.9 - i * 0.1,
                "refs": {"experiment_id": f"EXP_MOCK_{i}"},
                "relevance_score": 0.9 - i * 0.1,
                "created_at": datetime.utcnow().isoformat(),
            }
            for i in range(min(top_k, 3))
        ]
        
        return {
            "success": True,
            "query": query,
            "agent_id": agent_id,
            "count": len(mock_results),
            "results": mock_results,
            "_mock": True,
        }
    
    async def approve_memory(
        self,
        memory_id: str,
        approver_id: str,
        approved: bool,
        comments: Optional[str] = None,
    ) -> dict:
        """审批记忆
        
        Args:
            memory_id: 记忆 ID
            approver_id: 审批者 ID
            approved: 是否批准
            comments: 审批意见
            
        Returns:
            审批结果
        """
        pool = await self._get_pool()
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    # 更新审批记录
                    status = "APPROVED" if approved else "REJECTED"
                    await conn.execute("""
                        UPDATE memory_approvals
                        SET status = $1::approval_status,
                            comments = $2,
                            decided_at = NOW()
                        WHERE memory_id = $3 AND approver = $4 AND status = 'PENDING'
                    """, status, comments, memory_id, approver_id)
                    
                    # 检查是否所有审批都完成
                    pending = await conn.fetchval("""
                        SELECT COUNT(*) FROM memory_approvals
                        WHERE memory_id = $1 AND status = 'PENDING'
                    """, memory_id)
                    
                    if pending == 0:
                        # 检查是否有拒绝
                        rejected = await conn.fetchval("""
                            SELECT COUNT(*) FROM memory_approvals
                            WHERE memory_id = $1 AND status = 'REJECTED'
                        """, memory_id)
                        
                        final_status = "REJECTED" if rejected > 0 else "APPROVED"
                        
                        await conn.execute("""
                            UPDATE agent_memory
                            SET approval_status = $1::approval_status,
                                approved_by = $2,
                                approved_at = NOW()
                            WHERE id = $3
                        """, final_status, approver_id, memory_id)
                        
                        return {
                            "success": True,
                            "memory_id": memory_id,
                            "final_status": final_status,
                            "all_approved": final_status == "APPROVED",
                        }
                    
                    return {
                        "success": True,
                        "memory_id": memory_id,
                        "step_status": status,
                        "pending_approvals": pending,
                    }
                    
            except Exception as e:
                logger.error("审批记忆失败", error=str(e))
                return {
                    "success": False,
                    "error": str(e),
                }
        
        return {
            "success": True,
            "memory_id": memory_id,
            "status": "APPROVED" if approved else "REJECTED",
            "_mock": True,
        }
