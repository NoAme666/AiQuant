# AI Quant Company - Agent Scheduler
"""
Agent 调度器

负责 24/7 持续运行的 Agent 系统：
- 调度 Agent 执行
- 管理研究周期
- 触发定期任务
- 生成报告
- 处理审批队列
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import structlog

from agents.runtime import AgentRuntime, RuntimeAgent, get_agent_runtime, init_agent_runtime
from orchestrator.message_bus import MessageBus, get_message_bus

logger = structlog.get_logger()


class SchedulerState(str, Enum):
    """调度器状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    task_type: str = ""  # daily, weekly, interval, cron
    handler: Optional[Callable] = None
    
    # 调度参数
    interval_seconds: int = 0  # interval 类型使用
    hour: int = 0  # daily/weekly 类型使用
    minute: int = 0
    day_of_week: int = 0  # weekly 类型使用（0=周一）
    
    # 状态
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    enabled: bool = True


@dataclass
class ApprovalItem:
    """审批项"""
    id: str = field(default_factory=lambda: str(uuid4()))
    item_type: str = ""  # trading_plan, experiment, hiring, termination, meeting
    title: str = ""
    description: str = ""
    requester: str = ""
    data: dict = field(default_factory=dict)
    
    status: str = "pending"  # pending, approved, rejected
    decision_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    decision_reason: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class AgentScheduler:
    """Agent 调度器
    
    管理 Agent 系统的 24/7 运行
    """
    
    def __init__(
        self,
        use_mock_llm: bool = False,
        agent_interval: float = 2.0,
        scheduler_interval: float = 10.0,
    ):
        """初始化调度器
        
        Args:
            use_mock_llm: 是否使用 Mock LLM
            agent_interval: Agent 迭代间隔（秒）
            scheduler_interval: 调度器检查间隔（秒）
        """
        self.use_mock_llm = use_mock_llm
        self.agent_interval = agent_interval
        self.scheduler_interval = scheduler_interval
        
        self._state = SchedulerState.STOPPED
        self._runtime: Optional[AgentRuntime] = None
        self._message_bus: Optional[MessageBus] = None
        
        # 定时任务
        self._scheduled_tasks: dict[str, ScheduledTask] = {}
        self._setup_default_tasks()
        
        # 审批队列
        self._approval_queue: list[ApprovalItem] = []
        
        # Agent 运行任务
        self._agent_tasks: dict[str, asyncio.Task] = {}
        
        # 统计
        self._stats = {
            "started_at": None,
            "total_iterations": 0,
            "total_agent_runs": 0,
            "total_messages": 0,
            "total_approvals": 0,
            "errors": 0,
        }
    
    def _setup_default_tasks(self):
        """设置默认定时任务"""
        # 每日晨会
        self._scheduled_tasks["daily_standup"] = ScheduledTask(
            name="每日晨会",
            task_type="daily",
            hour=9,
            minute=0,
            handler=self._trigger_daily_standup,
        )
        
        # 每周董事会报告
        self._scheduled_tasks["weekly_board_report"] = ScheduledTask(
            name="周度董事会报告",
            task_type="weekly",
            day_of_week=4,  # 周五
            hour=16,
            minute=0,
            handler=self._generate_weekly_report,
        )
        
        # 每日合规检查
        self._scheduled_tasks["daily_compliance"] = ScheduledTask(
            name="每日合规检查",
            task_type="daily",
            hour=18,
            minute=0,
            handler=self._run_compliance_check,
        )
        
        # 定期健康检查
        self._scheduled_tasks["health_check"] = ScheduledTask(
            name="系统健康检查",
            task_type="interval",
            interval_seconds=300,  # 5分钟
            handler=self._health_check,
        )
    
    @property
    def state(self) -> SchedulerState:
        return self._state
    
    @property
    def is_running(self) -> bool:
        return self._state == SchedulerState.RUNNING
    
    # ============================================
    # 生命周期管理
    # ============================================
    
    async def start(self):
        """启动调度器"""
        if self._state != SchedulerState.STOPPED:
            logger.warning(f"调度器状态不正确: {self._state}")
            return
        
        self._state = SchedulerState.STARTING
        logger.info("启动 Agent 调度器...")
        
        try:
            # 初始化消息总线
            self._message_bus = get_message_bus()
            await self._message_bus.start()
            
            # 初始化 Agent 运行时
            self._runtime = await init_agent_runtime(use_mock=self.use_mock_llm)
            
            # 启动所有 Agent 的运行循环
            for agent_id, agent in self._runtime.get_all_agents().items():
                task = asyncio.create_task(
                    self._run_agent_loop(agent),
                    name=f"agent_{agent_id}"
                )
                self._agent_tasks[agent_id] = task
            
            # 初始化定时任务的下次运行时间
            self._init_task_schedules()
            
            self._state = SchedulerState.RUNNING
            self._stats["started_at"] = datetime.utcnow().isoformat()
            
            logger.info(
                "Agent 调度器启动完成",
                agent_count=len(self._agent_tasks),
                scheduled_tasks=len(self._scheduled_tasks),
            )
            
            # 发送启动通知
            await self._message_bus.broadcast(
                from_agent="system",
                content="AI Quant Company 系统已启动，所有 Agent 开始工作。",
                subject="系统启动通知",
            )
            
        except Exception as e:
            self._state = SchedulerState.STOPPED
            logger.error(f"调度器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止调度器"""
        if self._state not in (SchedulerState.RUNNING, SchedulerState.PAUSED):
            return
        
        self._state = SchedulerState.STOPPING
        logger.info("停止 Agent 调度器...")
        
        # 发送停止通知
        if self._message_bus:
            await self._message_bus.broadcast(
                from_agent="system",
                content="AI Quant Company 系统正在关闭。",
                subject="系统关闭通知",
            )
        
        # 取消所有 Agent 任务
        for task in self._agent_tasks.values():
            task.cancel()
        
        # 等待任务结束
        if self._agent_tasks:
            await asyncio.gather(*self._agent_tasks.values(), return_exceptions=True)
        
        # 停止运行时
        if self._runtime:
            await self._runtime.stop()
        
        # 停止消息总线
        if self._message_bus:
            await self._message_bus.stop()
        
        self._state = SchedulerState.STOPPED
        logger.info("Agent 调度器已停止")
    
    async def pause(self):
        """暂停调度器"""
        if self._state != SchedulerState.RUNNING:
            return
        
        self._state = SchedulerState.PAUSED
        logger.info("Agent 调度器已暂停")
    
    async def resume(self):
        """恢复调度器"""
        if self._state != SchedulerState.PAUSED:
            return
        
        self._state = SchedulerState.RUNNING
        logger.info("Agent 调度器已恢复")
    
    # ============================================
    # Agent 运行循环
    # ============================================
    
    async def _run_agent_loop(self, agent: RuntimeAgent):
        """运行单个 Agent 的循环"""
        agent_id = agent.agent_id
        logger.info(f"Agent {agent_id} 运行循环启动")
        
        while self._state in (SchedulerState.RUNNING, SchedulerState.PAUSED):
            try:
                if self._state == SchedulerState.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                stats = await agent.run_once()
                self._stats["total_agent_runs"] += 1
                self._stats["total_messages"] += stats.get("messages_processed", 0)
                
                if stats.get("errors", 0) > 0:
                    self._stats["errors"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent {agent_id} 运行错误: {e}")
                self._stats["errors"] += 1
            
            await asyncio.sleep(self.agent_interval)
        
        logger.info(f"Agent {agent_id} 运行循环结束")
    
    # ============================================
    # 主循环
    # ============================================
    
    async def run_forever(self):
        """主运行循环"""
        await self.start()
        
        try:
            while self._state in (SchedulerState.RUNNING, SchedulerState.PAUSED):
                try:
                    if self._state == SchedulerState.RUNNING:
                        await self._scheduler_iteration()
                    
                    self._stats["total_iterations"] += 1
                    
                except Exception as e:
                    logger.error(f"调度器迭代错误: {e}")
                    self._stats["errors"] += 1
                
                await asyncio.sleep(self.scheduler_interval)
                
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
    
    async def _scheduler_iteration(self):
        """调度器单次迭代"""
        now = datetime.utcnow()
        
        # 检查定时任务
        for task_id, task in self._scheduled_tasks.items():
            if not task.enabled:
                continue
            
            if task.next_run and now >= task.next_run:
                await self._execute_scheduled_task(task)
        
        # 检查过期的审批项
        self._check_expired_approvals()
    
    # ============================================
    # 定时任务
    # ============================================
    
    def _init_task_schedules(self):
        """初始化任务调度时间"""
        now = datetime.utcnow()
        
        for task in self._scheduled_tasks.values():
            task.next_run = self._calculate_next_run(task, now)
    
    def _calculate_next_run(
        self,
        task: ScheduledTask,
        from_time: datetime,
    ) -> datetime:
        """计算下次运行时间"""
        if task.task_type == "interval":
            return from_time + timedelta(seconds=task.interval_seconds)
        
        elif task.task_type == "daily":
            next_run = from_time.replace(
                hour=task.hour,
                minute=task.minute,
                second=0,
                microsecond=0,
            )
            if next_run <= from_time:
                next_run += timedelta(days=1)
            return next_run
        
        elif task.task_type == "weekly":
            # 计算到目标星期几的天数
            days_ahead = task.day_of_week - from_time.weekday()
            if days_ahead < 0:
                days_ahead += 7
            
            next_run = from_time.replace(
                hour=task.hour,
                minute=task.minute,
                second=0,
                microsecond=0,
            ) + timedelta(days=days_ahead)
            
            if next_run <= from_time:
                next_run += timedelta(weeks=1)
            return next_run
        
        return from_time + timedelta(hours=1)
    
    async def _execute_scheduled_task(self, task: ScheduledTask):
        """执行定时任务"""
        logger.info(f"执行定时任务: {task.name}")
        
        task.last_run = datetime.utcnow()
        task.run_count += 1
        
        try:
            if task.handler:
                await task.handler()
        except Exception as e:
            logger.error(f"定时任务执行失败: {task.name}, 错误: {e}")
        
        # 计算下次运行时间
        task.next_run = self._calculate_next_run(task, task.last_run)
    
    # ============================================
    # 内置定时任务处理器
    # ============================================
    
    async def _trigger_daily_standup(self):
        """触发每日晨会"""
        logger.info("触发每日晨会")
        
        # 创建会议
        meeting_id = f"standup_{datetime.utcnow().strftime('%Y%m%d')}"
        
        # 获取所有 Lead
        leads = [
            agent for agent in self._runtime.get_all_agents().values()
            if agent.config.is_lead
        ]
        
        if not leads:
            return
        
        lead_ids = [agent.agent_id for agent in leads]
        
        await self._message_bus.create_meeting_room(
            meeting_id=meeting_id,
            title="每日晨会",
            host="chief_of_staff",
            participants=lead_ids,
            metadata={"type": "standup"},
        )
        
        # 发送议程
        await self._message_bus.send_to_meeting(
            meeting_id=meeting_id,
            from_agent="system",
            content="""
今日晨会议程：
1. 各部门工作进展
2. 阻塞问题
3. 今日计划
4. 资源需求

请各位 Lead 依次汇报。
""",
            message_type="agenda",
        )
    
    async def _generate_weekly_report(self):
        """生成周度董事会报告"""
        logger.info("生成周度董事会报告")
        
        # 收集本周数据
        report_data = {
            "period": f"{(datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {datetime.utcnow().strftime('%Y-%m-%d')}",
            "stats": self._stats.copy(),
            "agent_statuses": self._runtime.get_agent_statuses() if self._runtime else [],
            "pending_approvals": len([a for a in self._approval_queue if a.status == "pending"]),
        }
        
        # 让 Chief of Staff 生成报告
        cos = self._runtime.get_agent("chief_of_staff") if self._runtime else None
        if cos:
            await cos.add_task(
                task_type="report",
                payload={
                    "type": "report",
                    "report_type": "weekly_board_report",
                    "data": report_data,
                },
            )
    
    async def _run_compliance_check(self):
        """运行每日合规检查"""
        logger.info("运行每日合规检查")
        
        # 让 CGO 执行检查
        cgo = self._runtime.get_agent("cgo") if self._runtime else None
        if cgo:
            await cgo.add_task(
                task_type="review",
                payload={
                    "type": "review",
                    "review_type": "daily_compliance",
                    "item": {
                        "date": datetime.utcnow().strftime("%Y-%m-%d"),
                        "stats": self._stats.copy(),
                    },
                },
            )
    
    async def _health_check(self):
        """系统健康检查"""
        if not self._runtime:
            return
        
        # 检查 Agent 状态
        inactive_agents = []
        for agent in self._runtime.get_all_agents().values():
            status = agent.get_status()
            last_active = datetime.fromisoformat(status["last_active"])
            if datetime.utcnow() - last_active > timedelta(minutes=5):
                inactive_agents.append(agent.agent_id)
        
        if inactive_agents:
            logger.warning(f"发现不活跃的 Agent: {inactive_agents}")
    
    # ============================================
    # 审批队列
    # ============================================
    
    async def submit_for_approval(
        self,
        item_type: str,
        title: str,
        description: str,
        requester: str,
        data: dict,
        expires_in_hours: int = 24,
    ) -> ApprovalItem:
        """提交审批"""
        item = ApprovalItem(
            item_type=item_type,
            title=title,
            description=description,
            requester=requester,
            data=data,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
        )
        
        self._approval_queue.append(item)
        self._stats["total_approvals"] += 1
        
        logger.info(
            "审批项已提交",
            item_id=item.id,
            item_type=item_type,
            requester=requester,
        )
        
        # 通知董事长
        await self._message_bus.send_direct(
            from_agent="system",
            to_agent="chairman",
            content=f"新的审批请求：{title}\n\n{description}",
            subject=f"[审批] {item_type}: {title}",
            metadata={"approval_id": item.id},
        )
        
        return item
    
    async def approve_item(
        self,
        item_id: str,
        decision_by: str = "chairman",
        reason: str = "",
    ) -> bool:
        """批准审批项"""
        for item in self._approval_queue:
            if item.id == item_id and item.status == "pending":
                item.status = "approved"
                item.decision_by = decision_by
                item.decision_at = datetime.utcnow()
                item.decision_reason = reason
                
                logger.info(f"审批项已批准: {item_id}")
                
                # 通知申请人
                await self._message_bus.send_direct(
                    from_agent="system",
                    to_agent=item.requester,
                    content=f"你的审批请求「{item.title}」已被批准。\n理由：{reason}",
                    subject="[审批通过]",
                )
                
                return True
        
        return False
    
    async def reject_item(
        self,
        item_id: str,
        decision_by: str = "chairman",
        reason: str = "",
    ) -> bool:
        """拒绝审批项"""
        for item in self._approval_queue:
            if item.id == item_id and item.status == "pending":
                item.status = "rejected"
                item.decision_by = decision_by
                item.decision_at = datetime.utcnow()
                item.decision_reason = reason
                
                logger.info(f"审批项已拒绝: {item_id}")
                
                # 通知申请人
                await self._message_bus.send_direct(
                    from_agent="system",
                    to_agent=item.requester,
                    content=f"你的审批请求「{item.title}」已被拒绝。\n理由：{reason}",
                    subject="[审批拒绝]",
                )
                
                return True
        
        return False
    
    def get_pending_approvals(self) -> list[ApprovalItem]:
        """获取待审批项"""
        return [item for item in self._approval_queue if item.status == "pending"]
    
    def get_all_approvals(self, limit: int = 50) -> list[ApprovalItem]:
        """获取所有审批项"""
        return self._approval_queue[-limit:]
    
    def _check_expired_approvals(self):
        """检查过期的审批项"""
        now = datetime.utcnow()
        for item in self._approval_queue:
            if item.status == "pending" and item.expires_at and now > item.expires_at:
                item.status = "rejected"
                item.decision_reason = "已过期"
                item.decision_at = now
                logger.info(f"审批项已过期: {item.id}")
    
    # ============================================
    # 查询接口
    # ============================================
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            "state": self._state.value,
            "uptime_seconds": (
                (datetime.utcnow() - datetime.fromisoformat(self._stats["started_at"])).total_seconds()
                if self._stats["started_at"] else 0
            ),
            "active_agents": len(self._agent_tasks),
            "pending_approvals": len(self.get_pending_approvals()),
        }
    
    def get_scheduled_tasks(self) -> list[dict]:
        """获取定时任务列表"""
        return [
            {
                "id": task_id,
                "name": task.name,
                "task_type": task.task_type,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "run_count": task.run_count,
            }
            for task_id, task in self._scheduled_tasks.items()
        ]


# 全局单例
_scheduler: Optional[AgentScheduler] = None


def get_scheduler() -> AgentScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AgentScheduler()
    return _scheduler


async def start_scheduler(use_mock: bool = False) -> AgentScheduler:
    """启动调度器"""
    global _scheduler
    _scheduler = AgentScheduler(use_mock_llm=use_mock)
    await _scheduler.start()
    return _scheduler
