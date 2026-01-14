# AI Quant Company - Trading State Machine
"""
交易流程状态机

管理从策略批准到实盘执行的完整流程：
- 策略通过董事会 → 制定交易计划 → 模拟测试 → 审批 → 实盘执行 → 监控
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


# ============================================
# 状态定义
# ============================================

class TradingPlanState(str, Enum):
    """交易计划状态"""
    DRAFT = "DRAFT"                         # 草稿
    SIMULATION_PENDING = "SIMULATION_PENDING"  # 等待模拟
    SIMULATION_RUNNING = "SIMULATION_RUNNING"  # 模拟执行中
    SIMULATION_COMPLETED = "SIMULATION_COMPLETED"  # 模拟完成
    REVIEW_BY_TRADER = "REVIEW_BY_TRADER"     # 交易主管审核
    PENDING_CHAIRMAN = "PENDING_CHAIRMAN"     # 等待董事长审批
    APPROVED = "APPROVED"                     # 已批准
    LIVE_PENDING = "LIVE_PENDING"             # 等待实盘执行
    LIVE_EXECUTING = "LIVE_EXECUTING"         # 实盘执行中
    LIVE_COMPLETED = "LIVE_COMPLETED"         # 实盘完成
    MONITORING = "MONITORING"                 # 持仓监控中
    CLOSED = "CLOSED"                         # 已平仓
    REJECTED = "REJECTED"                     # 被拒绝
    CANCELLED = "CANCELLED"                   # 已取消


class ExecutionType(str, Enum):
    """执行类型"""
    SIMULATION = "simulation"  # 模拟
    LIVE = "live"              # 实盘


class OrderSide(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


# ============================================
# 数据类
# ============================================

@dataclass
class TradingOrder:
    """交易订单"""
    id: str = field(default_factory=lambda: str(uuid4()))
    plan_id: str = ""
    
    # 订单参数
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    price: Optional[float] = None  # 限价单价格
    stop_price: Optional[float] = None  # 止损价格
    
    # 执行参数
    execution_type: ExecutionType = ExecutionType.SIMULATION
    time_in_force: str = "GTC"  # GTC, IOC, FOK
    max_slippage_bps: int = 50  # 最大允许滑点 (basis points)
    
    # 执行结果
    status: str = "pending"  # pending, submitted, filled, partial, cancelled, failed
    filled_quantity: float = 0.0
    average_price: float = 0.0
    commission: float = 0.0
    slippage_bps: float = 0.0
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    
    # 执行记录
    exchange_order_id: Optional[str] = None
    execution_log: list = field(default_factory=list)


@dataclass
class TradingPlan:
    """交易计划"""
    id: str = field(default_factory=lambda: str(uuid4()))
    
    # 关联
    strategy_id: Optional[str] = None  # 关联的策略 ID
    experiment_id: Optional[str] = None  # 关联的实验 ID
    cycle_id: Optional[str] = None  # 关联的研究周期 ID
    
    # 基本信息
    name: str = ""
    description: str = ""
    created_by: str = ""  # 创建者 agent_id
    
    # 交易目标
    target_portfolio: dict = field(default_factory=dict)  # {symbol: target_weight}
    current_portfolio: dict = field(default_factory=dict)  # {symbol: current_weight}
    
    # 风险参数
    max_position_size: float = 0.1  # 单一标的最大仓位
    max_total_exposure: float = 1.0  # 最大总敞口
    stop_loss_pct: float = 0.05  # 止损比例
    take_profit_pct: Optional[float] = None  # 止盈比例
    max_slippage_bps: int = 50  # 最大滑点
    
    # 执行参数
    execution_style: str = "twap"  # twap, vwap, market, limit
    execution_window_minutes: int = 60  # 执行时间窗口
    
    # 状态
    state: TradingPlanState = TradingPlanState.DRAFT
    
    # 订单
    orders: list[TradingOrder] = field(default_factory=list)
    
    # 模拟结果
    simulation_result: Optional[dict] = None
    
    # 审批
    trader_approval: Optional[dict] = None
    chairman_approval: Optional[dict] = None
    
    # 执行结果
    execution_summary: Optional[dict] = None
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


@dataclass
class Position:
    """持仓"""
    id: str = field(default_factory=lambda: str(uuid4()))
    plan_id: str = ""
    
    symbol: str = ""
    side: str = "long"  # long, short
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    
    # 盈亏
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    realized_pnl: float = 0.0
    
    # 风险
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # 时间
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    # 状态
    is_open: bool = True


# ============================================
# 状态转移
# ============================================

@dataclass
class Transition:
    """状态转移"""
    from_state: TradingPlanState
    to_state: TradingPlanState
    trigger: str
    guard: Optional[Callable] = None
    on_transition: Optional[Callable] = None


# 合法的状态转移
TRADING_TRANSITIONS: list[Transition] = [
    # 草稿 → 模拟
    Transition(TradingPlanState.DRAFT, TradingPlanState.SIMULATION_PENDING, "submit_simulation"),
    Transition(TradingPlanState.SIMULATION_PENDING, TradingPlanState.SIMULATION_RUNNING, "start_simulation"),
    Transition(TradingPlanState.SIMULATION_RUNNING, TradingPlanState.SIMULATION_COMPLETED, "simulation_done"),
    
    # 模拟完成 → 审核
    Transition(TradingPlanState.SIMULATION_COMPLETED, TradingPlanState.REVIEW_BY_TRADER, "submit_for_review"),
    Transition(TradingPlanState.SIMULATION_COMPLETED, TradingPlanState.DRAFT, "revise"),  # 退回修改
    
    # 交易主管审核
    Transition(TradingPlanState.REVIEW_BY_TRADER, TradingPlanState.PENDING_CHAIRMAN, "trader_approved"),
    Transition(TradingPlanState.REVIEW_BY_TRADER, TradingPlanState.DRAFT, "trader_rejected"),
    
    # 董事长审批
    Transition(TradingPlanState.PENDING_CHAIRMAN, TradingPlanState.APPROVED, "chairman_approved"),
    Transition(TradingPlanState.PENDING_CHAIRMAN, TradingPlanState.REJECTED, "chairman_rejected"),
    
    # 执行
    Transition(TradingPlanState.APPROVED, TradingPlanState.LIVE_PENDING, "schedule_execution"),
    Transition(TradingPlanState.LIVE_PENDING, TradingPlanState.LIVE_EXECUTING, "start_execution"),
    Transition(TradingPlanState.LIVE_EXECUTING, TradingPlanState.LIVE_COMPLETED, "execution_done"),
    
    # 监控
    Transition(TradingPlanState.LIVE_COMPLETED, TradingPlanState.MONITORING, "start_monitoring"),
    Transition(TradingPlanState.MONITORING, TradingPlanState.CLOSED, "close_position"),
    
    # 取消
    Transition(TradingPlanState.DRAFT, TradingPlanState.CANCELLED, "cancel"),
    Transition(TradingPlanState.SIMULATION_PENDING, TradingPlanState.CANCELLED, "cancel"),
    Transition(TradingPlanState.PENDING_CHAIRMAN, TradingPlanState.CANCELLED, "cancel"),
    Transition(TradingPlanState.APPROVED, TradingPlanState.CANCELLED, "cancel"),
]


# ============================================
# 交易状态机
# ============================================

class TradingStateMachine:
    """交易状态机"""
    
    def __init__(self):
        """初始化状态机"""
        self._plans: dict[str, TradingPlan] = {}
        self._positions: dict[str, Position] = {}
        self._transitions = {
            (t.from_state, t.trigger): t for t in TRADING_TRANSITIONS
        }
        
        # 事件回调
        self._callbacks: dict[str, list[Callable]] = {
            "on_state_change": [],
            "on_approval_required": [],
            "on_execution_start": [],
            "on_execution_complete": [],
            "on_position_update": [],
            "on_risk_alert": [],
        }
        
        logger.info("TradingStateMachine 初始化")
    
    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def _emit_event(self, event: str, **kwargs):
        """触发事件"""
        for callback in self._callbacks.get(event, []):
            try:
                await callback(**kwargs)
            except Exception as e:
                logger.error(f"回调执行失败: {event}, 错误: {e}")
    
    # ============================================
    # 计划管理
    # ============================================
    
    def create_plan(
        self,
        name: str,
        description: str,
        created_by: str,
        target_portfolio: dict,
        strategy_id: str = None,
        experiment_id: str = None,
        cycle_id: str = None,
        **kwargs,
    ) -> TradingPlan:
        """创建交易计划"""
        plan = TradingPlan(
            name=name,
            description=description,
            created_by=created_by,
            target_portfolio=target_portfolio,
            strategy_id=strategy_id,
            experiment_id=experiment_id,
            cycle_id=cycle_id,
            **kwargs,
        )
        
        self._plans[plan.id] = plan
        
        logger.info(
            "交易计划已创建",
            plan_id=plan.id,
            name=name,
            created_by=created_by,
        )
        
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[TradingPlan]:
        """获取交易计划"""
        return self._plans.get(plan_id)
    
    def list_plans(
        self,
        state: TradingPlanState = None,
        created_by: str = None,
    ) -> list[TradingPlan]:
        """列出交易计划"""
        plans = list(self._plans.values())
        
        if state:
            plans = [p for p in plans if p.state == state]
        if created_by:
            plans = [p for p in plans if p.created_by == created_by]
        
        return sorted(plans, key=lambda p: p.created_at, reverse=True)
    
    # ============================================
    # 状态转移
    # ============================================
    
    async def transition(
        self,
        plan_id: str,
        trigger: str,
        actor: str = None,
        data: dict = None,
    ) -> bool:
        """执行状态转移
        
        Args:
            plan_id: 计划 ID
            trigger: 触发条件
            actor: 执行者
            data: 附加数据
            
        Returns:
            是否成功
        """
        plan = self._plans.get(plan_id)
        if not plan:
            logger.warning(f"计划不存在: {plan_id}")
            return False
        
        key = (plan.state, trigger)
        transition = self._transitions.get(key)
        
        if not transition:
            logger.warning(
                f"非法状态转移",
                plan_id=plan_id,
                current_state=plan.state.value,
                trigger=trigger,
            )
            return False
        
        # 检查守卫条件
        if transition.guard and not transition.guard(plan, data):
            logger.warning(f"守卫条件未满足: {trigger}")
            return False
        
        # 记录旧状态
        old_state = plan.state
        
        # 执行转移
        plan.state = transition.to_state
        plan.updated_at = datetime.utcnow()
        
        # 执行转移动作
        if transition.on_transition:
            await transition.on_transition(plan, data)
        
        logger.info(
            "状态转移",
            plan_id=plan_id,
            from_state=old_state.value,
            to_state=plan.state.value,
            trigger=trigger,
            actor=actor,
        )
        
        # 触发事件
        await self._emit_event(
            "on_state_change",
            plan=plan,
            old_state=old_state,
            new_state=plan.state,
            trigger=trigger,
            actor=actor,
        )
        
        # 特殊状态处理
        if plan.state == TradingPlanState.PENDING_CHAIRMAN:
            await self._emit_event(
                "on_approval_required",
                plan=plan,
                approval_type="chairman",
            )
        elif plan.state == TradingPlanState.LIVE_EXECUTING:
            await self._emit_event("on_execution_start", plan=plan)
        elif plan.state == TradingPlanState.LIVE_COMPLETED:
            await self._emit_event("on_execution_complete", plan=plan)
        
        return True
    
    # ============================================
    # 模拟执行
    # ============================================
    
    async def run_simulation(self, plan_id: str) -> dict:
        """运行模拟交易
        
        Args:
            plan_id: 计划 ID
            
        Returns:
            模拟结果
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "计划不存在"}
        
        # 转移状态
        await self.transition(plan_id, "start_simulation")
        
        # 模拟执行
        # 这里应该调用回测引擎或模拟交易系统
        # 目前返回模拟结果
        simulation_result = {
            "plan_id": plan_id,
            "execution_type": "simulation",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": datetime.utcnow().isoformat(),
            "orders_executed": len(plan.target_portfolio),
            "total_value": 10000.0,
            "estimated_slippage_bps": 15.0,
            "estimated_commission": 10.0,
            "risk_metrics": {
                "var_95": -250.0,
                "max_drawdown": -0.05,
                "sharpe_ratio": 1.5,
            },
            "execution_quality": {
                "vwap_deviation": 0.001,
                "implementation_shortfall": 0.002,
            },
        }
        
        plan.simulation_result = simulation_result
        
        # 转移状态
        await self.transition(plan_id, "simulation_done")
        
        logger.info(
            "模拟执行完成",
            plan_id=plan_id,
            estimated_slippage=simulation_result["estimated_slippage_bps"],
        )
        
        return simulation_result
    
    # ============================================
    # 审批流程
    # ============================================
    
    async def submit_for_review(self, plan_id: str, submitter: str) -> bool:
        """提交审核"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        if not plan.simulation_result:
            logger.warning("必须先完成模拟")
            return False
        
        plan.submitted_at = datetime.utcnow()
        return await self.transition(plan_id, "submit_for_review", actor=submitter)
    
    async def trader_review(
        self,
        plan_id: str,
        approved: bool,
        reviewer: str,
        comments: str = "",
    ) -> bool:
        """交易主管审核"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        plan.trader_approval = {
            "approved": approved,
            "reviewer": reviewer,
            "comments": comments,
            "reviewed_at": datetime.utcnow().isoformat(),
        }
        
        trigger = "trader_approved" if approved else "trader_rejected"
        return await self.transition(plan_id, trigger, actor=reviewer)
    
    async def chairman_review(
        self,
        plan_id: str,
        approved: bool,
        comments: str = "",
    ) -> bool:
        """董事长审批"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        plan.chairman_approval = {
            "approved": approved,
            "comments": comments,
            "reviewed_at": datetime.utcnow().isoformat(),
        }
        
        if approved:
            plan.approved_at = datetime.utcnow()
        
        trigger = "chairman_approved" if approved else "chairman_rejected"
        return await self.transition(plan_id, trigger, actor="chairman")
    
    # ============================================
    # 实盘执行
    # ============================================
    
    async def schedule_execution(
        self,
        plan_id: str,
        execution_time: datetime = None,
    ) -> bool:
        """安排实盘执行"""
        return await self.transition(plan_id, "schedule_execution")
    
    async def start_live_execution(self, plan_id: str) -> bool:
        """开始实盘执行"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        if plan.state != TradingPlanState.LIVE_PENDING:
            logger.warning(f"计划状态不正确: {plan.state}")
            return False
        
        if not plan.chairman_approval or not plan.chairman_approval.get("approved"):
            logger.warning("需要董事长批准")
            return False
        
        plan.executed_at = datetime.utcnow()
        return await self.transition(plan_id, "start_execution")
    
    async def complete_execution(
        self,
        plan_id: str,
        execution_summary: dict,
    ) -> bool:
        """完成执行"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        plan.execution_summary = execution_summary
        return await self.transition(plan_id, "execution_done")
    
    # ============================================
    # 持仓管理
    # ============================================
    
    def create_position(
        self,
        plan_id: str,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float = None,
        take_profit: float = None,
    ) -> Position:
        """创建持仓"""
        position = Position(
            plan_id=plan_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        
        self._positions[position.id] = position
        
        logger.info(
            "持仓创建",
            position_id=position.id,
            symbol=symbol,
            side=side,
            quantity=quantity,
        )
        
        return position
    
    async def update_position_price(
        self,
        position_id: str,
        current_price: float,
    ) -> Optional[Position]:
        """更新持仓价格"""
        position = self._positions.get(position_id)
        if not position or not position.is_open:
            return None
        
        position.current_price = current_price
        
        # 计算未实现盈亏
        if position.side == "long":
            position.unrealized_pnl = (current_price - position.entry_price) * position.quantity
        else:
            position.unrealized_pnl = (position.entry_price - current_price) * position.quantity
        
        position.unrealized_pnl_pct = position.unrealized_pnl / (position.entry_price * position.quantity)
        
        # 检查止损止盈
        await self._check_position_triggers(position)
        
        await self._emit_event("on_position_update", position=position)
        
        return position
    
    async def _check_position_triggers(self, position: Position):
        """检查持仓触发条件"""
        # 止损检查
        if position.stop_loss:
            if position.side == "long" and position.current_price <= position.stop_loss:
                await self._emit_event(
                    "on_risk_alert",
                    alert_type="stop_loss_triggered",
                    position=position,
                )
            elif position.side == "short" and position.current_price >= position.stop_loss:
                await self._emit_event(
                    "on_risk_alert",
                    alert_type="stop_loss_triggered",
                    position=position,
                )
        
        # 止盈检查
        if position.take_profit:
            if position.side == "long" and position.current_price >= position.take_profit:
                await self._emit_event(
                    "on_risk_alert",
                    alert_type="take_profit_triggered",
                    position=position,
                )
            elif position.side == "short" and position.current_price <= position.take_profit:
                await self._emit_event(
                    "on_risk_alert",
                    alert_type="take_profit_triggered",
                    position=position,
                )
    
    async def close_position(
        self,
        position_id: str,
        close_price: float,
        reason: str = "",
    ) -> Optional[Position]:
        """平仓"""
        position = self._positions.get(position_id)
        if not position or not position.is_open:
            return None
        
        position.current_price = close_price
        position.is_open = False
        position.closed_at = datetime.utcnow()
        
        # 计算已实现盈亏
        if position.side == "long":
            position.realized_pnl = (close_price - position.entry_price) * position.quantity
        else:
            position.realized_pnl = (position.entry_price - close_price) * position.quantity
        
        position.unrealized_pnl = 0
        
        logger.info(
            "持仓已平仓",
            position_id=position_id,
            realized_pnl=position.realized_pnl,
            reason=reason,
        )
        
        return position
    
    def get_open_positions(self, plan_id: str = None) -> list[Position]:
        """获取未平仓持仓"""
        positions = [p for p in self._positions.values() if p.is_open]
        if plan_id:
            positions = [p for p in positions if p.plan_id == plan_id]
        return positions
    
    def get_all_positions(self, plan_id: str = None) -> list[Position]:
        """获取所有持仓"""
        positions = list(self._positions.values())
        if plan_id:
            positions = [p for p in positions if p.plan_id == plan_id]
        return positions
    
    # ============================================
    # 统计查询
    # ============================================
    
    def get_pending_approvals(self) -> list[TradingPlan]:
        """获取待审批的计划"""
        return [
            p for p in self._plans.values()
            if p.state in (TradingPlanState.REVIEW_BY_TRADER, TradingPlanState.PENDING_CHAIRMAN)
        ]
    
    def get_active_executions(self) -> list[TradingPlan]:
        """获取正在执行的计划"""
        return [
            p for p in self._plans.values()
            if p.state in (TradingPlanState.LIVE_PENDING, TradingPlanState.LIVE_EXECUTING)
        ]
    
    def get_monitoring_plans(self) -> list[TradingPlan]:
        """获取监控中的计划"""
        return [
            p for p in self._plans.values()
            if p.state == TradingPlanState.MONITORING
        ]
    
    def get_portfolio_summary(self) -> dict:
        """获取组合汇总"""
        open_positions = self.get_open_positions()
        
        total_value = sum(p.entry_price * p.quantity for p in open_positions)
        total_unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)
        
        return {
            "open_positions": len(open_positions),
            "total_value": total_value,
            "total_unrealized_pnl": total_unrealized_pnl,
            "positions": [
                {
                    "symbol": p.symbol,
                    "side": p.side,
                    "quantity": p.quantity,
                    "entry_price": p.entry_price,
                    "current_price": p.current_price,
                    "unrealized_pnl": p.unrealized_pnl,
                    "unrealized_pnl_pct": p.unrealized_pnl_pct,
                }
                for p in open_positions
            ],
        }


# 全局单例
_trading_state_machine: Optional[TradingStateMachine] = None


def get_trading_state_machine() -> TradingStateMachine:
    """获取交易状态机单例"""
    global _trading_state_machine
    if _trading_state_machine is None:
        _trading_state_machine = TradingStateMachine()
    return _trading_state_machine
