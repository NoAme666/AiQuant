# AI Quant Company - Agent Proactive Behavior System
"""
Agent 主动行为系统

提供:
- 研究员自动研究循环
- 策略发现与提案
- 自动回测实验
- Agent 间协作触发
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class AgentState(str, Enum):
    """Agent 状态"""
    IDLE = "idle"                 # 空闲
    RESEARCHING = "researching"   # 研究中
    BACKTESTING = "backtesting"   # 回测中
    REVIEWING = "reviewing"       # 审核中
    MEETING = "meeting"           # 开会中
    WAITING = "waiting"           # 等待中


class TaskType(str, Enum):
    """任务类型"""
    MARKET_ANALYSIS = "market_analysis"       # 市场分析
    STRATEGY_RESEARCH = "strategy_research"   # 策略研究
    BACKTEST_RUN = "backtest_run"             # 运行回测
    DATA_COLLECTION = "data_collection"       # 数据收集
    RISK_ASSESSMENT = "risk_assessment"       # 风险评估
    REPORT_GENERATION = "report_generation"   # 报告生成
    PEER_REVIEW = "peer_review"               # 同行评审
    MEETING_PREP = "meeting_prep"             # 会议准备


@dataclass
class AgentTask:
    """Agent 任务"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    task_type: TaskType = TaskType.MARKET_ANALYSIS
    agent_id: str = ""
    description: str = ""
    priority: int = 5  # 1-10, 10 最高
    
    # 执行
    status: str = "pending"  # pending, running, completed, failed
    progress: float = 0.0
    result: dict = field(default_factory=dict)
    
    # 时间
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 依赖
    depends_on: list[str] = field(default_factory=list)
    triggers: list[str] = field(default_factory=list)  # 完成后触发的任务


@dataclass
class AgentActivity:
    """Agent 活动记录"""
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    agent_id: str = ""
    agent_name: str = ""
    activity_type: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AgentBehavior:
    """Agent 行为定义"""
    
    # 各角色的默认行为模式
    ROLE_BEHAVIORS = {
        "researcher": {
            "tasks": [
                TaskType.MARKET_ANALYSIS,
                TaskType.STRATEGY_RESEARCH,
                TaskType.BACKTEST_RUN,
            ],
            "task_weights": [0.3, 0.5, 0.2],
            "work_interval_minutes": 30,
            "creativity_score": 0.7,
        },
        "risk": {
            "tasks": [
                TaskType.RISK_ASSESSMENT,
                TaskType.PEER_REVIEW,
            ],
            "task_weights": [0.6, 0.4],
            "work_interval_minutes": 60,
            "skepticism_score": 0.8,
        },
        "trader": {
            "tasks": [
                TaskType.MARKET_ANALYSIS,
                TaskType.DATA_COLLECTION,
            ],
            "task_weights": [0.7, 0.3],
            "work_interval_minutes": 15,
            "execution_focus": 0.9,
        },
        "intelligence": {
            "tasks": [
                TaskType.MARKET_ANALYSIS,
                TaskType.DATA_COLLECTION,
                TaskType.REPORT_GENERATION,
            ],
            "task_weights": [0.4, 0.4, 0.2],
            "work_interval_minutes": 10,
            "monitoring_focus": 0.9,
        },
    }


class AgentLoop:
    """Agent 主循环系统"""
    
    def __init__(self):
        self._agents: dict[str, dict] = {}
        self._tasks: dict[str, AgentTask] = {}
        self._activities: list[AgentActivity] = []
        self._running = False
        self._task_queue: asyncio.Queue = asyncio.Queue()
        logger.info("AgentLoop 初始化")
    
    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        role: str,
        department: str,
    ):
        """注册 Agent"""
        behavior = AgentBehavior.ROLE_BEHAVIORS.get(role, AgentBehavior.ROLE_BEHAVIORS["researcher"])
        
        self._agents[agent_id] = {
            "id": agent_id,
            "name": agent_name,
            "role": role,
            "department": department,
            "state": AgentState.IDLE,
            "behavior": behavior,
            "current_task": None,
            "last_activity": datetime.utcnow(),
            "tasks_completed": 0,
            "discoveries": [],
        }
        
        logger.info("Agent 已注册", agent_id=agent_id, role=role)
    
    async def start(self):
        """启动主循环"""
        self._running = True
        logger.info("Agent 主循环启动")
        
        # 启动所有 Agent 的工作循环
        tasks = []
        for agent_id in self._agents:
            tasks.append(asyncio.create_task(self._agent_work_loop(agent_id)))
        
        # 启动任务处理循环
        tasks.append(asyncio.create_task(self._task_processor()))
        
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """停止主循环"""
        self._running = False
        logger.info("Agent 主循环停止")
    
    async def _agent_work_loop(self, agent_id: str):
        """单个 Agent 的工作循环"""
        agent = self._agents.get(agent_id)
        if not agent:
            return
        
        behavior = agent["behavior"]
        interval = behavior.get("work_interval_minutes", 30)
        
        while self._running:
            try:
                # 检查是否应该工作
                if agent["state"] == AgentState.IDLE:
                    # 选择一个任务
                    task = await self._select_task_for_agent(agent_id)
                    if task:
                        await self._execute_task(agent_id, task)
                
                # 等待下一个工作周期
                await asyncio.sleep(interval * 60)  # 转换为秒
                
            except Exception as e:
                logger.error("Agent 工作循环异常", agent_id=agent_id, error=str(e))
                await asyncio.sleep(60)
    
    async def _select_task_for_agent(self, agent_id: str) -> Optional[AgentTask]:
        """为 Agent 选择任务"""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        behavior = agent["behavior"]
        tasks = behavior.get("tasks", [])
        weights = behavior.get("task_weights", [])
        
        if not tasks:
            return None
        
        # 按权重随机选择任务类型
        if weights and len(weights) == len(tasks):
            task_type = random.choices(tasks, weights=weights, k=1)[0]
        else:
            task_type = random.choice(tasks)
        
        # 创建任务
        task = AgentTask(
            task_type=task_type,
            agent_id=agent_id,
            description=self._generate_task_description(task_type, agent),
            priority=random.randint(3, 8),
        )
        
        self._tasks[task.id] = task
        return task
    
    def _generate_task_description(self, task_type: TaskType, agent: dict) -> str:
        """生成任务描述"""
        descriptions = {
            TaskType.MARKET_ANALYSIS: [
                "分析 BTC/USDT 近期价格走势和量价关系",
                "研究 ETH 生态近期资金流向",
                "评估当前市场整体风险水平",
                "分析主要币种相关性变化",
            ],
            TaskType.STRATEGY_RESEARCH: [
                "探索基于链上数据的动量策略",
                "研究跨交易所套利机会",
                "分析波动率策略在当前市场的适用性",
                "评估均值回归策略的参数优化空间",
            ],
            TaskType.BACKTEST_RUN: [
                "对动量策略进行参数敏感性测试",
                "运行 walk-forward 验证实验",
                "测试策略在极端市场条件下的表现",
                "进行随机信号对照实验",
            ],
            TaskType.DATA_COLLECTION: [
                "收集链上巨鲸地址活动数据",
                "获取社交媒体情绪指标",
                "更新交易所资金费率数据",
                "收集期权市场隐含波动率",
            ],
            TaskType.RISK_ASSESSMENT: [
                "评估当前组合的尾部风险",
                "计算压力测试场景下的潜在损失",
                "审核新策略的风险敞口",
                "更新 VaR 模型参数",
            ],
            TaskType.REPORT_GENERATION: [
                "生成每日市场情报摘要",
                "编写策略研究进度报告",
                "准备投委会汇报材料",
                "更新风控合规报告",
            ],
            TaskType.PEER_REVIEW: [
                "审核 Alpha A 团队的策略提案",
                "评估回测实验的方法论",
                "检查数据处理流程的合规性",
                "验证风险模型的假设",
            ],
        }
        
        options = descriptions.get(task_type, ["执行常规任务"])
        return random.choice(options)
    
    async def _execute_task(self, agent_id: str, task: AgentTask):
        """执行任务"""
        agent = self._agents.get(agent_id)
        if not agent:
            return
        
        # 更新状态
        agent["state"] = AgentState.RESEARCHING
        agent["current_task"] = task.id
        task.status = "running"
        task.started_at = datetime.utcnow()
        
        logger.info(
            "Agent 开始执行任务",
            agent_id=agent_id,
            task_id=task.id,
            task_type=task.task_type.value,
        )
        
        # 记录活动
        self._record_activity(
            agent_id=agent_id,
            agent_name=agent["name"],
            activity_type="task_started",
            description=f"开始: {task.description}",
            metadata={"task_id": task.id, "task_type": task.task_type.value},
        )
        
        # 模拟任务执行
        execution_time = random.uniform(5, 30)  # 5-30 秒
        steps = 10
        for i in range(steps):
            if not self._running:
                break
            await asyncio.sleep(execution_time / steps)
            task.progress = (i + 1) / steps
        
        # 生成任务结果
        task.result = await self._generate_task_result(task, agent)
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        
        # 更新 Agent 状态
        agent["state"] = AgentState.IDLE
        agent["current_task"] = None
        agent["last_activity"] = datetime.utcnow()
        agent["tasks_completed"] += 1
        
        # 记录完成活动
        self._record_activity(
            agent_id=agent_id,
            agent_name=agent["name"],
            activity_type="task_completed",
            description=f"完成: {task.description}",
            metadata={
                "task_id": task.id,
                "task_type": task.task_type.value,
                "result_summary": task.result.get("summary", ""),
            },
        )
        
        logger.info(
            "Agent 完成任务",
            agent_id=agent_id,
            task_id=task.id,
            result_summary=task.result.get("summary", "")[:100],
        )
        
        # 检查是否发现了新策略
        if task.result.get("discovery"):
            agent["discoveries"].append(task.result["discovery"])
            self._record_activity(
                agent_id=agent_id,
                agent_name=agent["name"],
                activity_type="discovery",
                description=f"发现: {task.result['discovery']['title']}",
                metadata=task.result["discovery"],
            )
    
    async def _generate_task_result(self, task: AgentTask, agent: dict) -> dict:
        """生成任务结果"""
        base_result = {
            "task_id": task.id,
            "agent_id": task.agent_id,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        # 根据任务类型生成不同的结果
        if task.task_type == TaskType.MARKET_ANALYSIS:
            base_result["summary"] = f"完成市场分析: {task.description}"
            base_result["findings"] = [
                "BTC 近期呈现震荡上行态势",
                "成交量有所放大，市场活跃度提升",
                "恐惧贪婪指数处于中性偏贪婪区间",
            ]
            base_result["sentiment"] = random.choice(["bullish", "neutral", "bearish"])
            
        elif task.task_type == TaskType.STRATEGY_RESEARCH:
            base_result["summary"] = f"完成策略研究: {task.description}"
            # 有一定概率发现新策略
            if random.random() < 0.3:  # 30% 概率
                base_result["discovery"] = {
                    "type": "strategy_idea",
                    "title": f"策略发现: {random.choice(['链上动量', '情绪反转', '波动率套利', '资金费率策略'])}",
                    "confidence": round(random.uniform(0.5, 0.9), 2),
                    "estimated_sharpe": round(random.uniform(0.8, 2.5), 2),
                    "status": "proposed",
                }
            base_result["research_notes"] = "详细研究笔记..."
            
        elif task.task_type == TaskType.BACKTEST_RUN:
            sharpe = round(random.uniform(0.5, 2.5), 2)
            max_dd = round(random.uniform(-0.3, -0.05), 3)
            base_result["summary"] = f"完成回测: {task.description}"
            base_result["metrics"] = {
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "win_rate": round(random.uniform(0.4, 0.65), 2),
                "profit_factor": round(random.uniform(1.0, 2.5), 2),
            }
            base_result["passed"] = sharpe > 1.0 and max_dd > -0.2
            
        elif task.task_type == TaskType.RISK_ASSESSMENT:
            base_result["summary"] = f"完成风险评估: {task.description}"
            base_result["risk_score"] = random.randint(30, 90)
            base_result["concerns"] = [
                "当前杠杆水平需要关注",
                "部分策略相关性较高",
            ] if random.random() < 0.5 else []
            
        else:
            base_result["summary"] = f"完成任务: {task.description}"
        
        return base_result
    
    def _record_activity(
        self,
        agent_id: str,
        agent_name: str,
        activity_type: str,
        description: str,
        metadata: dict = None,
    ):
        """记录活动"""
        activity = AgentActivity(
            agent_id=agent_id,
            agent_name=agent_name,
            activity_type=activity_type,
            description=description,
            metadata=metadata or {},
        )
        self._activities.append(activity)
        
        # 只保留最近 1000 条
        if len(self._activities) > 1000:
            self._activities = self._activities[-1000:]
    
    async def _task_processor(self):
        """任务处理器"""
        while self._running:
            try:
                # 处理队列中的任务
                try:
                    task = await asyncio.wait_for(self._task_queue.get(), timeout=10)
                    # 分配给合适的 Agent
                    await self._assign_task(task)
                except asyncio.TimeoutError:
                    pass
            except Exception as e:
                logger.error("任务处理异常", error=str(e))
                await asyncio.sleep(5)
    
    async def _assign_task(self, task: AgentTask):
        """分配任务给 Agent"""
        # 找到空闲的合适 Agent
        for agent_id, agent in self._agents.items():
            if agent["state"] == AgentState.IDLE:
                behavior = agent["behavior"]
                if task.task_type in behavior.get("tasks", []):
                    await self._execute_task(agent_id, task)
                    return
        
        # 没有合适的 Agent，任务保留在队列中
        logger.warning("没有合适的 Agent 处理任务", task_id=task.id)
    
    def get_agent_status(self, agent_id: str = None) -> dict:
        """获取 Agent 状态"""
        if agent_id:
            agent = self._agents.get(agent_id)
            if not agent:
                return {"error": "Agent 不存在"}
            return {
                "id": agent["id"],
                "name": agent["name"],
                "role": agent["role"],
                "state": agent["state"].value,
                "current_task": agent["current_task"],
                "tasks_completed": agent["tasks_completed"],
                "discoveries_count": len(agent["discoveries"]),
                "last_activity": agent["last_activity"].isoformat(),
            }
        
        return {
            "total_agents": len(self._agents),
            "by_state": {
                state.value: len([a for a in self._agents.values() if a["state"] == state])
                for state in AgentState
            },
            "agents": [
                {
                    "id": a["id"],
                    "name": a["name"],
                    "state": a["state"].value,
                    "tasks_completed": a["tasks_completed"],
                }
                for a in self._agents.values()
            ],
        }
    
    def get_recent_activities(self, limit: int = 50, agent_id: str = None) -> list[dict]:
        """获取最近活动"""
        activities = self._activities
        if agent_id:
            activities = [a for a in activities if a.agent_id == agent_id]
        
        activities = sorted(activities, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [
            {
                "id": a.id,
                "agent_id": a.agent_id,
                "agent_name": a.agent_name,
                "activity_type": a.activity_type,
                "description": a.description,
                "metadata": a.metadata,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in activities
        ]
    
    def get_discoveries(self, agent_id: str = None) -> list[dict]:
        """获取发现的策略"""
        discoveries = []
        for agent in self._agents.values():
            if agent_id and agent["id"] != agent_id:
                continue
            for d in agent["discoveries"]:
                discoveries.append({
                    "agent_id": agent["id"],
                    "agent_name": agent["name"],
                    **d,
                })
        return discoveries


# 全局单例
_agent_loop: Optional[AgentLoop] = None


def get_agent_loop() -> AgentLoop:
    """获取 AgentLoop 单例"""
    global _agent_loop
    if _agent_loop is None:
        _agent_loop = AgentLoop()
    return _agent_loop
