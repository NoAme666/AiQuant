# AI Quant Company - Tool Router
"""
工具路由器

负责:
- 工具调用权限检查 (RBAC)
- 预算控制与扣费
- 审计日志记录
- 工具执行调度
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatch
from typing import Any, Optional
from uuid import uuid4

import structlog
import yaml

from tools.registry import ToolRegistry, ToolResult, ToolCategory, get_tool_registry
from tools.market import MarketTools
from tools.backtest import BacktestTools
from tools.memory import MemoryTools
from tools.meeting import MeetingTools

logger = structlog.get_logger()


@dataclass
class ToolCallRequest:
    """工具调用请求"""
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    tool_name: str = ""
    args: dict = field(default_factory=dict)
    
    # 上下文
    meeting_id: Optional[str] = None
    research_cycle_id: Optional[str] = None
    
    # 请求时间
    requested_at: datetime = field(default_factory=datetime.utcnow)


@dataclass 
class ToolPermission:
    """工具权限配置"""
    tool_name: str
    allowed_agents: list[str] = field(default_factory=list)  # 支持通配符
    allowed_departments: list[str] = field(default_factory=list)
    max_cost: Optional[int] = None
    requires_approval_above: Optional[int] = None
    approvers: list[str] = field(default_factory=list)
    
    # 参数限制
    max_limit: Optional[int] = None
    allowed_timeframes: list[str] = field(default_factory=list)
    
    # 范围审批 (memory.write 专用)
    scope_approval: dict = field(default_factory=dict)


class ToolRouter:
    """工具路由器
    
    负责:
    1. 权限检查 (RBAC)
    2. 预算控制
    3. 审计日志
    4. 工具执行
    """
    
    def __init__(
        self,
        permissions_path: str = "configs/permissions.yaml",
        db_url: Optional[str] = None,
        llm_client = None,
    ):
        """初始化工具路由器
        
        Args:
            permissions_path: 权限配置文件路径
            db_url: 数据库 URL
            llm_client: LLM 客户端（用于 memory 工具）
        """
        self.permissions_path = permissions_path
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.llm_client = llm_client
        
        # 工具注册表
        self.registry = get_tool_registry()
        
        # 权限配置
        self._permissions: dict[str, ToolPermission] = {}
        self._load_permissions()
        
        # 工具实例
        self._tools: dict[ToolCategory, Any] = {}
        self._init_tools()
        
        # 数据库连接池
        self._pool = None
        
        logger.info("ToolRouter 初始化完成", tools_count=len(self.registry.list_tools()))
    
    def _load_permissions(self) -> None:
        """加载权限配置"""
        if not os.path.exists(self.permissions_path):
            logger.warning("权限配置文件不存在", path=self.permissions_path)
            return
        
        with open(self.permissions_path) as f:
            config = yaml.safe_load(f)
        
        tools_config = config.get("tools", {})
        for tool_name, tool_perm in tools_config.items():
            self._permissions[tool_name] = ToolPermission(
                tool_name=tool_name,
                allowed_agents=tool_perm.get("allowed_agents", []),
                allowed_departments=tool_perm.get("allowed_departments", []),
                max_cost=tool_perm.get("max_cost"),
                requires_approval_above=tool_perm.get("requires_approval_above"),
                approvers=tool_perm.get("approvers", []),
                max_limit=tool_perm.get("max_limit"),
                allowed_timeframes=tool_perm.get("allowed_timeframes", []),
                scope_approval=tool_perm.get("scope_approval", {}),
            )
        
        logger.info("权限配置加载完成", permissions_count=len(self._permissions))
    
    def _init_tools(self) -> None:
        """初始化工具实例"""
        self._tools[ToolCategory.MARKET] = MarketTools()
        self._tools[ToolCategory.BACKTEST] = BacktestTools()
        self._tools[ToolCategory.MEMORY] = MemoryTools(
            db_url=self.db_url,
            llm_client=self.llm_client,
        )
        self._tools[ToolCategory.MEETING] = MeetingTools(db_url=self.db_url)
    
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
    
    def check_permission(
        self,
        agent_id: str,
        agent_department: str,
        tool_name: str,
        args: dict,
    ) -> tuple[bool, str]:
        """检查工具调用权限
        
        Args:
            agent_id: Agent ID
            agent_department: Agent 部门
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            (是否允许, 原因)
        """
        # 获取工具 schema
        schema = self.registry.get(tool_name)
        if not schema:
            return False, f"Unknown tool: {tool_name}"
        
        # 检查 schema 级别的权限
        if schema.allowed_departments:
            if agent_department not in schema.allowed_departments:
                return False, f"Department {agent_department} not allowed for {tool_name}"
        
        # 检查配置级别的权限
        perm = self._permissions.get(tool_name)
        if perm:
            # 检查 agent 白名单
            if perm.allowed_agents:
                allowed = False
                for pattern in perm.allowed_agents:
                    if fnmatch(agent_id, pattern):
                        allowed = True
                        break
                if not allowed:
                    return False, f"Agent {agent_id} not in allowed list for {tool_name}"
            
            # 检查部门白名单
            if perm.allowed_departments:
                if agent_department not in perm.allowed_departments:
                    return False, f"Department {agent_department} not allowed for {tool_name}"
            
            # 检查参数限制
            if perm.max_limit and args.get("limit", 0) > perm.max_limit:
                return False, f"Limit {args.get('limit')} exceeds max {perm.max_limit}"
            
            if perm.allowed_timeframes and args.get("timeframe"):
                if args["timeframe"] not in perm.allowed_timeframes:
                    return False, f"Timeframe {args['timeframe']} not allowed"
        
        return True, "OK"
    
    def estimate_cost(self, tool_name: str, args: dict) -> int:
        """估算工具调用成本"""
        return self.registry.estimate_cost(tool_name, args)
    
    async def check_budget(self, agent_id: str, cost: int) -> tuple[bool, int]:
        """检查预算是否足够
        
        Args:
            agent_id: Agent ID
            cost: 所需成本
            
        Returns:
            (是否足够, 当前余额)
        """
        pool = await self._get_pool()
        if not pool:
            return True, 9999  # Mock 模式
        
        try:
            async with pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT current_period_points - points_spent as remaining
                    FROM budget_accounts
                    WHERE id = $1 OR id = (
                        SELECT team FROM agents WHERE id = $1
                    )
                    LIMIT 1
                """, agent_id)
                
                if result:
                    remaining = result["remaining"]
                    return remaining >= cost, remaining
                
                return True, 0  # 无预算记录，允许调用
                
        except Exception as e:
            logger.warning(f"检查预算失败: {e}")
            return True, 0
    
    async def deduct_budget(
        self,
        agent_id: str,
        cost: int,
        tool_name: str,
        tool_call_id: str,
    ) -> bool:
        """扣除预算
        
        Args:
            agent_id: Agent ID
            cost: 扣除金额
            tool_name: 工具名称
            tool_call_id: 工具调用 ID
            
        Returns:
            是否成功
        """
        pool = await self._get_pool()
        if not pool:
            return True  # Mock 模式
        
        try:
            async with pool.acquire() as conn:
                # 找到账户 ID（可能是 agent 或 team）
                account_id = await conn.fetchval("""
                    SELECT COALESCE(
                        (SELECT id FROM budget_accounts WHERE id = $1),
                        (SELECT team FROM agents WHERE id = $1)
                    )
                """, agent_id)
                
                if not account_id:
                    logger.warning(f"未找到预算账户: {agent_id}")
                    return True
                
                # 使用存储过程扣除
                success = await conn.fetchval(
                    "SELECT deduct_budget($1, $2, $3, NULL, $4)",
                    account_id, cost, tool_name, f"Tool call: {tool_call_id}"
                )
                
                return success or False
                
        except Exception as e:
            logger.error(f"扣除预算失败: {e}")
            return False
    
    async def log_tool_call(
        self,
        request: ToolCallRequest,
        status: str,
        result: Optional[ToolResult] = None,
        error: Optional[str] = None,
    ) -> None:
        """记录工具调用日志
        
        Args:
            request: 调用请求
            status: 状态
            result: 执行结果
            error: 错误信息
        """
        pool = await self._get_pool()
        
        log_data = {
            "tool_call_id": request.id,
            "agent_id": request.agent_id,
            "tool_name": request.tool_name,
            "status": status,
            "requested_at": request.requested_at.isoformat(),
        }
        
        if result:
            log_data.update({
                "data_version_hash": result.data_version_hash,
                "experiment_id": result.experiment_id,
                "compute_points_used": result.compute_points_used,
            })
        
        if error:
            log_data["error"] = error
        
        logger.info("工具调用日志", **log_data)
        
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO tool_calls (
                            id, agent_id, tool_name, tool_args, status,
                            estimated_cost, actual_cost, result, error_message,
                            data_version_hash, experiment_id,
                            meeting_id, research_cycle_id, created_at
                        ) VALUES (
                            $1, $2, $3, $4, $5::tool_call_status,
                            $6, $7, $8, $9, $10, $11, $12, $13, $14
                        )
                    """,
                        request.id, request.agent_id, request.tool_name,
                        json.dumps(request.args), status,
                        self.estimate_cost(request.tool_name, request.args),
                        result.compute_points_used if result else 0,
                        json.dumps(result.to_dict()) if result else None,
                        error,
                        result.data_version_hash if result else None,
                        result.experiment_id if result else None,
                        request.meeting_id, request.research_cycle_id,
                        request.requested_at
                    )
            except Exception as e:
                logger.error(f"保存工具调用日志失败: {e}")
    
    async def execute(
        self,
        agent_id: str,
        agent_department: str,
        tool_name: str,
        args: dict,
        meeting_id: Optional[str] = None,
        research_cycle_id: Optional[str] = None,
    ) -> ToolResult:
        """执行工具调用
        
        完整流程:
        1. 权限检查 (RBAC)
        2. 预算检查
        3. 记录请求日志
        4. 执行工具
        5. 扣除预算
        6. 记录完成日志
        
        Args:
            agent_id: Agent ID
            agent_department: Agent 部门
            tool_name: 工具名称
            args: 工具参数
            meeting_id: 会议 ID（如果在会议中）
            research_cycle_id: 研究周期 ID
            
        Returns:
            工具执行结果
        """
        request = ToolCallRequest(
            agent_id=agent_id,
            tool_name=tool_name,
            args=args,
            meeting_id=meeting_id,
            research_cycle_id=research_cycle_id,
        )
        
        started_at = datetime.utcnow()
        
        # 1. 权限检查
        allowed, reason = self.check_permission(
            agent_id, agent_department, tool_name, args
        )
        if not allowed:
            await self.log_tool_call(request, "rejected", error=reason)
            return ToolResult(
                success=False,
                error=f"Permission denied: {reason}",
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )
        
        # 2. 估算成本并检查预算
        estimated_cost = self.estimate_cost(tool_name, args)
        has_budget, remaining = await self.check_budget(agent_id, estimated_cost)
        
        if not has_budget:
            await self.log_tool_call(
                request, "rejected",
                error=f"Insufficient budget: need {estimated_cost}, have {remaining}"
            )
            return ToolResult(
                success=False,
                error=f"Insufficient budget: need {estimated_cost} CP, have {remaining}",
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )
        
        # 3. 检查是否需要审批
        perm = self._permissions.get(tool_name)
        if perm and perm.requires_approval_above:
            if estimated_cost > perm.requires_approval_above:
                await self.log_tool_call(
                    request, "requested",
                    error=f"Requires approval for cost {estimated_cost} > {perm.requires_approval_above}"
                )
                return ToolResult(
                    success=False,
                    error=f"Cost {estimated_cost} exceeds approval threshold. Requires approval from: {perm.approvers}",
                    compute_points_used=0,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                )
        
        # 4. 记录执行开始
        await self.log_tool_call(request, "executing")
        
        try:
            # 5. 执行工具
            result = await self._execute_tool(tool_name, args, request)
            result.started_at = started_at
            result.completed_at = datetime.utcnow()
            result.compute_points_used = estimated_cost
            
            # 6. 扣除预算
            if result.success:
                await self.deduct_budget(agent_id, estimated_cost, tool_name, request.id)
            
            # 7. 记录完成
            await self.log_tool_call(request, "completed", result=result)
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            await self.log_tool_call(request, "failed", error=error_msg)
            return ToolResult(
                success=False,
                error=error_msg,
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )
    
    async def _execute_tool(
        self,
        tool_name: str,
        args: dict,
        request: ToolCallRequest,
    ) -> ToolResult:
        """执行具体工具
        
        Args:
            tool_name: 工具名称
            args: 参数
            request: 调用请求
            
        Returns:
            执行结果
        """
        schema = self.registry.get(tool_name)
        if not schema:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
        
        category = schema.category
        tool_instance = self._tools.get(category)
        
        if not tool_instance:
            return ToolResult(success=False, error=f"Tool not initialized: {tool_name}")
        
        # 根据工具名称路由到具体方法
        if tool_name == "market.get_ohlcv":
            data = await tool_instance.get_ohlcv(**args)
            return ToolResult(
                success=True,
                data=data,
                data_version_hash=data.get("data_version_hash"),
            )
        
        elif tool_name == "market.get_quote":
            data = await tool_instance.get_quote(**args)
            return ToolResult(success=True, data=data)
        
        elif tool_name == "market.compute_indicators":
            data = await tool_instance.compute_indicators(**args)
            return ToolResult(
                success=True,
                data=data,
                data_version_hash=data.get("feature_version_hash"),
            )
        
        elif tool_name == "backtest.run":
            data = await tool_instance.run(**args)
            return ToolResult(
                success=data.get("status") == "COMPLETED",
                data=data,
                experiment_id=data.get("experiment_id"),
                data_version_hash=data.get("data_version_hash"),
                artifact_ids=list(data.get("artifacts", {}).keys()),
                error=data.get("error"),
            )
        
        elif tool_name == "memory.write":
            data = await tool_instance.write(**args)
            return ToolResult(
                success=data.get("success", False),
                data=data,
                error=data.get("error"),
            )
        
        elif tool_name == "memory.search":
            data = await tool_instance.search(**args)
            return ToolResult(
                success=data.get("success", False),
                data=data,
                error=data.get("error"),
            )
        
        elif tool_name == "meeting.present":
            # 会议展示需要验证会议上下文
            if not request.meeting_id:
                return ToolResult(
                    success=False,
                    error="meeting.present can only be called during an active meeting",
                )
            
            data = await tool_instance.present(
                meeting_id=request.meeting_id,
                presenter_id=request.agent_id,
                **args,
            )
            return ToolResult(
                success=data.get("success", False),
                data=data,
                artifact_ids=[a["artifact_id"] for a in data.get("artifacts", [])],
                error=data.get("error"),
            )
        
        else:
            return ToolResult(
                success=False,
                error=f"Tool not implemented: {tool_name}",
            )


# 全局路由器实例
_router: Optional[ToolRouter] = None


def get_tool_router() -> ToolRouter:
    """获取工具路由器单例"""
    global _router
    if _router is None:
        _router = ToolRouter()
    return _router
