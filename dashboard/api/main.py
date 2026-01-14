# AI Quant Company - Dashboard API
"""
FastAPI 后端入口

核心端点:
- /api/lobby: 总览指标
- /api/org-chart: 组织架构
- /api/pipeline: 研究流水线
- /api/experiments: 实验库
- /api/reports: 报告库
- /api/meetings: 会议系统
- /api/chat: 1v1 对话
- /api/events: 事件流
- /api/directive: 董事长指令
- /api/market: 实时市场数据
- /api/account: 账户余额与持仓
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from uuid import UUID

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import structlog

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.market import get_market_tools, ExchangeManager
from tools.intelligence import get_intelligence_tools
from orchestrator.performance import get_performance_system, JobLevel
from orchestrator.topic_meeting import get_topic_meeting_system, TopicCategory, TopicPriority, TopicStatus
from orchestrator.intention import get_intention_system, IntentionType, IntentionPriority
from orchestrator.risk_governance import get_risk_governance_system, RuleType, RuleStatus, VoteType
from orchestrator.agent_loop import get_agent_loop

# 数据库模块
from dashboard.api import database as db

# 数据管理器
from dashboard.api.data_manager import (
    SignalManager, PositionManager, TradingPlanManager,
    ResearchCycleManager, ReportManager, ApprovalManager,
    MeetingManager, BacktestManager, AgentStatusManager
)

logger = structlog.get_logger()


# ============================================
# 生命周期管理
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动 AI Quant Company Dashboard API")
    # 初始化数据库连接池
    try:
        await db.get_pool()
        logger.info("数据库连接池初始化成功")
    except Exception as e:
        logger.warning(f"数据库连接失败，使用降级模式: {e}")
    yield
    # 关闭数据库连接池
    await db.close_pool()
    logger.info("关闭 API 服务")


# ============================================
# 应用初始化
# ============================================

app = FastAPI(
    title="AI Quant Company Dashboard",
    description="Multi-Agent 量化公司仿真系统 Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置 - 支持 Vercel 前端和本地开发
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
# 添加 Vercel 默认域名模式
cors_origins.extend([
    "https://aiquant.vercel.app",
    "https://*.vercel.app",
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # 允许所有 Vercel 子域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# ============================================
# 数据模型
# ============================================

class LobbyStats(BaseModel):
    """Lobby 总览统计"""
    active_cycles: int = 0
    pending_approvals: int = 0
    total_experiments: int = 0
    total_agents: int = 0
    budget_utilization: float = 0.0
    avg_reputation: float = 0.0


class AgentStatus(BaseModel):
    """Agent 状态"""
    id: str
    name: str
    name_en: str
    department: str
    is_lead: bool
    status: str
    budget_remaining: int = 0
    reputation_score: float = 0.5
    current_task: Optional[str] = None


class DepartmentInfo(BaseModel):
    """部门信息"""
    id: str
    name: str
    name_en: str
    agents: list[AgentStatus]


class ResearchCycleInfo(BaseModel):
    """研究周期信息"""
    id: str
    name: str
    current_state: str
    team: str
    proposer: str
    created_at: datetime
    updated_at: datetime


class ExperimentInfo(BaseModel):
    """实验信息"""
    id: str
    cycle_id: Optional[str]
    experiment_type: str
    status: str
    metrics: Optional[dict]
    created_at: datetime


class MeetingInfo(BaseModel):
    """会议信息"""
    id: str
    title: str
    status: str
    requester: str
    participants: list[str]
    risk_level: str
    scheduled_at: Optional[datetime]


class ChatMessage(BaseModel):
    """对话消息"""
    content: str
    agent_id: str


class ChairmanDirective(BaseModel):
    """董事长指令"""
    directive_type: str
    target_type: str
    target_id: Optional[str] = None
    content: str
    reason: str
    scope: str = "global"
    effective_until: Optional[datetime] = None


class EventInfo(BaseModel):
    """事件信息"""
    id: str
    event_type: str
    actor: Optional[str]
    action: str
    details: dict
    created_at: datetime


# ============================================
# 路由 - Lobby
# ============================================

@app.get("/api/lobby", response_model=LobbyStats, tags=["Lobby"])
async def get_lobby_stats():
    """获取 Lobby 总览统计"""
    try:
        stats = await db.get_lobby_stats()
        return LobbyStats(**stats)
    except Exception as e:
        logger.warning(f"数据库查询失败，使用默认值: {e}")
        return LobbyStats(
            active_cycles=0,
            pending_approvals=0,
            total_experiments=0,
            total_agents=0,
            budget_utilization=0.0,
            avg_reputation=0.5,
        )


# ============================================
# 路由 - Org Chart
# ============================================

@app.get("/api/org-chart", response_model=list[DepartmentInfo], tags=["Organization"])
async def get_org_chart():
    """获取组织架构"""
    try:
        departments = await db.get_org_chart()
        return [DepartmentInfo(**dept) for dept in departments]
    except Exception as e:
        logger.warning(f"获取组织架构失败: {e}")
        return []


@app.get("/api/agents/status", tags=["Organization"])
async def get_agents_status():
    """获取所有 Agent 状态列表"""
    try:
        agents = await db.get_all_agents()
        return {
            "agents": [
                {
                    "id": a["id"],
                    "name": a["name"],
                    "status": str(a.get("status", "active")).lower(),
                    "task": f"工作中 ({a['department']})"
                }
                for a in agents[:10]  # 只返回前10个
            ]
        }
    except Exception as e:
        logger.warning(f"获取 Agent 状态失败: {e}")
        return {"agents": []}


@app.get("/api/agents/{agent_id}", response_model=AgentStatus, tags=["Organization"])
async def get_agent(agent_id: str):
    """获取 Agent 详情"""
    try:
        agent = await db.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return AgentStatus(
            id=agent["id"],
            name=agent["name"],
            name_en=agent.get("name_en", agent["name"]),
            department=agent["department"],
            is_lead=agent.get("is_lead", False),
            status=str(agent.get("status", "active")).lower(),
            budget_remaining=0,
            reputation_score=float(agent.get("reputation_score", 0.5)),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"获取 Agent 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 路由 - Pipeline
# ============================================

@app.get("/api/pipeline", response_model=list[ResearchCycleInfo], tags=["Pipeline"])
async def get_pipeline(
    state: Optional[str] = Query(None, description="过滤状态"),
    team: Optional[str] = Query(None, description="过滤团队"),
    limit: int = Query(50, ge=1, le=100),
):
    """获取研究流水线"""
    try:
        cycles = await db.get_research_cycles(state=state, team=team, limit=limit)
        return [
            ResearchCycleInfo(
                id=str(c["id"]),
                name=c["name"],
                current_state=c["current_state"],
                team=c.get("team", "unknown"),
                proposer=c.get("proposer", "unknown"),
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
            for c in cycles
        ]
    except Exception as e:
        logger.warning(f"获取研究流水线失败: {e}")
        return []


@app.get("/api/pipeline/{cycle_id}", response_model=ResearchCycleInfo, tags=["Pipeline"])
async def get_cycle(cycle_id: str):
    """获取研究周期详情"""
    # TODO: 从数据库获取
    return ResearchCycleInfo(
        id=cycle_id,
        name="BTC 动量策略 v1",
        current_state="ROBUSTNESS_GATE",
        team="alpha_a",
        proposer="alpha_a_lead",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ============================================
# 路由 - Experiments
# ============================================

@app.get("/api/experiments", response_model=list[ExperimentInfo], tags=["Experiments"])
async def list_experiments(
    cycle_id: Optional[str] = Query(None),
    experiment_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    """获取实验列表"""
    # TODO: 从数据库获取
    return [
        ExperimentInfo(
            id="EXP_20240115_123456_ABCD1234",
            cycle_id="cycle-001",
            experiment_type="backtest",
            status="COMPLETED",
            metrics={
                "sharpe_ratio": 1.85,
                "annualized_return": 0.32,
                "max_drawdown": 0.12,
            },
            created_at=datetime.utcnow(),
        ),
    ]


@app.get("/api/experiments/{experiment_id}", tags=["Experiments"])
async def get_experiment(experiment_id: str):
    """获取实验详情"""
    # TODO: 从数据库和文件系统获取
    return {
        "id": experiment_id,
        "cycle_id": "cycle-001",
        "experiment_type": "backtest",
        "status": "COMPLETED",
        "metrics": {
            "sharpe_ratio": 1.85,
            "annualized_return": 0.32,
            "max_drawdown": 0.12,
        },
        "config": {},
        "data_version_hash": "a1b2c3d4e5f6",
        "config_hash": "1234abcd",
        "created_at": datetime.utcnow().isoformat(),
    }


# ============================================
# 路由 - Reports
# ============================================

@app.get("/api/reports", tags=["Reports"])
async def list_reports(
    report_type: Optional[str] = Query(None, description="报告类型: board_pack, research"),
    limit: int = Query(20, ge=1, le=50),
):
    """获取报告列表"""
    return [
        {
            "id": "report-001",
            "type": "board_pack",
            "title": "BTC 动量策略评审报告",
            "cycle_id": "cycle-001",
            "created_at": datetime.utcnow().isoformat(),
            "status": "final",
        },
    ]


@app.get("/api/reports/{report_id}", tags=["Reports"])
async def get_report(report_id: str):
    """获取报告详情"""
    return {
        "id": report_id,
        "type": "board_pack",
        "title": "BTC 动量策略评审报告",
        "content": "# 报告内容...",
        "created_at": datetime.utcnow().isoformat(),
    }


# ============================================
# 路由 - Meetings
# ============================================

@app.get("/api/meetings", response_model=list[MeetingInfo], tags=["Meetings"])
async def list_meetings(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    """获取会议列表"""
    return [
        MeetingInfo(
            id="meeting-001",
            title="Alpha A 策略评审会议",
            status="PENDING_APPROVAL",
            requester="alpha_a_lead",
            participants=["cio", "cro", "head_of_research"],
            risk_level="M",
            scheduled_at=None,
        ),
    ]


@app.get("/api/meetings/pending", tags=["Meetings"])
async def get_pending_meetings(approver: Optional[str] = Query(None)):
    """获取待审批会议"""
    return []


@app.post("/api/meetings", tags=["Meetings"])
async def create_meeting(meeting: MeetingInfo):
    """创建会议申请"""
    # TODO: 调用 MeetingSystem
    return {"id": "meeting-new", "status": "DRAFT"}


@app.post("/api/meetings/{meeting_id}/approve", tags=["Meetings"])
async def approve_meeting(
    meeting_id: str,
    approved: bool,
    comments: str = "",
):
    """审批会议"""
    return {"success": True, "message": "审批成功"}


# ============================================
# 路由 - Chat
# ============================================

@app.post("/api/chat/{agent_id}", tags=["Chat"])
async def send_chat(agent_id: str, message: ChatMessage):
    """发送 1v1 对话消息"""
    # TODO: 调用 Agent 处理消息
    return {
        "success": True,
        "response": f"[{agent_id}] 收到您的消息，正在处理...",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/chat/{agent_id}/history", tags=["Chat"])
async def get_chat_history(
    agent_id: str,
    limit: int = Query(50, ge=1, le=100),
):
    """获取对话历史"""
    return []


# ============================================
# 路由 - Chairman Directive
# ============================================

@app.post("/api/directive", tags=["Directive"])
async def create_directive(directive: ChairmanDirective):
    """发布董事长指令"""
    # TODO: 存储指令并触发相应动作
    return {
        "id": "directive-001",
        "status": "ACTIVE",
        "created_at": datetime.utcnow().isoformat(),
    }


@app.get("/api/directives", tags=["Directive"])
async def list_directives(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
):
    """获取董事长指令列表"""
    return []


# ============================================
# 路由 - Events (WebSocket)
# ============================================

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@app.websocket("/api/events")
async def websocket_events(websocket: WebSocket):
    """事件流 WebSocket"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（心跳等）
            data = await websocket.receive_text()
            # 可以处理订阅请求等
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/events/recent", tags=["Events"])
async def get_recent_events(limit: int = Query(10, ge=1, le=50)):
    """获取最近事件（前端用）"""
    try:
        events = await db.get_recent_events(limit=limit)
        return {
            "events": [
                {
                    "time": e["created_at"].strftime("%H:%M") if e["created_at"] else "--:--",
                    "agent": e.get("actor_name") or e.get("actor") or "系统",
                    "action": e["action"],
                    "type": e["event_type"].split(".")[0] if e["event_type"] else "system"
                }
                for e in events
            ]
        }
    except Exception as e:
        logger.warning(f"获取事件失败: {e}")
        return {"events": []}


@app.get("/api/events/history", response_model=list[EventInfo], tags=["Events"])
async def get_events_history(
    event_type: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """获取事件历史"""
    try:
        events = await db.get_recent_events(limit=limit)
        return [
            EventInfo(
                id=str(e["id"]),
                event_type=e["event_type"],
                actor=e.get("actor"),
                action=e["action"],
                details=e.get("details", {}),
                created_at=e["created_at"]
            )
            for e in events
        ]
    except Exception as e:
        logger.warning(f"获取事件历史失败: {e}")
        return []


# ============================================
# 路由 - Audit
# ============================================

@app.get("/api/audit", tags=["Audit"])
async def get_audit_log(
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """获取审计日志"""
    return []


# ============================================
# 路由 - Budget & Reputation
# ============================================

@app.get("/api/budget", tags=["Budget"])
async def get_budget_overview():
    """获取预算概览"""
    return {
        "total_allocated": 10000,
        "total_spent": 6500,
        "by_team": {
            "alpha_a": {"allocated": 1000, "spent": 650},
            "alpha_b": {"allocated": 1000, "spent": 720},
        },
    }


@app.get("/api/reputation", tags=["Reputation"])
async def get_reputation_overview():
    """获取声誉概览"""
    return {
        "avg_score": 0.72,
        "top_performers": [],
        "needs_attention": [],
    }


# ============================================
# 路由 - Market Data (实时市场数据)
# ============================================

@app.get("/api/market/quote/{symbol:path}", tags=["Market"])
async def get_market_quote(symbol: str):
    """获取单个交易对实时报价
    
    Args:
        symbol: 交易对，如 BTC/USDT 或 BTC-USDT
    """
    try:
        # 支持 BTC-USDT 或 BTC/USDT 格式
        symbol = symbol.replace('-', '/')
        market_tools = get_market_tools()
        quote = await market_tools.get_quote(symbol)
        return quote
    except Exception as e:
        logger.error(f"获取报价失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/ohlcv/{symbol:path}", tags=["Market"])
async def get_market_ohlcv(
    symbol: str,
    timeframe: str = Query("1h", description="K线周期: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="数据条数"),
):
    """获取 K 线数据
    
    Args:
        symbol: 交易对，如 BTC/USDT 或 BTC-USDT
        timeframe: K线周期
        limit: 数据条数
    """
    try:
        # 支持 BTC-USDT 或 BTC/USDT 格式
        symbol = symbol.replace('-', '/')
        exchange_manager = ExchangeManager.get_instance()
        ohlcv = await exchange_manager.fetch_ohlcv(symbol, timeframe, limit=limit)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(ohlcv),
            "data": ohlcv,
        }
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/tickers", tags=["Market"])
async def get_market_tickers(
    symbols: Optional[str] = Query(None, description="逗号分隔的交易对列表，为空则返回热门币种"),
):
    """获取多个交易对行情
    
    Args:
        symbols: 逗号分隔的交易对，如 BTC/USDT,ETH/USDT
    """
    try:
        market_tools = get_market_tools()
        symbol_list = symbols.split(",") if symbols else None
        tickers = await market_tools.get_tickers(symbol_list)
        return {
            "count": len(tickers),
            "tickers": tickers,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"获取行情列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 路由 - Account (账户数据)
# ============================================

@app.get("/api/account/balance", tags=["Account"])
async def get_account_balance():
    """获取账户余额"""
    try:
        market_tools = get_market_tools()
        balance = await market_tools.get_balance()
        return balance
    except Exception as e:
        logger.error(f"获取账户余额失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/positions", tags=["Account"])
async def get_account_positions():
    """获取账户持仓"""
    try:
        market_tools = get_market_tools()
        positions = await market_tools.get_positions()
        return positions
    except Exception as e:
        logger.error(f"获取持仓失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/summary", tags=["Account"])
async def get_account_summary():
    """获取账户总览（余额 + 持仓）"""
    try:
        market_tools = get_market_tools()
        balance = await market_tools.get_balance()
        positions = await market_tools.get_positions()
        
        return {
            "exchange": balance.get("exchange"),
            "total_usd": balance.get("total_usd", 0),
            "balance_count": len(balance.get("balances", [])),
            "top_balances": balance.get("balances", [])[:5],
            "position_count": len(positions.get("positions", [])),
            "positions": positions.get("positions", []),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"获取账户总览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 路由 - PnL 统计
# ============================================

@app.post("/api/account/snapshot", tags=["Account"])
async def record_pnl_snapshot():
    """记录当前 PnL 快照"""
    try:
        market_tools = get_market_tools()
        balance = await market_tools.get_balance()
        positions = await market_tools.get_positions()
        
        total_value = balance.get("total_usd", 0)
        
        # 获取昨日数据计算日收益
        async with db.get_connection() as conn:
            yesterday = await conn.fetchrow("""
                SELECT total_value_usd, cumulative_pnl 
                FROM pnl_snapshots 
                WHERE snapshot_date < CURRENT_DATE
                ORDER BY snapshot_date DESC LIMIT 1
            """)
            
            if yesterday:
                prev_value = float(yesterday["total_value_usd"])
                daily_pnl = total_value - prev_value
                daily_pnl_pct = (daily_pnl / prev_value * 100) if prev_value > 0 else 0
                cumulative_pnl = float(yesterday["cumulative_pnl"] or 0) + daily_pnl
            else:
                daily_pnl = 0
                daily_pnl_pct = 0
                cumulative_pnl = 0
            
            # 初始值（第一次快照）
            first_snapshot = await conn.fetchrow("""
                SELECT total_value_usd FROM pnl_snapshots ORDER BY snapshot_date ASC LIMIT 1
            """)
            initial_value = float(first_snapshot["total_value_usd"]) if first_snapshot else total_value
            cumulative_pnl_pct = ((total_value - initial_value) / initial_value * 100) if initial_value > 0 else 0
            
            # 插入或更新快照
            import json
            await conn.execute("""
                INSERT INTO pnl_snapshots (
                    snapshot_date, exchange, total_value_usd,
                    balances, positions,
                    daily_pnl, daily_pnl_pct,
                    cumulative_pnl, cumulative_pnl_pct
                ) VALUES (
                    CURRENT_DATE, $1, $2, $3, $4, $5, $6, $7, $8
                )
                ON CONFLICT (snapshot_date, exchange) DO UPDATE SET
                    total_value_usd = EXCLUDED.total_value_usd,
                    balances = EXCLUDED.balances,
                    positions = EXCLUDED.positions,
                    daily_pnl = EXCLUDED.daily_pnl,
                    daily_pnl_pct = EXCLUDED.daily_pnl_pct,
                    cumulative_pnl = EXCLUDED.cumulative_pnl,
                    cumulative_pnl_pct = EXCLUDED.cumulative_pnl_pct,
                    snapshot_time = NOW()
            """,
                balance.get("exchange", "okx"),
                total_value,
                json.dumps(balance.get("balances", [])),
                json.dumps(positions.get("positions", [])),
                daily_pnl,
                daily_pnl_pct,
                cumulative_pnl,
                cumulative_pnl_pct,
            )
        
        return {
            "success": True,
            "total_value_usd": total_value,
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 4),
            "cumulative_pnl": round(cumulative_pnl, 2),
            "cumulative_pnl_pct": round(cumulative_pnl_pct, 4),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"记录 PnL 快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/pnl", tags=["Account"])
async def get_account_pnl():
    """获取账户盈亏统计"""
    try:
        market_tools = get_market_tools()
        balance = await market_tools.get_balance()
        
        total_value = balance.get("total_usd", 0)
        
        async with db.get_connection() as conn:
            # 获取最新快照
            latest = await conn.fetchrow("""
                SELECT * FROM pnl_snapshots ORDER BY snapshot_date DESC LIMIT 1
            """)
            
            # 获取各时间段统计
            stats = await conn.fetchrow("""
                WITH periods AS (
                    SELECT 
                        COALESCE(SUM(CASE WHEN snapshot_date >= CURRENT_DATE THEN daily_pnl END), 0) as today_pnl,
                        COALESCE(SUM(CASE WHEN snapshot_date >= CURRENT_DATE - INTERVAL '7 days' THEN daily_pnl END), 0) as week_pnl,
                        COALESCE(SUM(CASE WHEN snapshot_date >= CURRENT_DATE - INTERVAL '30 days' THEN daily_pnl END), 0) as month_pnl,
                        (SELECT total_value_usd FROM pnl_snapshots WHERE snapshot_date = CURRENT_DATE - INTERVAL '1 day' LIMIT 1) as yesterday_value,
                        (SELECT total_value_usd FROM pnl_snapshots WHERE snapshot_date = CURRENT_DATE - INTERVAL '7 days' LIMIT 1) as week_ago_value,
                        (SELECT total_value_usd FROM pnl_snapshots WHERE snapshot_date = CURRENT_DATE - INTERVAL '30 days' LIMIT 1) as month_ago_value,
                        (SELECT total_value_usd FROM pnl_snapshots ORDER BY snapshot_date ASC LIMIT 1) as initial_value
                    FROM pnl_snapshots
                )
                SELECT * FROM periods
            """)
            
            # 计算盈亏
            yesterday_value = float(stats["yesterday_value"] or total_value) if stats else total_value
            week_ago_value = float(stats["week_ago_value"] or total_value) if stats else total_value
            month_ago_value = float(stats["month_ago_value"] or total_value) if stats else total_value
            initial_value = float(stats["initial_value"] or total_value) if stats else total_value
            
            today_pnl = total_value - yesterday_value
            week_pnl = total_value - week_ago_value
            month_pnl = total_value - month_ago_value
            total_pnl = total_value - initial_value
            
            # 获取历史数据（最近30天）
            history = await conn.fetch("""
                SELECT snapshot_date, total_value_usd, daily_pnl, daily_pnl_pct
                FROM pnl_snapshots
                WHERE snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY snapshot_date ASC
            """)
        
        return {
            "exchange": balance.get("exchange", "okx"),
            "total_value_usd": round(total_value, 2),
            
            # 今日
            "today": {
                "pnl": round(today_pnl, 2),
                "pnl_pct": round((today_pnl / yesterday_value * 100) if yesterday_value > 0 else 0, 2),
            },
            
            # 本周
            "week": {
                "pnl": round(week_pnl, 2),
                "pnl_pct": round((week_pnl / week_ago_value * 100) if week_ago_value > 0 else 0, 2),
            },
            
            # 本月
            "month": {
                "pnl": round(month_pnl, 2),
                "pnl_pct": round((month_pnl / month_ago_value * 100) if month_ago_value > 0 else 0, 2),
            },
            
            # 累计
            "total": {
                "pnl": round(total_pnl, 2),
                "pnl_pct": round((total_pnl / initial_value * 100) if initial_value > 0 else 0, 2),
                "initial_value": round(initial_value, 2),
            },
            
            # 历史数据
            "history": [
                {
                    "date": row["snapshot_date"].isoformat(),
                    "value": float(row["total_value_usd"]),
                    "daily_pnl": float(row["daily_pnl"] or 0),
                    "daily_pnl_pct": float(row["daily_pnl_pct"] or 0),
                }
                for row in history
            ] if history else [],
            
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"获取 PnL 统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/pnl/history", tags=["Account"])
async def get_pnl_history(
    days: int = Query(default=30, ge=1, le=365, description="历史天数"),
):
    """获取 PnL 历史数据"""
    try:
        async with db.get_connection() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    snapshot_date,
                    total_value_usd,
                    daily_pnl,
                    daily_pnl_pct,
                    cumulative_pnl,
                    cumulative_pnl_pct
                FROM pnl_snapshots
                WHERE snapshot_date >= CURRENT_DATE - INTERVAL '{days} days'
                ORDER BY snapshot_date ASC
            """)
            
            return {
                "history": [
                    {
                        "date": row["snapshot_date"].isoformat(),
                        "value": float(row["total_value_usd"]),
                        "daily_pnl": float(row["daily_pnl"] or 0),
                        "daily_pnl_pct": float(row["daily_pnl_pct"] or 0),
                        "cumulative_pnl": float(row["cumulative_pnl"] or 0),
                        "cumulative_pnl_pct": float(row["cumulative_pnl_pct"] or 0),
                    }
                    for row in rows
                ],
                "count": len(rows),
            }
    except Exception as e:
        logger.error(f"获取 PnL 历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WebSocket - 实时行情流
# ============================================

class MarketStreamManager:
    """市场数据 WebSocket 管理器"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}
        self._running = False
        self._task = None
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info("Market WebSocket 连接建立")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info("Market WebSocket 连接断开")
    
    async def subscribe(self, websocket: WebSocket, symbols: list[str]):
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(symbols)
            await websocket.send_json({
                "type": "subscribed",
                "symbols": list(self.subscriptions[websocket]),
            })
    
    async def broadcast_ticker(self, ticker: dict):
        symbol = ticker.get("symbol")
        for ws in self.active_connections:
            if symbol in self.subscriptions.get(ws, set()) or not self.subscriptions.get(ws):
                try:
                    await ws.send_json({
                        "type": "ticker",
                        "data": ticker,
                    })
                except:
                    pass
    
    async def start_streaming(self):
        """启动行情推送循环"""
        if self._running:
            return
        self._running = True
        
        default_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
        exchange_manager = ExchangeManager.get_instance()
        
        while self._running and self.active_connections:
            try:
                for symbol in default_symbols:
                    ticker = await exchange_manager.fetch_ticker(symbol)
                    await self.broadcast_ticker(ticker)
                await asyncio.sleep(5)  # 每5秒更新一次
            except Exception as e:
                logger.error(f"行情推送错误: {e}")
                await asyncio.sleep(10)
        
        self._running = False
    
    def stop_streaming(self):
        self._running = False


market_stream_manager = MarketStreamManager()


@app.websocket("/api/market/stream")
async def websocket_market_stream(websocket: WebSocket):
    """实时行情 WebSocket 流
    
    连接后发送订阅消息:
    {"action": "subscribe", "symbols": ["BTC/USDT", "ETH/USDT"]}
    """
    await market_stream_manager.connect(websocket)
    
    # 启动行情推送
    if not market_stream_manager._running:
        asyncio.create_task(market_stream_manager.start_streaming())
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe":
                symbols = data.get("symbols", [])
                await market_stream_manager.subscribe(websocket, symbols)
            elif action == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        market_stream_manager.disconnect(websocket)


# ============================================
# 路由 - Trading Plans (交易计划)
# ============================================

class TradingPlanCreate(BaseModel):
    """创建交易计划请求"""
    name: str
    strategy_id: Optional[str] = None
    target_symbols: list[str]
    allocation_usd: float
    risk_limit_usd: float
    description: Optional[str] = None


class TradingPlanInfo(BaseModel):
    """交易计划信息"""
    id: str
    name: str
    author_agent_id: str
    strategy_id: Optional[str]
    target_symbols: list[str]
    allocation_usd: float
    risk_limit_usd: float
    current_state: str
    simulation_results: Optional[dict] = None
    approval_by_chairman: bool = False
    created_at: datetime
    updated_at: datetime


class TradeExecutionInfo(BaseModel):
    """交易执行信息"""
    id: str
    plan_id: str
    symbol: str
    side: str
    order_type: str
    amount: float
    price: Optional[float]
    filled_amount: float
    filled_price: Optional[float]
    status: str
    created_at: datetime


@app.get("/api/trading/plans", response_model=list[TradingPlanInfo], tags=["Trading"])
async def list_trading_plans(
    state: Optional[str] = Query(None, description="过滤状态"),
    limit: int = Query(50, ge=1, le=100),
):
    """获取交易计划列表"""
    # TODO: 从数据库获取
    return [
        TradingPlanInfo(
            id="TP-001",
            name="BTC 动量策略执行",
            author_agent_id="head_trader",
            strategy_id="EXP_20260115_001",
            target_symbols=["BTC/USDT"],
            allocation_usd=50000,
            risk_limit_usd=5000,
            current_state="MONITORING",
            simulation_results={"sharpe": 1.85, "max_dd": -0.12},
            approval_by_chairman=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        TradingPlanInfo(
            id="TP-002",
            name="ETH 均值回归建仓",
            author_agent_id="head_trader",
            strategy_id="EXP_20260115_002",
            target_symbols=["ETH/USDT"],
            allocation_usd=30000,
            risk_limit_usd=3000,
            current_state="PENDING_CHAIRMAN_APPROVAL",
            simulation_results={"sharpe": 1.42, "max_dd": -0.08},
            approval_by_chairman=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


@app.post("/api/trading/plans", tags=["Trading"])
async def create_trading_plan(plan: TradingPlanCreate):
    """创建交易计划"""
    # TODO: 调用 TradingTools 创建计划
    return {
        "id": f"TP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "status": "DRAFT",
        "message": "交易计划创建成功，请完成模拟测试后提交审批",
    }


@app.get("/api/trading/plans/{plan_id}", response_model=TradingPlanInfo, tags=["Trading"])
async def get_trading_plan(plan_id: str):
    """获取交易计划详情"""
    return TradingPlanInfo(
        id=plan_id,
        name="BTC 动量策略执行",
        author_agent_id="head_trader",
        strategy_id="EXP_20260115_001",
        target_symbols=["BTC/USDT"],
        allocation_usd=50000,
        risk_limit_usd=5000,
        current_state="MONITORING",
        simulation_results={"sharpe": 1.85, "max_dd": -0.12},
        approval_by_chairman=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@app.post("/api/trading/plans/{plan_id}/simulate", tags=["Trading"])
async def simulate_trading_plan(plan_id: str):
    """执行交易计划模拟"""
    # TODO: 调用 TradingTools.simulate_trade
    return {
        "success": True,
        "plan_id": plan_id,
        "simulation_results": {
            "sharpe": 1.65,
            "max_dd": -0.10,
            "win_rate": 0.58,
            "avg_return": 0.023,
            "trades_count": 15,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/trading/plans/{plan_id}/submit", tags=["Trading"])
async def submit_trading_plan(plan_id: str):
    """提交交易计划等待审批"""
    return {
        "success": True,
        "plan_id": plan_id,
        "new_state": "PENDING_CHAIRMAN_APPROVAL",
        "message": "交易计划已提交，等待董事长审批",
    }


@app.post("/api/trading/plans/{plan_id}/approve", tags=["Trading"])
async def approve_trading_plan(
    plan_id: str,
    approved: bool = True,
    comments: str = "",
):
    """董事长审批交易计划"""
    if approved:
        return {
            "success": True,
            "plan_id": plan_id,
            "new_state": "APPROVED",
            "message": "交易计划已批准，可以开始执行",
        }
    else:
        return {
            "success": True,
            "plan_id": plan_id,
            "new_state": "REJECTED",
            "message": f"交易计划被拒绝: {comments}",
        }


@app.get("/api/trading/executions", response_model=list[TradeExecutionInfo], tags=["Trading"])
async def list_trade_executions(
    plan_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    """获取交易执行记录"""
    return [
        TradeExecutionInfo(
            id="TE-001",
            plan_id="TP-001",
            symbol="BTC/USDT",
            side="buy",
            order_type="market",
            amount=0.5,
            price=None,
            filled_amount=0.5,
            filled_price=94500,
            status="FILLED",
            created_at=datetime.utcnow(),
        ),
    ]


# ============================================
# 路由 - Approvals (审批队列)
# ============================================

class ApprovalItemCreate(BaseModel):
    """创建审批项请求"""
    approval_type: str  # trading, hiring, strategy, experiment, meeting
    title: str
    description: str
    urgency: str = "normal"
    data: Optional[dict] = None


class ApprovalItemInfo(BaseModel):
    """审批项信息"""
    id: str
    approval_type: str
    title: str
    description: str
    requester: str
    department: str
    urgency: str
    status: str
    data: Optional[dict] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


@app.get("/api/approvals/pending", tags=["Approvals"])
async def get_pending_approvals_list():
    """获取待审批列表（前端用）"""
    try:
        approvals = await db.get_pending_approvals()
        return {
            "approvals": [
                {
                    "id": a["id"],
                    "title": a["title"],
                    "type": a["type"],
                    "urgency": a.get("urgency", "normal"),
                    "from": a.get("requester_name") or a.get("requester", "unknown")
                }
                for a in approvals
            ]
        }
    except Exception as e:
        logger.warning(f"获取待审批失败: {e}")
        return {"approvals": []}


@app.get("/api/research/cycles", tags=["Research"])
async def get_research_cycles_list():
    """获取研究周期列表（前端用）"""
    try:
        cycles = await db.get_research_cycles(limit=10)
        
        # 计算进度
        state_progress = {
            "IDEA_INTAKE": 10,
            "DATA_GATE": 25,
            "BACKTEST_GATE": 45,
            "ROBUSTNESS_GATE": 60,
            "RISK_SKEPTIC_GATE": 75,
            "IC_REVIEW": 85,
            "BOARD_PACK": 90,
            "BOARD_DECISION": 95,
            "ARCHIVE": 100,
        }
        
        return {
            "cycles": [
                {
                    "id": f"RC-{str(c['id'])[:8]}",
                    "name": c["name"],
                    "stage": c["current_state"],
                    "progress": state_progress.get(c["current_state"], 0)
                }
                for c in cycles
            ]
        }
    except Exception as e:
        logger.warning(f"获取研究周期失败: {e}")
        return {"cycles": []}


@app.get("/api/approvals", response_model=list[ApprovalItemInfo], tags=["Approvals"])
async def list_approvals(
    status: Optional[str] = Query(None, description="pending, approved, rejected"),
    approval_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
):
    """获取审批队列"""
    items = [
        ApprovalItemInfo(
            id="AP-001",
            approval_type="trading",
            title="BTC/USDT 做多交易计划",
            description="基于动量策略信号，建议建仓 BTC 30% 仓位",
            requester="head_trader",
            department="Trading Guild",
            urgency="high",
            status="pending",
            data={"symbol": "BTC/USDT", "target_weight": 0.3, "stop_loss": -0.05},
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
        ),
        ApprovalItemInfo(
            id="AP-002",
            approval_type="hiring",
            title="新增 ML Alpha 研究员",
            description="当前研究团队负载较高，建议招聘一名专注机器学习策略的研究员",
            requester="cpo",
            department="Meta-Governance",
            urgency="normal",
            status="pending",
            data={"role": "ML Alpha Researcher", "budget_impact": 5000},
            created_at=datetime.utcnow(),
        ),
        ApprovalItemInfo(
            id="AP-003",
            approval_type="strategy",
            title="波动率策略 v2 上线",
            description="策略已通过所有闸门审核，Sharpe 2.1，Max DD -15%",
            requester="cio",
            department="Investment Committee",
            urgency="normal",
            status="pending",
            data={"sharpe": 2.1, "max_dd": -0.15, "initial_allocation": 0.1},
            created_at=datetime.utcnow(),
        ),
    ]
    
    # 过滤
    if status:
        items = [i for i in items if i.status == status]
    if approval_type:
        items = [i for i in items if i.approval_type == approval_type]
    
    return items[:limit]


@app.get("/api/approvals/pending/count", tags=["Approvals"])
async def get_pending_approvals_count():
    """获取待审批数量"""
    return {
        "total": 3,
        "urgent": 1,
        "by_type": {
            "trading": 1,
            "hiring": 1,
            "strategy": 1,
        },
    }


@app.post("/api/approvals/{approval_id}/approve", tags=["Approvals"])
async def approve_item(
    approval_id: str,
    approved: bool = True,
    comments: str = "",
):
    """审批项目"""
    return {
        "success": True,
        "approval_id": approval_id,
        "new_status": "approved" if approved else "rejected",
        "message": "审批完成",
    }


# ============================================
# 路由 - Reports (增强版)
# ============================================

class ReportCreate(BaseModel):
    """创建报告请求"""
    report_type: str  # board_pack, research, trading, compliance, weekly
    title: str
    related_entity_id: Optional[str] = None


class ReportInfo(BaseModel):
    """报告信息"""
    id: str
    report_type: str
    title: str
    author: str
    summary: Optional[str] = None
    status: str
    created_at: datetime
    pdf_path: Optional[str] = None


@app.get("/api/reports/types", tags=["Reports"])
async def get_report_types():
    """获取报告类型列表"""
    return [
        {"id": "board_pack", "name": "董事会报告", "description": "策略上线审批报告"},
        {"id": "research", "name": "研究报告", "description": "策略研究详细报告"},
        {"id": "trading", "name": "交易报告", "description": "交易执行报告"},
        {"id": "compliance", "name": "合规报告", "description": "每日合规审计报告"},
        {"id": "weekly", "name": "周报", "description": "周度董事会汇报"},
    ]


@app.post("/api/reports/generate", tags=["Reports"])
async def generate_report(request: ReportCreate):
    """生成报告"""
    report_id = f"RPT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "id": report_id,
        "status": "generating",
        "message": f"正在生成 {request.report_type} 报告...",
        "estimated_time": "30 seconds",
    }


@app.get("/api/reports/{report_id}/download", tags=["Reports"])
async def download_report(report_id: str, format: str = Query("pdf")):
    """下载报告"""
    # TODO: 实际生成和返回文件
    return {
        "id": report_id,
        "format": format,
        "download_url": f"/api/reports/{report_id}/file.{format}",
        "message": "报告生成中，请稍后刷新获取下载链接",
    }


# ============================================
# 路由 - Research Cycles (增强版)
# ============================================

class ResearchCycleCreate(BaseModel):
    """创建研究周期请求"""
    name: str
    strategy_type: str
    description: Optional[str] = None
    team: str


@app.post("/api/pipeline", tags=["Pipeline"])
async def create_research_cycle(cycle: ResearchCycleCreate):
    """创建研究周期"""
    cycle_id = f"RC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return {
        "id": cycle_id,
        "state": "IDEA_INTAKE",
        "message": "研究周期已创建，请开始数据准备阶段",
    }


@app.post("/api/pipeline/{cycle_id}/advance", tags=["Pipeline"])
async def advance_cycle(cycle_id: str, comments: str = ""):
    """推进研究周期到下一阶段"""
    # TODO: 调用 StateMachine.advance
    return {
        "success": True,
        "cycle_id": cycle_id,
        "new_state": "DATA_GATE",
        "message": "研究周期已推进到数据闸门阶段",
    }


@app.post("/api/pipeline/{cycle_id}/reject", tags=["Pipeline"])
async def reject_cycle(cycle_id: str, reason: str):
    """拒绝研究周期（回退或归档）"""
    return {
        "success": True,
        "cycle_id": cycle_id,
        "new_state": "ARCHIVE",
        "message": f"研究周期已归档: {reason}",
    }


# ============================================
# 路由 - Agent Messages (Agent 通信)
# ============================================

class AgentMessage(BaseModel):
    """Agent 消息"""
    from_agent: str
    to_agent: Optional[str] = None
    subject: str
    content: str
    message_type: str = "text"


@app.get("/api/agents/{agent_id}/messages", tags=["Agents"])
async def get_agent_messages(
    agent_id: str,
    limit: int = Query(50, ge=1, le=100),
):
    """获取 Agent 的消息列表"""
    return [
        {
            "id": "msg-001",
            "from_agent": "alpha_a_lead",
            "to_agent": agent_id,
            "subject": "策略评审请求",
            "content": "BTC 动量策略已完成回测，请安排投委会评审",
            "created_at": datetime.utcnow().isoformat(),
        },
    ]


@app.post("/api/agents/{agent_id}/messages", tags=["Agents"])
async def send_agent_message(agent_id: str, message: AgentMessage):
    """发送消息给 Agent"""
    # TODO: 通过 MessageBus 发送
    return {
        "success": True,
        "message_id": f"msg-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "status": "delivered",
    }


# ============================================
# 路由 - Intelligence (市场情报)
# ============================================

@app.get("/api/intelligence/news", tags=["Intelligence"])
async def get_news(
    keywords: Optional[str] = Query(None, description="关键词，逗号分隔"),
    limit: int = Query(20, ge=1, le=50),
    hours: int = Query(24, ge=1, le=168),
):
    """获取财经新闻"""
    try:
        intel_tools = get_intelligence_tools()
        keyword_list = keywords.split(",") if keywords else None
        result = await intel_tools.fetch_news(
            keywords=keyword_list,
            limit=limit,
            since_hours=hours,
        )
        return result
    except Exception as e:
        logger.error(f"获取新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/sentiment", tags=["Intelligence"])
async def get_sentiment(
    asset: Optional[str] = Query(None, description="资产符号"),
):
    """获取市场情绪分析"""
    try:
        intel_tools = get_intelligence_tools()
        result = await intel_tools.analyze_sentiment(asset=asset)
        return result
    except Exception as e:
        logger.error(f"获取情绪分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/social", tags=["Intelligence"])
async def get_social_monitoring(
    keywords: Optional[str] = Query(None, description="关键词，逗号分隔"),
    platforms: Optional[str] = Query(None, description="平台，逗号分隔"),
    limit: int = Query(20, ge=1, le=50),
):
    """获取社交媒体监控"""
    try:
        intel_tools = get_intelligence_tools()
        keyword_list = keywords.split(",") if keywords else None
        platform_list = platforms.split(",") if platforms else None
        result = await intel_tools.monitor_social(
            platforms=platform_list,
            keywords=keyword_list,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error(f"获取社交媒体监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/onchain/{asset}", tags=["Intelligence"])
async def get_onchain_analysis(asset: str):
    """获取链上数据分析"""
    try:
        intel_tools = get_intelligence_tools()
        result = await intel_tools.get_onchain_data(asset=asset.upper())
        return result
    except Exception as e:
        logger.error(f"获取链上数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/fear-greed", tags=["Intelligence"])
async def get_fear_greed():
    """获取恐惧贪婪指数"""
    try:
        intel_tools = get_intelligence_tools()
        result = await intel_tools.get_fear_greed_index()
        return result
    except Exception as e:
        logger.error(f"获取恐惧贪婪指数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/alerts", tags=["Intelligence"])
async def get_alerts(
    asset: Optional[str] = Query(None, description="资产符号"),
    types: Optional[str] = Query(None, description="预警类型，逗号分隔"),
):
    """获取市场预警"""
    try:
        intel_tools = get_intelligence_tools()
        type_list = types.split(",") if types else None
        result = await intel_tools.get_market_alerts(
            asset=asset,
            alert_types=type_list,
        )
        return result
    except Exception as e:
        logger.error(f"获取市场预警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 路由 - Performance (绩效评估)
# ============================================

@app.get("/api/performance/agents/{agent_id}", tags=["Performance"])
async def get_agent_performance(agent_id: str):
    """获取 Agent 绩效报告"""
    perf_system = get_performance_system()
    report = perf_system.generate_performance_report(agent_id)
    
    if "error" in report:
        # 创建一个示例记录卡
        from datetime import timedelta
        now = datetime.utcnow()
        scorecard = perf_system.create_scorecard(
            agent_id=agent_id,
            role_type="researcher",
            period_start=now - timedelta(days=30),
            period_end=now,
            job_level=JobLevel.INTERMEDIATE,
        )
        # 设置一些示例数据
        perf_system.update_kpi(agent_id, "strategy_proposals", 4)
        perf_system.update_kpi(agent_id, "backtest_sharpe_avg", 1.65)
        perf_system.update_kpi(agent_id, "pass_rate_robustness", 0.7)
        perf_system.update_kpi(agent_id, "data_quality_issues", 1)
        perf_system.update_kpi(agent_id, "collaboration_score", 0.85)
        perf_system.update_kpi(agent_id, "memory_contribution", 8)
        perf_system.calculate_performance(agent_id)
        report = perf_system.generate_performance_report(agent_id)
    
    return report


@app.get("/api/performance/leaderboard", tags=["Performance"])
async def get_leaderboard(team: Optional[str] = Query(None)):
    """获取绩效排行榜"""
    perf_system = get_performance_system()
    leaderboard = perf_system.get_team_leaderboard(team)
    
    # 如果没有数据，创建一些示例
    if not leaderboard:
        from datetime import timedelta
        now = datetime.utcnow()
        
        example_agents = [
            ("alpha_a_lead", "researcher", JobLevel.LEAD, 1.35),
            ("alpha_b_lead", "researcher", JobLevel.LEAD, 1.22),
            ("head_trader", "trader", JobLevel.DIRECTOR, 1.15),
            ("cro", "risk", JobLevel.C_LEVEL, 1.08),
            ("alpha_a_researcher_1", "researcher", JobLevel.INTERMEDIATE, 0.95),
        ]
        
        for agent_id, role, level, score_factor in example_agents:
            scorecard = perf_system.create_scorecard(
                agent_id=agent_id,
                role_type=role,
                period_start=now - timedelta(days=30),
                period_end=now,
                job_level=level,
            )
            # 设置 KPI 达到目标的一定比例
            for kpi in scorecard.kpis:
                kpi.actual = kpi.target * score_factor
            perf_system.calculate_performance(agent_id)
        
        leaderboard = perf_system.get_team_leaderboard(team)
    
    return {
        "leaderboard": leaderboard,
        "team": team,
        "count": len(leaderboard),
        "generated_at": datetime.utcnow().isoformat(),
    }


@app.post("/api/performance/feedback", tags=["Performance"])
async def add_performance_feedback(
    agent_id: str,
    from_agent: str,
    feedback_type: str,
    content: str,
    context: Optional[str] = None,
):
    """添加绩效反馈"""
    perf_system = get_performance_system()
    perf_system.add_feedback(
        agent_id=agent_id,
        from_agent=from_agent,
        feedback_type=feedback_type,
        content=content,
        context=context,
    )
    return {"success": True, "message": "反馈已添加"}


@app.get("/api/performance/promotion-check/{agent_id}", tags=["Performance"])
async def check_promotion(agent_id: str):
    """检查晋升资格"""
    perf_system = get_performance_system()
    result = perf_system.check_promotion_eligibility(agent_id)
    return result


@app.get("/api/performance/kpi-templates", tags=["Performance"])
async def get_kpi_templates():
    """获取 KPI 模板列表"""
    perf_system = get_performance_system()
    templates = {}
    for role_type in ["researcher", "risk", "trader", "intelligence", "governance", "default"]:
        templates[role_type] = [
            {
                "name": kpi.name,
                "description": kpi.description,
                "weight": kpi.weight,
                "target": kpi.target,
                "unit": kpi.unit,
                "higher_is_better": kpi.higher_is_better,
            }
            for kpi in perf_system.get_kpi_template(role_type)
        ]
    return templates


# ============================================
# 路由 - Topic Meeting (议题驱动会议)
# ============================================

class TopicProposal(BaseModel):
    """议题提案"""
    title: str
    description: str
    category: str
    priority: str = "normal"
    suggested_participants: list[str] = []


@app.get("/api/topics", tags=["Topics"])
async def list_topics(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    proposer: Optional[str] = Query(None),
):
    """获取议题列表"""
    topic_system = get_topic_meeting_system()
    
    cat = TopicCategory(category) if category else None
    stat = TopicStatus(status) if status else None
    
    topics = topic_system.get_active_topics(
        category=cat,
        status=stat,
        proposer_id=proposer,
    )
    
    return {
        "count": len(topics),
        "topics": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "category": t.category.value,
                "priority": t.priority.value,
                "status": t.status.value,
                "proposer_id": t.proposer_id,
                "second_count": t.second_count,
                "required_seconds": t.required_seconds,
                "is_seconded": t.is_seconded,
                "scheduled_at": t.scheduled_at.isoformat() if t.scheduled_at else None,
                "created_at": t.created_at.isoformat(),
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            }
            for t in topics
        ],
    }


@app.post("/api/topics", tags=["Topics"])
async def propose_topic(proposal: TopicProposal, proposer_id: str = "chairman"):
    """提出新议题"""
    topic_system = get_topic_meeting_system()
    
    topic = topic_system.propose_topic(
        proposer_id=proposer_id,
        proposer_department="chairman",
        title=proposal.title,
        description=proposal.description,
        category=TopicCategory(proposal.category),
        priority=TopicPriority(proposal.priority),
        suggested_participants=proposal.suggested_participants,
    )
    
    return {
        "success": True,
        "topic_id": topic.id,
        "status": topic.status.value,
        "required_seconds": topic.required_seconds,
        "message": "议题已提出" if topic.required_seconds > 0 else "议题已安排会议",
    }


@app.get("/api/topics/{topic_id}", tags=["Topics"])
async def get_topic(topic_id: str):
    """获取议题详情"""
    topic_system = get_topic_meeting_system()
    topic = topic_system.get_topic(topic_id)
    
    if not topic:
        raise HTTPException(status_code=404, detail="议题不存在")
    
    return {
        "id": topic.id,
        "title": topic.title,
        "description": topic.description,
        "category": topic.category.value,
        "priority": topic.priority.value,
        "status": topic.status.value,
        "proposer_id": topic.proposer_id,
        "proposer_department": topic.proposer_department,
        "seconds": [
            {
                "agent_id": s.agent_id,
                "reason": s.reason,
                "timestamp": s.timestamp.isoformat(),
            }
            for s in topic.seconds
        ],
        "second_count": topic.second_count,
        "required_seconds": topic.required_seconds,
        "is_seconded": topic.is_seconded,
        "suggested_participants": topic.suggested_participants,
        "actual_participants": topic.actual_participants,
        "scheduled_at": topic.scheduled_at.isoformat() if topic.scheduled_at else None,
        "created_at": topic.created_at.isoformat(),
        "updated_at": topic.updated_at.isoformat(),
        "expires_at": topic.expires_at.isoformat() if topic.expires_at else None,
        "resolution": topic.resolution,
        "action_items": topic.action_items,
    }


@app.post("/api/topics/{topic_id}/second", tags=["Topics"])
async def second_topic(
    topic_id: str,
    agent_id: str,
    reason: str,
    agent_level: str = "intermediate",
):
    """附议议题"""
    topic_system = get_topic_meeting_system()
    result = topic_system.second_topic(
        topic_id=topic_id,
        agent_id=agent_id,
        reason=reason,
        agent_level=agent_level,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/topics/{topic_id}/resolve", tags=["Topics"])
async def resolve_topic(
    topic_id: str,
    resolution: str,
    action_items: list[dict] = None,
):
    """解决议题"""
    topic_system = get_topic_meeting_system()
    result = topic_system.resolve_topic(
        topic_id=topic_id,
        resolution=resolution,
        action_items=action_items or [],
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/topics/{topic_id}/reject", tags=["Topics"])
async def reject_topic(
    topic_id: str,
    reason: str,
    rejector_id: str = "chairman",
):
    """拒绝议题"""
    topic_system = get_topic_meeting_system()
    result = topic_system.reject_topic(
        topic_id=topic_id,
        reason=reason,
        rejector_id=rejector_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.get("/api/topics/statistics", tags=["Topics"])
async def get_topic_statistics():
    """获取议题统计"""
    topic_system = get_topic_meeting_system()
    return topic_system.get_statistics()


# ============================================
# 路由 - Intention (Agent 意愿系统)
# ============================================

class IntentionRequest(BaseModel):
    """意愿请求"""
    agent_id: str
    agent_name: str
    department: str
    intention_type: str
    title: str
    description: str
    priority: str = "normal"
    context: dict = {}
    target_agents: list[str] = []
    autonomous_scope: str = ""


@app.get("/api/intentions", tags=["Intentions"])
async def list_intentions(
    agent_id: Optional[str] = Query(None),
    intention_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
):
    """获取意愿列表"""
    from orchestrator.intention import IntentionStatus
    
    intention_system = get_intention_system()
    
    int_type = IntentionType(intention_type) if intention_type else None
    int_status = IntentionStatus(status) if status else None
    int_priority = IntentionPriority(priority) if priority else None
    
    intentions = intention_system.get_agent_intentions(
        agent_id=agent_id,
        intention_type=int_type,
        status=int_status,
        priority=int_priority,
    )
    
    return {
        "count": len(intentions),
        "intentions": [
            {
                "id": i.id,
                "agent_id": i.agent_id,
                "agent_name": i.agent_name,
                "department": i.department,
                "intention_type": i.intention_type.value,
                "priority": i.priority.value,
                "status": i.status.value,
                "title": i.title,
                "description": i.description,
                "target_agents": i.target_agents,
                "autonomous_approved": i.autonomous_approved,
                "created_at": i.created_at.isoformat(),
                "expires_at": i.expires_at.isoformat() if i.expires_at else None,
            }
            for i in intentions
        ],
    }


@app.post("/api/intentions", tags=["Intentions"])
async def create_intention(request: IntentionRequest):
    """创建意愿"""
    intention_system = get_intention_system()
    
    intention = intention_system.express_intention(
        agent_id=request.agent_id,
        agent_name=request.agent_name,
        department=request.department,
        intention_type=IntentionType(request.intention_type),
        title=request.title,
        description=request.description,
        priority=IntentionPriority(request.priority),
        context=request.context,
        target_agents=request.target_agents,
        autonomous_scope=request.autonomous_scope,
    )
    
    return {
        "success": True,
        "intention_id": intention.id,
        "status": intention.status.value,
        "autonomous_approved": intention.autonomous_approved,
    }


@app.get("/api/intentions/triggers", tags=["Intentions"])
async def get_risk_triggers():
    """获取风险触发器列表"""
    intention_system = get_intention_system()
    triggers = intention_system.get_triggers()
    
    return {
        "count": len(triggers),
        "triggers": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "metric": t.metric,
                "operator": t.operator,
                "threshold": t.threshold,
                "action_type": t.action_type,
                "target_agents": t.target_agents,
                "priority": t.priority.value,
                "enabled": t.enabled,
                "last_triggered": t.last_triggered.isoformat() if t.last_triggered else None,
                "trigger_count": t.trigger_count,
            }
            for t in triggers
        ],
    }


@app.get("/api/intentions/statistics", tags=["Intentions"])
async def get_intention_statistics():
    """获取意愿统计"""
    intention_system = get_intention_system()
    return intention_system.get_statistics()


@app.get("/api/intentions/{intention_id}", tags=["Intentions"])
async def get_intention(intention_id: str):
    """获取意愿详情"""
    intention_system = get_intention_system()
    intention = intention_system.get_intention(intention_id)
    
    if not intention:
        raise HTTPException(status_code=404, detail="意愿不存在")
    
    return {
        "id": intention.id,
        "agent_id": intention.agent_id,
        "agent_name": intention.agent_name,
        "department": intention.department,
        "intention_type": intention.intention_type.value,
        "priority": intention.priority.value,
        "status": intention.status.value,
        "title": intention.title,
        "description": intention.description,
        "context": intention.context,
        "target_agents": intention.target_agents,
        "trigger_type": intention.trigger_type,
        "autonomous_scope": intention.autonomous_scope,
        "autonomous_approved": intention.autonomous_approved,
        "created_at": intention.created_at.isoformat(),
        "updated_at": intention.updated_at.isoformat(),
        "expires_at": intention.expires_at.isoformat() if intention.expires_at else None,
        "response": intention.response,
        "action_taken": intention.action_taken,
    }


@app.post("/api/intentions/{intention_id}/respond", tags=["Intentions"])
async def respond_to_intention(
    intention_id: str,
    action: str,  # approve, reject, acknowledge
    responder_id: str = "chairman",
    response: str = None,
):
    """回应意愿"""
    intention_system = get_intention_system()
    result = intention_system.respond_to_intention(
        intention_id=intention_id,
        responder_id=responder_id,
        action=action,
        response=response,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/intentions/{intention_id}/complete", tags=["Intentions"])
async def complete_intention(
    intention_id: str,
    action_taken: str,
):
    """完成意愿"""
    intention_system = get_intention_system()
    result = intention_system.complete_intention(
        intention_id=intention_id,
        action_taken=action_taken,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/intentions/triggers/{trigger_id}/toggle", tags=["Intentions"])
async def toggle_trigger(trigger_id: str, enabled: bool):
    """启用/禁用触发器"""
    intention_system = get_intention_system()
    result = intention_system.toggle_trigger(trigger_id, enabled)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/intentions/check-triggers", tags=["Intentions"])
async def check_risk_triggers(metrics: dict):
    """检查风险触发器"""
    intention_system = get_intention_system()
    triggered = intention_system.check_risk_triggers(metrics)
    
    return {
        "triggered_count": len(triggered),
        "triggered_intentions": [
            {
                "id": i.id,
                "title": i.title,
                "priority": i.priority.value,
            }
            for i in triggered
        ],
    }


# ============================================
# 路由 - Risk Governance (风险策略治理)
# ============================================

class RuleProposal(BaseModel):
    """规则提案"""
    name: str
    description: str
    rule_type: str
    parameters: dict
    effective_days: int = 30


class RuleVote(BaseModel):
    """规则投票"""
    voter_id: str
    voter_name: str
    department: str
    vote: str  # approve, reject, abstain
    reason: str


@app.get("/api/governance/rules", tags=["Governance"])
async def list_governance_rules(
    rule_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """获取风控规则列表"""
    gov_system = get_risk_governance_system()
    
    rt = RuleType(rule_type) if rule_type else None
    rs = RuleStatus(status) if status else None
    
    rules = gov_system.get_all_rules(rule_type=rt, status=rs)
    
    return {
        "count": len(rules),
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "rule_type": r.rule_type.value,
                "status": r.status.value,
                "parameters": r.parameters,
                "proposer_id": r.proposer_id,
                "proposer_name": r.proposer_name,
                "approval_rate": round(r.approval_rate * 100, 1),
                "votes_count": len(r.votes),
                "required_voters": r.required_voters,
                "created_at": r.created_at.isoformat(),
                "effective_from": r.effective_from.isoformat() if r.effective_from else None,
            }
            for r in rules
        ],
    }


@app.get("/api/governance/rules/active", tags=["Governance"])
async def get_active_rules():
    """获取生效中的规则"""
    gov_system = get_risk_governance_system()
    rules = gov_system.get_active_rules()
    
    return {
        "count": len(rules),
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "rule_type": r.rule_type.value,
                "parameters": r.parameters,
                "effective_from": r.effective_from.isoformat() if r.effective_from else None,
            }
            for r in rules
        ],
    }


@app.post("/api/governance/rules", tags=["Governance"])
async def propose_rule(
    proposal: RuleProposal,
    proposer_id: str = "chairman",
    proposer_name: str = "董事长",
):
    """提议新规则"""
    gov_system = get_risk_governance_system()
    
    rule = gov_system.propose_rule(
        proposer_id=proposer_id,
        proposer_name=proposer_name,
        name=proposal.name,
        description=proposal.description,
        rule_type=RuleType(proposal.rule_type),
        parameters=proposal.parameters,
        effective_days=proposal.effective_days,
    )
    
    return {
        "success": True,
        "rule_id": rule.id,
        "status": rule.status.value,
        "required_voters": rule.required_voters,
    }


@app.get("/api/governance/rules/{rule_id}", tags=["Governance"])
async def get_rule_detail(rule_id: str):
    """获取规则详情"""
    gov_system = get_risk_governance_system()
    rule = gov_system.get_rule(rule_id)
    
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type.value,
        "status": rule.status.value,
        "parameters": rule.parameters,
        "proposer_id": rule.proposer_id,
        "proposer_name": rule.proposer_name,
        "votes": [
            {
                "voter_id": v.voter_id,
                "voter_name": v.voter_name,
                "department": v.department,
                "vote": v.vote.value,
                "reason": v.reason,
                "weight": v.weight,
                "timestamp": v.timestamp.isoformat(),
            }
            for v in rule.votes
        ],
        "approval_rate": round(rule.approval_rate * 100, 1),
        "required_approval_rate": round(rule.required_approval_rate * 100, 1),
        "required_voters": rule.required_voters,
        "created_at": rule.created_at.isoformat(),
        "updated_at": rule.updated_at.isoformat(),
        "effective_from": rule.effective_from.isoformat() if rule.effective_from else None,
        "effective_until": rule.effective_until.isoformat() if rule.effective_until else None,
        "resolution": rule.resolution,
    }


@app.post("/api/governance/rules/{rule_id}/vote", tags=["Governance"])
async def vote_on_rule(rule_id: str, vote: RuleVote):
    """对规则投票"""
    gov_system = get_risk_governance_system()
    
    result = gov_system.vote_on_rule(
        rule_id=rule_id,
        voter_id=vote.voter_id,
        voter_name=vote.voter_name,
        department=vote.department,
        vote_type=VoteType(vote.vote),
        reason=vote.reason,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/governance/rules/{rule_id}/activate", tags=["Governance"])
async def activate_rule(rule_id: str):
    """激活规则"""
    gov_system = get_risk_governance_system()
    result = gov_system.activate_rule(rule_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/governance/rules/{rule_id}/suspend", tags=["Governance"])
async def suspend_rule(rule_id: str, reason: str, suspender_id: str = "chairman"):
    """暂停规则"""
    gov_system = get_risk_governance_system()
    result = gov_system.suspend_rule(rule_id, reason, suspender_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@app.post("/api/governance/compliance-check", tags=["Governance"])
async def check_compliance(position_data: dict):
    """检查合规性"""
    gov_system = get_risk_governance_system()
    return gov_system.check_compliance(position_data)


@app.get("/api/governance/decisions", tags=["Governance"])
async def get_governance_decisions(rule_id: Optional[str] = Query(None)):
    """获取治理决议"""
    gov_system = get_risk_governance_system()
    decisions = gov_system.get_decisions(rule_id)
    
    return {
        "count": len(decisions),
        "decisions": [
            {
                "id": d.id,
                "rule_id": d.rule_id,
                "decision_type": d.decision_type,
                "summary": d.summary,
                "rationale": d.rationale,
                "participants": d.participants,
                "decided_at": d.decided_at.isoformat(),
                "executed": d.executed,
            }
            for d in decisions
        ],
    }


@app.get("/api/governance/statistics", tags=["Governance"])
async def get_governance_statistics():
    """获取治理统计"""
    gov_system = get_risk_governance_system()
    return gov_system.get_statistics()


# ============================================
# 路由 - Agent Loop (Agent 主动行为)
# ============================================

@app.get("/api/agent-loop/status", tags=["Agent Loop"])
async def get_agents_loop_status(agent_id: Optional[str] = Query(None)):
    """获取 Agent 运行状态"""
    agent_loop = get_agent_loop()
    return agent_loop.get_agent_status(agent_id)


@app.get("/api/agent-loop/activities", tags=["Agent Loop"])
async def get_agent_activities(
    limit: int = Query(50, ge=1, le=200),
    agent_id: Optional[str] = Query(None),
):
    """获取 Agent 最近活动"""
    agent_loop = get_agent_loop()
    return {
        "count": len(agent_loop.get_recent_activities(limit, agent_id)),
        "activities": agent_loop.get_recent_activities(limit, agent_id),
    }


@app.get("/api/agent-loop/discoveries", tags=["Agent Loop"])
async def get_agent_discoveries(agent_id: Optional[str] = Query(None)):
    """获取 Agent 发现的策略"""
    agent_loop = get_agent_loop()
    discoveries = agent_loop.get_discoveries(agent_id)
    return {
        "count": len(discoveries),
        "discoveries": discoveries,
    }


@app.post("/api/agent-loop/register", tags=["Agent Loop"])
async def register_agent_to_loop(
    agent_id: str,
    agent_name: str,
    role: str,
    department: str,
):
    """注册 Agent 到循环"""
    agent_loop = get_agent_loop()
    agent_loop.register_agent(agent_id, agent_name, role, department)
    return {"success": True, "agent_id": agent_id}


@app.post("/api/agent-loop/initialize", tags=["Agent Loop"])
async def initialize_default_agents():
    """初始化默认 Agents"""
    agent_loop = get_agent_loop()
    
    default_agents = [
        ("alpha_a_lead", "Alpha A 组长", "researcher", "research_guild"),
        ("alpha_a_researcher_1", "Alpha A 研究员1", "researcher", "research_guild"),
        ("alpha_b_lead", "Alpha B 组长", "researcher", "research_guild"),
        ("cro", "首席风险官", "risk", "risk_guild"),
        ("skeptic", "质疑者", "risk", "risk_guild"),
        ("head_trader", "交易主管", "trader", "trading_guild"),
        ("head_of_intelligence", "情报总监", "intelligence", "intelligence_guild"),
        ("news_analyst", "新闻分析师", "intelligence", "intelligence_guild"),
    ]
    
    for agent_id, name, role, dept in default_agents:
        agent_loop.register_agent(agent_id, name, role, dept)
    
    return {
        "success": True,
        "registered_count": len(default_agents),
        "agents": [a[0] for a in default_agents],
    }


@app.get("/api/intelligence/summary", tags=["Intelligence"])
async def get_intelligence_summary():
    """获取情报总览"""
    try:
        intel_tools = get_intelligence_tools()
        
        # 并行获取所有情报
        news_task = intel_tools.fetch_news(limit=5)
        sentiment_task = intel_tools.analyze_sentiment(asset="BTC")
        fear_greed_task = intel_tools.get_fear_greed_index()
        alerts_task = intel_tools.get_market_alerts()
        
        import asyncio
        news, sentiment, fear_greed, alerts = await asyncio.gather(
            news_task, sentiment_task, fear_greed_task, alerts_task
        )
        
        return {
            "latest_news": news["news"][:3],
            "market_sentiment": sentiment,
            "fear_greed": fear_greed,
            "active_alerts": alerts["alerts"][:5],
            "summary": {
                "news_count": news["count"],
                "alert_count": alerts["count"],
                "overall_mood": sentiment["sentiment_label"],
                "fear_greed_value": fear_greed["value"],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"获取情报总览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Agent 系统控制
# ============================================

import subprocess
import signal

# 全局状态
_agent_process = None
_token_stats = {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_requests": 0,
    "session_start": None,
    "last_updated": None,
}

# LLM 价格配置 (2026年1月价格)
LLM_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},  # per million tokens
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-4.5-opus": {"input": 5.00, "output": 25.00},
    "claude-4.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3.5-haiku": {"input": 0.80, "output": 4.00},
    "deepseek-v3": {"input": 0.27, "output": 1.10},
    "antigravity": {"input": 1.00, "output": 3.00},  # 估算
}


@app.get("/api/system/token-stats", tags=["System"])
async def get_token_stats():
    """获取 Token 使用统计"""
    global _token_stats
    
    db_stats = None
    
    # 从数据库获取实际 token 使用
    try:
        async with db.get_connection() as conn:
            # 先尝试从 llm_usage 表统计
            db_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_calls,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(CASE WHEN thinking_enabled THEN 1 END) as thinking_calls
                FROM llm_usage
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
    except Exception as e:
        logger.warning(f"llm_usage 表查询失败 (可能不存在): {e}")
    
    # 如果数据库有数据，使用数据库数据
    if db_stats and db_stats["total_calls"] > 0:
        total_input = int(db_stats["input_tokens"])
        total_output = int(db_stats["output_tokens"])
        total_cost = float(db_stats["total_cost"])
        total_requests = int(db_stats["total_calls"])
        thinking_calls = int(db_stats["thinking_calls"] or 0)
    else:
        # 使用内存中的统计（兜底）
        total_input = _token_stats["total_input_tokens"]
        total_output = _token_stats["total_output_tokens"]
        total_requests = _token_stats["total_requests"]
        thinking_calls = 0
        # 计算成本
        pricing = LLM_PRICING.get("antigravity", {"input": 1.0, "output": 3.0})
        total_cost = (total_input / 1_000_000) * pricing["input"] + (total_output / 1_000_000) * pricing["output"]
    
    # 计算成本细分
    pricing = LLM_PRICING.get("antigravity", {"input": 1.0, "output": 3.0})
    input_cost = (total_input / 1_000_000) * pricing["input"]
    output_cost = (total_output / 1_000_000) * pricing["output"]
    
    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "total_requests": total_requests,
        "thinking_calls": thinking_calls,
        "estimated_cost_usd": round(total_cost, 4),
        "cost_breakdown": {
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
        },
        "pricing_model": "antigravity",
        "pricing_per_million": pricing,
    }


@app.get("/api/system/llm-pricing", tags=["System"])
async def get_llm_pricing():
    """获取 LLM 价格列表"""
    return {
        "pricing": LLM_PRICING,
        "currency": "USD",
        "unit": "per million tokens",
        "last_updated": "2026-01-14",
    }


class TokenUsageRequest(BaseModel):
    """Token 使用记录请求"""
    agent_id: Optional[str] = None
    model: str = "antigravity"
    input_tokens: int
    output_tokens: int
    thinking_enabled: bool = False
    request_type: Optional[str] = None
    latency_ms: Optional[int] = None


@app.post("/api/system/record-tokens", tags=["System"])
async def record_token_usage(req: TokenUsageRequest):
    """记录 Token 使用"""
    global _token_stats
    
    # 更新内存统计（兜底）
    _token_stats["total_input_tokens"] += req.input_tokens
    _token_stats["total_output_tokens"] += req.output_tokens
    _token_stats["total_requests"] += 1
    _token_stats["last_updated"] = datetime.utcnow().isoformat()
    
    # 计算成本
    pricing = LLM_PRICING.get(req.model, {"input": 1.0, "output": 3.0})
    input_cost = (req.input_tokens / 1_000_000) * pricing["input"]
    output_cost = (req.output_tokens / 1_000_000) * pricing["output"]
    
    # 写入数据库
    try:
        async with db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO llm_usage (
                    agent_id, model, input_tokens, output_tokens,
                    input_cost, output_cost, thinking_enabled,
                    request_type, latency_ms
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                req.agent_id, req.model, req.input_tokens, req.output_tokens,
                input_cost, output_cost, req.thinking_enabled,
                req.request_type, req.latency_ms,
            )
    except Exception as e:
        logger.warning(f"记录 token 使用到数据库失败: {e}")
    
    return {
        "success": True, 
        "total_tokens": req.input_tokens + req.output_tokens,
        "cost_usd": round(input_cost + output_cost, 6),
    }


@app.get("/api/system/agent-status", tags=["System"])
async def get_agent_system_status():
    """获取 Agent 系统运行状态"""
    global _agent_process
    
    is_running = _agent_process is not None and _agent_process.poll() is None
    
    return {
        "is_running": is_running,
        "pid": _agent_process.pid if is_running else None,
        "status": "running" if is_running else "stopped",
        "mode": "real" if is_running else None,
    }


@app.post("/api/system/start-agents", tags=["System"])
async def start_agent_system(mock: bool = False):
    """启动 Agent 系统"""
    global _agent_process
    
    # 检查是否已经在运行
    if _agent_process is not None and _agent_process.poll() is None:
        return {
            "success": False,
            "error": "Agent 系统已经在运行",
            "pid": _agent_process.pid,
        }
    
    try:
        # 构建命令
        cmd = ["python", "scripts/run_agents.py"]
        if mock:
            cmd.append("--mock")
        
        # 启动进程
        _agent_process = subprocess.Popen(
            cmd,
            cwd="/Users/noame/development/AiQuant",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        
        # 等待一下确认启动成功
        await asyncio.sleep(1)
        
        if _agent_process.poll() is not None:
            # 进程已经退出
            stdout, stderr = _agent_process.communicate()
            return {
                "success": False,
                "error": "Agent 系统启动失败",
                "stderr": stderr.decode()[:500] if stderr else None,
            }
        
        # 记录事件
        await db.create_event(
            event_type="system.agent_start",
            action=f"Agent 系统启动 ({'Mock 模式' if mock else '真实模式'})",
            details={"pid": _agent_process.pid, "mock": mock}
        )
        
        return {
            "success": True,
            "message": f"Agent 系统已启动 ({'Mock 模式' if mock else '真实模式'})",
            "pid": _agent_process.pid,
        }
        
    except Exception as e:
        logger.error(f"启动 Agent 系统失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@app.post("/api/system/stop-agents", tags=["System"])
async def stop_agent_system():
    """停止 Agent 系统"""
    global _agent_process
    
    if _agent_process is None or _agent_process.poll() is not None:
        return {
            "success": False,
            "error": "Agent 系统未在运行",
        }
    
    try:
        # 发送 SIGTERM
        import os
        os.killpg(os.getpgid(_agent_process.pid), signal.SIGTERM)
        
        # 等待进程结束
        _agent_process.wait(timeout=5)
        
        # 记录事件
        await db.create_event(
            event_type="system.agent_stop",
            action="Agent 系统停止",
            details={"pid": _agent_process.pid}
        )
        
        _agent_process = None
        
        return {
            "success": True,
            "message": "Agent 系统已停止",
        }
        
    except subprocess.TimeoutExpired:
        # 强制杀死
        os.killpg(os.getpgid(_agent_process.pid), signal.SIGKILL)
        _agent_process = None
        return {
            "success": True,
            "message": "Agent 系统已强制停止",
        }
    except Exception as e:
        logger.error(f"停止 Agent 系统失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@app.get("/api/system/cost-estimate", tags=["System"])
async def get_cost_estimate():
    """获取运行成本预估"""
    # 估算每个 Agent 每小时的 token 使用
    # 假设：每个 Agent 每分钟执行 1 次，每次平均 500 input + 200 output tokens
    agents_count = 34
    runs_per_hour = 60
    avg_input_per_run = 500
    avg_output_per_run = 200
    
    hourly_input = agents_count * runs_per_hour * avg_input_per_run
    hourly_output = agents_count * runs_per_hour * avg_output_per_run
    
    estimates = {}
    for model, pricing in LLM_PRICING.items():
        hourly_cost = (hourly_input / 1_000_000) * pricing["input"] + (hourly_output / 1_000_000) * pricing["output"]
        daily_cost = hourly_cost * 24
        monthly_cost = daily_cost * 30
        
        estimates[model] = {
            "hourly": round(hourly_cost, 2),
            "daily": round(daily_cost, 2),
            "monthly": round(monthly_cost, 2),
        }
    
    return {
        "assumptions": {
            "agents_count": agents_count,
            "runs_per_hour": runs_per_hour,
            "avg_input_tokens_per_run": avg_input_per_run,
            "avg_output_tokens_per_run": avg_output_per_run,
            "hourly_input_tokens": hourly_input,
            "hourly_output_tokens": hourly_output,
        },
        "estimates": estimates,
        "recommended": "deepseek-v3",  # 性价比最高
        "note": "实际成本取决于 Agent 活跃度和任务复杂度",
    }


# ============================================
# 健康检查
# ============================================

@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/", tags=["Health"])
async def root():
    """API 根路径"""
    return {
        "name": "AI Quant Company Dashboard API",
        "version": "0.2.0",
        "docs": "/docs",
        "features": [
            "组织架构管理",
            "研究流水线",
            "实验库",
            "实时市场数据",
            "账户余额与持仓",
            "WebSocket 实时行情流",
        ],
    }


# ============================================
# 真实数据 API - 交易信号
# ============================================

@app.get("/api/v2/signals", tags=["Trading V2"])
async def get_signals(status: Optional[str] = None):
    """获取交易信号列表"""
    signals = SignalManager.get_all()
    if status:
        signals = [s for s in signals if s.get("status") == status]
    return {"signals": signals, "total": len(signals)}


@app.get("/api/v2/signals/pending", tags=["Trading V2"])
async def get_pending_signals():
    """获取待执行信号"""
    signals = SignalManager.get_pending()
    return {"signals": signals, "total": len(signals)}


@app.post("/api/v2/signals", tags=["Trading V2"])
async def create_signal(signal: dict):
    """创建新信号"""
    result = SignalManager.create(signal)
    return {"success": True, "signal": result}


@app.put("/api/v2/signals/{signal_id}/execute", tags=["Trading V2"])
async def execute_signal(signal_id: str, pnl: float = 0):
    """执行信号"""
    result = SignalManager.update_status(signal_id, "executed", pnl)
    if result:
        return {"success": True, "signal": result}
    raise HTTPException(status_code=404, detail="信号不存在")


@app.put("/api/v2/signals/{signal_id}/cancel", tags=["Trading V2"])
async def cancel_signal(signal_id: str):
    """取消信号"""
    result = SignalManager.update_status(signal_id, "cancelled")
    if result:
        return {"success": True, "signal": result}
    raise HTTPException(status_code=404, detail="信号不存在")


# ============================================
# 真实数据 API - 持仓
# ============================================

@app.get("/api/v2/positions", tags=["Trading V2"])
async def get_positions():
    """获取持仓列表"""
    positions = PositionManager.get_all()
    return {"positions": positions, "total": len(positions)}


@app.post("/api/v2/positions", tags=["Trading V2"])
async def add_position(position: dict):
    """添加持仓"""
    result = PositionManager.add(position)
    return {"success": True, "position": result}


# ============================================
# 真实数据 API - 交易计划
# ============================================

@app.get("/api/v2/trading-plans", tags=["Trading V2"])
async def get_trading_plans_v2(state: Optional[str] = None):
    """获取交易计划列表"""
    plans = TradingPlanManager.get_all()
    if state:
        plans = [p for p in plans if p.get("state") == state]
    return {"plans": plans, "total": len(plans)}


@app.get("/api/v2/trading-plans/{plan_id}", tags=["Trading V2"])
async def get_trading_plan_v2(plan_id: str):
    """获取交易计划详情"""
    plan = TradingPlanManager.get_by_id(plan_id)
    if plan:
        return plan
    raise HTTPException(status_code=404, detail="计划不存在")


@app.post("/api/v2/trading-plans", tags=["Trading V2"])
async def create_trading_plan_v2(plan: dict):
    """创建交易计划"""
    result = TradingPlanManager.create(plan)
    return {"success": True, "plan": result}


@app.put("/api/v2/trading-plans/{plan_id}/state", tags=["Trading V2"])
async def update_trading_plan_state(plan_id: str, state: str):
    """更新计划状态"""
    result = TradingPlanManager.update_state(plan_id, state)
    if result:
        return {"success": True, "plan": result}
    raise HTTPException(status_code=404, detail="计划不存在")


# ============================================
# 真实数据 API - 研究周期
# ============================================

@app.get("/api/v2/research-cycles", tags=["Research V2"])
async def get_research_cycles_v2(state: Optional[str] = None):
    """获取研究周期列表"""
    cycles = ResearchCycleManager.get_all()
    if state:
        cycles = [c for c in cycles if c.get("state") == state]
    return {"cycles": cycles, "total": len(cycles)}


@app.get("/api/v2/research-cycles/{cycle_id}", tags=["Research V2"])
async def get_research_cycle_v2(cycle_id: str):
    """获取研究周期详情"""
    cycle = ResearchCycleManager.get_by_id(cycle_id)
    if cycle:
        return cycle
    raise HTTPException(status_code=404, detail="周期不存在")


@app.post("/api/v2/research-cycles", tags=["Research V2"])
async def create_research_cycle_v2(cycle: dict):
    """创建研究周期"""
    result = ResearchCycleManager.create(cycle)
    return {"success": True, "cycle": result}


@app.post("/api/v2/research-cycles/{cycle_id}/discussion", tags=["Research V2"])
async def add_cycle_discussion(cycle_id: str, message: dict):
    """添加研究讨论"""
    result = ResearchCycleManager.add_discussion(cycle_id, message)
    if result:
        return {"success": True, "cycle": result}
    raise HTTPException(status_code=404, detail="周期不存在")


@app.post("/api/v2/research-cycles/{cycle_id}/reference", tags=["Research V2"])
async def add_cycle_reference(cycle_id: str, reference: dict):
    """添加引用"""
    result = ResearchCycleManager.add_reference(cycle_id, reference)
    if result:
        return {"success": True, "cycle": result}
    raise HTTPException(status_code=404, detail="周期不存在")


@app.put("/api/v2/research-cycles/{cycle_id}/state", tags=["Research V2"])
async def update_cycle_state(cycle_id: str, state: str, progress: int = None):
    """更新周期状态"""
    result = ResearchCycleManager.update_state(cycle_id, state, progress)
    if result:
        return {"success": True, "cycle": result}
    raise HTTPException(status_code=404, detail="周期不存在")


# ============================================
# 真实数据 API - 报告
# ============================================

@app.get("/api/v2/reports", tags=["Reports V2"])
async def get_reports_v2(report_type: Optional[str] = None):
    """获取报告列表"""
    if report_type:
        reports = ReportManager.get_by_type(report_type)
    else:
        reports = ReportManager.get_all()
    return {"reports": reports, "total": len(reports)}


@app.post("/api/v2/reports", tags=["Reports V2"])
async def create_report_v2(report: dict):
    """创建报告"""
    result = ReportManager.create(report)
    return {"success": True, "report": result}


@app.put("/api/v2/reports/{report_id}/status", tags=["Reports V2"])
async def update_report_status(report_id: str, status: str):
    """更新报告状态"""
    result = ReportManager.update_status(report_id, status)
    if result:
        return {"success": True, "report": result}
    raise HTTPException(status_code=404, detail="报告不存在")


# ============================================
# 真实数据 API - 审批
# ============================================

@app.get("/api/v2/approvals", tags=["Approvals V2"])
async def get_approvals_v2(status: Optional[str] = None):
    """获取审批列表"""
    approvals = ApprovalManager.get_all()
    if status:
        approvals = [a for a in approvals if a.get("status") == status]
    return {"approvals": approvals, "total": len(approvals)}


@app.get("/api/v2/approvals/pending", tags=["Approvals V2"])
async def get_pending_approvals_v2():
    """获取待审批项"""
    approvals = ApprovalManager.get_pending()
    return {"approvals": approvals, "total": len(approvals)}


@app.post("/api/v2/approvals", tags=["Approvals V2"])
async def create_approval_v2(approval: dict):
    """创建审批项"""
    result = ApprovalManager.create(approval)
    return {"success": True, "approval": result}


@app.put("/api/v2/approvals/{approval_id}/approve", tags=["Approvals V2"])
async def approve_approval_v2(approval_id: str, approver: str = "chairman"):
    """批准"""
    result = ApprovalManager.approve(approval_id, approver)
    if result:
        return {"success": True, "approval": result}
    raise HTTPException(status_code=404, detail="审批项不存在")


@app.put("/api/v2/approvals/{approval_id}/reject", tags=["Approvals V2"])
async def reject_approval_v2(approval_id: str, reason: str = None):
    """驳回"""
    result = ApprovalManager.reject(approval_id, reason)
    if result:
        return {"success": True, "approval": result}
    raise HTTPException(status_code=404, detail="审批项不存在")


# ============================================
# 真实数据 API - 会议
# ============================================

@app.get("/api/v2/meetings", tags=["Meetings V2"])
async def get_meetings_v2(status: Optional[str] = None):
    """获取会议列表"""
    if status:
        meetings = MeetingManager.get_by_status(status)
    else:
        meetings = MeetingManager.get_all()
    return {"meetings": meetings, "total": len(meetings)}


@app.get("/api/v2/meetings/{meeting_id}", tags=["Meetings V2"])
async def get_meeting_v2(meeting_id: str):
    """获取会议详情"""
    meeting = MeetingManager.get_by_id(meeting_id)
    if meeting:
        return meeting
    raise HTTPException(status_code=404, detail="会议不存在")


@app.post("/api/v2/meetings", tags=["Meetings V2"])
async def create_meeting_v2(meeting: dict):
    """创建会议"""
    result = MeetingManager.create(meeting)
    return {"success": True, "meeting": result}


@app.post("/api/v2/meetings/{meeting_id}/message", tags=["Meetings V2"])
async def add_meeting_message(meeting_id: str, message: dict):
    """添加会议消息"""
    result = MeetingManager.add_message(meeting_id, message)
    if result:
        return {"success": True, "meeting": result}
    raise HTTPException(status_code=404, detail="会议不存在")


@app.put("/api/v2/meetings/{meeting_id}/status", tags=["Meetings V2"])
async def update_meeting_status(meeting_id: str, status: str):
    """更新会议状态"""
    result = MeetingManager.update_status(meeting_id, status)
    if result:
        return {"success": True, "meeting": result}
    raise HTTPException(status_code=404, detail="会议不存在")


# ============================================
# 真实数据 API - 回测
# ============================================

@app.get("/api/v2/backtests", tags=["Backtest V2"])
async def get_backtests_v2():
    """获取回测列表"""
    backtests = BacktestManager.get_all()
    return {"backtests": backtests, "total": len(backtests)}


@app.get("/api/v2/backtests/{backtest_id}", tags=["Backtest V2"])
async def get_backtest_v2(backtest_id: str):
    """获取回测详情"""
    backtest = BacktestManager.get_by_id(backtest_id)
    if backtest:
        return backtest
    raise HTTPException(status_code=404, detail="回测不存在")


@app.post("/api/v2/backtests", tags=["Backtest V2"])
async def create_backtest_v2(backtest: dict):
    """创建回测"""
    result = BacktestManager.create(backtest)
    return {"success": True, "backtest": result}


@app.put("/api/v2/backtests/{backtest_id}", tags=["Backtest V2"])
async def update_backtest_v2(backtest_id: str, updates: dict):
    """更新回测"""
    result = BacktestManager.update(backtest_id, updates)
    if result:
        return {"success": True, "backtest": result}
    raise HTTPException(status_code=404, detail="回测不存在")


# ============================================
# 真实数据 API - Agent 状态
# ============================================

@app.get("/api/v2/agents/status", tags=["Agents V2"])
async def get_agents_status_v2():
    """获取所有 Agent 状态"""
    return AgentStatusManager.get_all()


@app.get("/api/v2/agents/{agent_id}/status", tags=["Agents V2"])
async def get_agent_status_v2(agent_id: str):
    """获取单个 Agent 状态"""
    status = AgentStatusManager.get_agent(agent_id)
    if status:
        return status
    return {"agent_id": agent_id, "status": "unknown"}


@app.put("/api/v2/agents/{agent_id}/status", tags=["Agents V2"])
async def update_agent_status_v2(agent_id: str, status: dict):
    """更新 Agent 状态"""
    result = AgentStatusManager.update_agent(agent_id, status)
    return {"success": True, "status": result}
