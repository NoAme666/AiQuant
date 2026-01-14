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

logger = structlog.get_logger()


# ============================================
# 生命周期管理
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动 AI Quant Company Dashboard API")
    yield
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
    # TODO: 从数据库获取实际数据
    return LobbyStats(
        active_cycles=3,
        pending_approvals=5,
        total_experiments=127,
        total_agents=18,
        budget_utilization=0.65,
        avg_reputation=0.72,
    )


# ============================================
# 路由 - Org Chart
# ============================================

@app.get("/api/org-chart", response_model=list[DepartmentInfo], tags=["Organization"])
async def get_org_chart():
    """获取组织架构"""
    # TODO: 从配置和数据库获取实际数据
    departments = [
        DepartmentInfo(
            id="board_office",
            name="董事会办公室",
            name_en="Board Office",
            agents=[
                AgentStatus(
                    id="chief_of_staff",
                    name="办公室主任",
                    name_en="Chief of Staff",
                    department="board_office",
                    is_lead=True,
                    status="active",
                    budget_remaining=180,
                    reputation_score=0.85,
                ),
            ],
        ),
        DepartmentInfo(
            id="research_guild",
            name="研究部",
            name_en="Research Guild",
            agents=[
                AgentStatus(
                    id="head_of_research",
                    name="研究总监",
                    name_en="Head of Research",
                    department="research_guild",
                    is_lead=True,
                    status="active",
                    budget_remaining=150,
                    reputation_score=0.78,
                ),
                AgentStatus(
                    id="alpha_a_lead",
                    name="Alpha A 组长",
                    name_en="Alpha Team A Lead",
                    department="research_guild",
                    is_lead=True,
                    status="active",
                    budget_remaining=800,
                    reputation_score=0.72,
                    current_task="策略回测中",
                ),
            ],
        ),
    ]
    return departments


@app.get("/api/agents/{agent_id}", response_model=AgentStatus, tags=["Organization"])
async def get_agent(agent_id: str):
    """获取 Agent 详情"""
    # TODO: 从数据库获取
    return AgentStatus(
        id=agent_id,
        name="办公室主任",
        name_en="Chief of Staff",
        department="board_office",
        is_lead=True,
        status="active",
        budget_remaining=180,
        reputation_score=0.85,
    )


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
    # TODO: 从数据库获取
    return [
        ResearchCycleInfo(
            id="cycle-001",
            name="BTC 动量策略 v1",
            current_state="ROBUSTNESS_GATE",
            team="alpha_a",
            proposer="alpha_a_lead",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        ResearchCycleInfo(
            id="cycle-002",
            name="ETH 均值回归",
            current_state="DATA_GATE",
            team="alpha_b",
            proposer="alpha_b_lead",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
    ]


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


@app.get("/api/events/history", response_model=list[EventInfo], tags=["Events"])
async def get_events_history(
    event_type: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """获取事件历史"""
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
