# AI Quant Company - Agent Runtime
"""
Agent 运行时容器

管理 Agent 的生命周期和执行环境：
- 加载 Agent 配置
- 初始化 LLM 客户端
- 处理消息循环
- 执行任务队列
- 状态管理和持久化
"""

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import structlog
import yaml

from agents.base import (
    AgentConfig,
    AgentStatus,
    AntigravityLLMClient,
    BaseAgent,
    LLMClient,
    Message,
    MessageType,
    MockLLMClient,
    TaskResult,
)
from orchestrator.message_bus import BusMessage, ChannelType, MessageBus, get_message_bus
from tools.registry import get_tool_schemas

logger = structlog.get_logger()


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class AgentTask:
    """Agent 任务"""
    id: str = field(default_factory=lambda: str(uuid4()))
    task_type: str = ""  # think, respond, execute, review, report
    payload: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    retries: int = 0
    max_retries: int = 3


class RuntimeAgent(BaseAgent):
    """运行时 Agent
    
    具有完整运行时环境的 Agent 实现
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm_client: Optional[LLMClient] = None,
        message_bus: Optional[MessageBus] = None,
    ):
        super().__init__(config, llm_client)
        
        self.message_bus = message_bus or get_message_bus()
        
        # 任务队列
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_task: Optional[AgentTask] = None
        
        # 活动日志
        self._activity_log: list[dict] = []
        self._max_activity_log = 100
        
        # 对话历史（用于上下文）
        self._conversation_history: list[dict] = []
        self._max_conversation_history = 50
        
        # 工具调用历史
        self._tool_calls: list[dict] = []
        
        # 可用工具
        self._available_tools = get_tool_schemas()
        
        # 运行状态
        self._is_running = False
        self._last_active = datetime.utcnow()
        
        # 订阅消息
        self._setup_subscriptions()
    
    def _setup_subscriptions(self):
        """设置消息订阅"""
        # 订阅直接消息
        self.message_bus.subscribe(
            subscriber_id=self.agent_id,
            channel_type=ChannelType.DIRECT,
            channel_id=self.agent_id,
        )
        
        # 订阅部门消息
        self.message_bus.subscribe(
            subscriber_id=self.agent_id,
            channel_type=ChannelType.DEPARTMENT,
            channel_id=self.config.department,
        )
        
        # 订阅团队消息（如果有）
        if self.config.team:
            self.message_bus.subscribe(
                subscriber_id=self.agent_id,
                channel_type=ChannelType.TEAM,
                channel_id=self.config.team,
            )
        
        # 订阅系统消息
        self.message_bus.subscribe(
            subscriber_id=self.agent_id,
            channel_type=ChannelType.SYSTEM,
            channel_id=self.agent_id,
        )
    
    # ============================================
    # 任务管理
    # ============================================
    
    async def add_task(
        self,
        task_type: str,
        payload: dict,
        priority: TaskPriority = TaskPriority.NORMAL,
        deadline: datetime = None,
    ) -> AgentTask:
        """添加任务到队列"""
        task = AgentTask(
            task_type=task_type,
            payload=payload,
            priority=priority,
            deadline=deadline,
        )
        
        # PriorityQueue 使用元组，第一个元素是优先级（负数使高优先级排前面）
        await self._task_queue.put((-priority.value, task.created_at, task))
        
        logger.info(
            "任务已添加",
            agent_id=self.agent_id,
            task_id=task.id,
            task_type=task_type,
            priority=priority.name,
        )
        
        return task
    
    async def process_next_task(self) -> Optional[TaskResult]:
        """处理下一个任务"""
        if self._task_queue.empty():
            return None
        
        _, _, task = await self._task_queue.get()
        self._running_task = task
        task.started_at = datetime.utcnow()
        
        logger.info(
            "开始处理任务",
            agent_id=self.agent_id,
            task_id=task.id,
            task_type=task.task_type,
        )
        
        try:
            result = await self.execute_task(task.payload)
            task.result = result
            task.completed_at = datetime.utcnow()
            
            self._log_activity("task_completed", {
                "task_id": task.id,
                "task_type": task.task_type,
                "success": result.success,
                "duration": (task.completed_at - task.started_at).total_seconds(),
            })
            
        except Exception as e:
            task.retries += 1
            if task.retries < task.max_retries:
                # 重新入队
                await self._task_queue.put((-task.priority.value, task.created_at, task))
                logger.warning(
                    "任务失败，重试中",
                    agent_id=self.agent_id,
                    task_id=task.id,
                    retry=task.retries,
                    error=str(e),
                )
            else:
                task.result = TaskResult(success=False, error=str(e))
                task.completed_at = datetime.utcnow()
                logger.error(
                    "任务失败，已达最大重试次数",
                    agent_id=self.agent_id,
                    task_id=task.id,
                    error=str(e),
                )
        
        finally:
            self._running_task = None
        
        return task.result
    
    async def execute_task(self, task: dict) -> TaskResult:
        """执行任务"""
        task_type = task.get("type", "think")
        
        if task_type == "think":
            # 思考任务
            prompt = task.get("prompt", "")
            context = task.get("context")
            response = await self.think(prompt, context)
            return TaskResult(success=True, output=response)
        
        elif task_type == "respond":
            # 回复消息
            message_content = task.get("message", "")
            from_agent = task.get("from_agent", "")
            response = await self._generate_response(message_content, from_agent)
            
            # 发送回复
            if from_agent:
                await self.message_bus.send_direct(
                    from_agent=self.agent_id,
                    to_agent=from_agent,
                    content=response,
                    subject=f"Re: {task.get('subject', '')}",
                )
            
            return TaskResult(success=True, output=response)
        
        elif task_type == "review":
            # 审核任务
            item = task.get("item", {})
            review_type = task.get("review_type", "general")
            response = await self._conduct_review(item, review_type)
            return TaskResult(success=True, output=response)
        
        elif task_type == "report":
            # 生成报告
            report_type = task.get("report_type", "summary")
            data = task.get("data", {})
            response = await self._generate_report(report_type, data)
            return TaskResult(success=True, output=response)
        
        elif task_type == "meeting":
            # 参与会议
            meeting_id = task.get("meeting_id")
            agenda = task.get("agenda", "")
            response = await self._participate_meeting(meeting_id, agenda)
            return TaskResult(success=True, output=response)
        
        else:
            return TaskResult(
                success=False,
                error=f"未知任务类型: {task_type}",
            )
    
    # ============================================
    # 消息处理
    # ============================================
    
    async def process_messages(self) -> int:
        """处理待处理消息
        
        Returns:
            处理的消息数量
        """
        messages = await self.message_bus.get_messages(
            agent_id=self.agent_id,
            timeout=0.1,
            max_messages=10,
        )
        
        for message in messages:
            await self._handle_bus_message(message)
        
        return len(messages)
    
    async def _handle_bus_message(self, message: BusMessage):
        """处理总线消息"""
        self._last_active = datetime.utcnow()
        
        self._log_activity("message_received", {
            "message_id": message.id,
            "from_agent": message.from_agent,
            "channel_type": message.channel_type.value,
            "message_type": message.message_type,
        })
        
        if message.channel_type == ChannelType.SYSTEM:
            # 系统消息直接处理
            await self._handle_system_message_bus(message)
        
        elif message.channel_type == ChannelType.MEETING:
            # 会议消息
            await self._handle_meeting_message(message)
        
        else:
            # 其他消息转换为任务
            await self.add_task(
                task_type="respond",
                payload={
                    "type": "respond",
                    "message": message.content,
                    "from_agent": message.from_agent,
                    "subject": message.subject,
                    "metadata": message.metadata,
                },
                priority=TaskPriority(message.priority) if message.priority <= 3 else TaskPriority.URGENT,
            )
    
    async def _handle_system_message_bus(self, message: BusMessage):
        """处理系统消息"""
        metadata = message.metadata or {}
        
        if "meeting_id" in metadata:
            # 会议相关通知
            logger.info(
                "收到会议通知",
                agent_id=self.agent_id,
                meeting_id=metadata["meeting_id"],
                subject=message.subject,
            )
    
    async def _handle_meeting_message(self, message: BusMessage):
        """处理会议消息"""
        # 记录会议发言
        self._conversation_history.append({
            "role": "user",
            "content": f"[{message.from_agent}]: {message.content}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # 生成回复（如果需要）
        if message.metadata.get("requires_response"):
            await self.add_task(
                task_type="meeting",
                payload={
                    "type": "meeting",
                    "meeting_id": message.channel_id,
                    "message": message.content,
                    "from_agent": message.from_agent,
                },
                priority=TaskPriority.HIGH,
            )
    
    # ============================================
    # LLM 交互
    # ============================================
    
    async def _generate_response(
        self,
        message: str,
        from_agent: str,
    ) -> str:
        """生成对消息的回复"""
        # 构建上下文
        context = {
            "from_agent": from_agent,
            "my_role": self.config.name,
            "department": self.config.department,
            "recent_activity": self._activity_log[-5:] if self._activity_log else [],
        }
        
        prompt = f"""
收到来自 {from_agent} 的消息：

{message}

请根据你的角色和职责进行回复。
"""
        
        response = await self.think(prompt, context)
        
        # 记录对话
        self._conversation_history.append({
            "role": "user",
            "content": f"[{from_agent}]: {message}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # 限制历史长度
        if len(self._conversation_history) > self._max_conversation_history:
            self._conversation_history = self._conversation_history[-self._max_conversation_history:]
        
        return response
    
    async def _conduct_review(
        self,
        item: dict,
        review_type: str,
    ) -> dict:
        """进行审核"""
        prompt = f"""
请对以下{review_type}进行审核：

{yaml.dump(item, allow_unicode=True)}

审核要点：
1. 是否符合流程要求？
2. 数据是否完整？
3. 是否有明显问题或风险？
4. 你的建议是什么？

请输出结构化的审核意见，包括：
- decision: approved / rejected / need_revision
- reason: 理由
- comments: 详细意见
- suggestions: 建议（如果有）
"""
        
        response = await self.think(prompt)
        
        # 尝试解析结构化输出
        try:
            # 简单解析
            decision = "need_revision"
            if "approved" in response.lower() or "通过" in response:
                decision = "approved"
            elif "rejected" in response.lower() or "拒绝" in response:
                decision = "rejected"
            
            return {
                "decision": decision,
                "response": response,
                "reviewer": self.agent_id,
                "reviewed_at": datetime.utcnow().isoformat(),
            }
        except Exception:
            return {
                "decision": "need_revision",
                "response": response,
                "reviewer": self.agent_id,
                "reviewed_at": datetime.utcnow().isoformat(),
            }
    
    async def _generate_report(
        self,
        report_type: str,
        data: dict,
    ) -> str:
        """生成报告"""
        prompt = f"""
请生成一份{report_type}报告。

数据：
{yaml.dump(data, allow_unicode=True)}

要求：
1. 结构清晰，层次分明
2. 数据准确，引用有据
3. 结论明确，建议具体
4. 适合{self.config.department}的报告风格
"""
        
        return await self.think(prompt)
    
    async def _participate_meeting(
        self,
        meeting_id: str,
        agenda: str,
    ) -> str:
        """参与会议讨论"""
        recent_messages = [
            m for m in self._conversation_history
            if "meeting" in m.get("timestamp", "").lower()
        ][-10:]
        
        context_str = "\n".join([
            f"{m['role']}: {m['content']}"
            for m in recent_messages
        ])
        
        prompt = f"""
你正在参加一个会议。

会议议程：{agenda}

最近的讨论：
{context_str}

请根据你的角色（{self.config.name}）发表你的意见或提问。
保持专业、简洁、有建设性。
"""
        
        response = await self.think(prompt)
        
        # 发送到会议
        await self.message_bus.send_to_meeting(
            meeting_id=meeting_id,
            from_agent=self.agent_id,
            content=response,
            message_type="discussion",
        )
        
        return response
    
    # ============================================
    # 主动行为
    # ============================================
    
    async def check_for_work(self) -> bool:
        """检查是否有工作需要做
        
        Returns:
            是否添加了新任务
        """
        # 这个方法可以被子类覆盖，实现特定角色的主动行为
        return False
    
    async def daily_routine(self):
        """每日例行工作"""
        # 可以被子类覆盖
        pass
    
    # ============================================
    # 运行循环
    # ============================================
    
    async def run_once(self) -> dict:
        """运行一次迭代
        
        Returns:
            执行统计
        """
        stats = {
            "messages_processed": 0,
            "tasks_completed": 0,
            "errors": 0,
        }
        
        if self.status != AgentStatus.ACTIVE:
            return stats
        
        try:
            # 1. 处理消息
            stats["messages_processed"] = await self.process_messages()
            
            # 2. 检查是否有主动工作
            await self.check_for_work()
            
            # 3. 处理任务
            if not self._task_queue.empty():
                result = await self.process_next_task()
                if result:
                    stats["tasks_completed"] = 1
                    if not result.success:
                        stats["errors"] = 1
            
            self._last_active = datetime.utcnow()
            
        except Exception as e:
            stats["errors"] = 1
            logger.error(
                "Agent 运行错误",
                agent_id=self.agent_id,
                error=str(e),
            )
        
        return stats
    
    async def run_forever(self, interval: float = 1.0):
        """持续运行
        
        Args:
            interval: 迭代间隔（秒）
        """
        self._is_running = True
        logger.info(f"Agent {self.agent_id} 开始运行")
        
        while self._is_running:
            await self.run_once()
            await asyncio.sleep(interval)
        
        logger.info(f"Agent {self.agent_id} 已停止")
    
    def stop(self):
        """停止运行"""
        self._is_running = False
    
    # ============================================
    # 活动日志
    # ============================================
    
    def _log_activity(self, activity_type: str, details: dict):
        """记录活动"""
        entry = {
            "type": activity_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details,
        }
        
        self._activity_log.append(entry)
        
        if len(self._activity_log) > self._max_activity_log:
            self._activity_log = self._activity_log[-self._max_activity_log:]
    
    def get_activity_log(self, limit: int = 20) -> list[dict]:
        """获取活动日志"""
        return self._activity_log[-limit:]
    
    # ============================================
    # 状态查询
    # ============================================
    
    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "department": self.config.department,
            "status": self.status.value,
            "is_running": self._is_running,
            "pending_tasks": self._task_queue.qsize(),
            "running_task": self._running_task.task_type if self._running_task else None,
            "last_active": self._last_active.isoformat(),
            "budget_remaining": self.budget_remaining,
            "reputation_score": self.reputation_score,
            "recent_activity_count": len(self._activity_log),
        }


class AgentRuntime:
    """Agent 运行时管理器
    
    管理所有 Agent 的生命周期
    """
    
    def __init__(
        self,
        config_path: str = "configs/agents.yaml",
        use_mock_llm: bool = False,
    ):
        """初始化运行时
        
        Args:
            config_path: Agent 配置文件路径
            use_mock_llm: 是否使用 Mock LLM（用于测试）
        """
        self.config_path = config_path
        self.use_mock_llm = use_mock_llm
        
        self._agents: dict[str, RuntimeAgent] = {}
        self._llm_client: Optional[LLMClient] = None
        self._message_bus: Optional[MessageBus] = None
        self._is_running = False
        
        # 加载配置
        self._configs: dict[str, AgentConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """加载 Agent 配置"""
        if not os.path.exists(self.config_path):
            logger.warning(f"配置文件不存在: {self.config_path}")
            return
        
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        
        agents_data = data.get("agents", {})
        for agent_id, agent_data in agents_data.items():
            agent_data["id"] = agent_id
            self._configs[agent_id] = AgentConfig.from_dict(agent_data)
        
        logger.info(f"加载了 {len(self._configs)} 个 Agent 配置")
    
    async def start(self):
        """启动运行时"""
        logger.info("启动 Agent Runtime...")
        
        # 初始化消息总线
        self._message_bus = get_message_bus()
        await self._message_bus.start()
        
        # 初始化 LLM 客户端
        if self.use_mock_llm:
            self._llm_client = MockLLMClient()
            logger.info("使用 Mock LLM 客户端")
        else:
            try:
                self._llm_client = AntigravityLLMClient()
                logger.info("使用 Antigravity LLM 客户端")
            except Exception as e:
                logger.warning(f"Antigravity 初始化失败，使用 Mock: {e}")
                self._llm_client = MockLLMClient()
        
        # 创建所有 Agent
        for agent_id, config in self._configs.items():
            agent = RuntimeAgent(
                config=config,
                llm_client=self._llm_client,
                message_bus=self._message_bus,
            )
            self._agents[agent_id] = agent
            logger.info(f"Agent 已创建: {agent_id} ({config.name})")
        
        self._is_running = True
        logger.info(f"Agent Runtime 启动完成，共 {len(self._agents)} 个 Agent")
    
    async def stop(self):
        """停止运行时"""
        logger.info("停止 Agent Runtime...")
        
        self._is_running = False
        
        # 停止所有 Agent
        for agent in self._agents.values():
            agent.stop()
        
        # 停止消息总线
        if self._message_bus:
            await self._message_bus.stop()
        
        logger.info("Agent Runtime 已停止")
    
    def get_agent(self, agent_id: str) -> Optional[RuntimeAgent]:
        """获取 Agent"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> list[str]:
        """列出所有 Agent ID"""
        return list(self._agents.keys())
    
    def get_all_agents(self) -> dict[str, RuntimeAgent]:
        """获取所有 Agent"""
        return self._agents.copy()
    
    def get_agents_by_department(self, department: str) -> list[RuntimeAgent]:
        """按部门获取 Agent"""
        return [
            agent for agent in self._agents.values()
            if agent.config.department == department
        ]
    
    def get_agent_statuses(self) -> list[dict]:
        """获取所有 Agent 状态"""
        return [agent.get_status() for agent in self._agents.values()]
    
    async def send_message_to_agent(
        self,
        to_agent: str,
        content: str,
        from_agent: str = "chairman",
        subject: str = "",
    ) -> bool:
        """发送消息给 Agent
        
        Args:
            to_agent: 接收者 Agent ID
            content: 消息内容
            from_agent: 发送者（默认董事长）
            subject: 主题
            
        Returns:
            是否成功
        """
        if to_agent not in self._agents:
            return False
        
        await self._message_bus.send_direct(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            subject=subject,
        )
        return True
    
    async def broadcast_message(
        self,
        content: str,
        from_agent: str = "chairman",
        subject: str = "公告",
    ):
        """广播消息"""
        await self._message_bus.broadcast(
            from_agent=from_agent,
            content=content,
            subject=subject,
        )


# 全局单例
_agent_runtime: Optional[AgentRuntime] = None


def get_agent_runtime() -> AgentRuntime:
    """获取 Agent 运行时单例"""
    global _agent_runtime
    if _agent_runtime is None:
        _agent_runtime = AgentRuntime()
    return _agent_runtime


async def init_agent_runtime(use_mock: bool = False) -> AgentRuntime:
    """初始化并启动 Agent 运行时"""
    global _agent_runtime
    _agent_runtime = AgentRuntime(use_mock_llm=use_mock)
    await _agent_runtime.start()
    return _agent_runtime
