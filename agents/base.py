# AI Quant Company - Agent 基类
"""
Agent Runtime 基类

提供:
- Agent 基础属性与方法
- LLM 调用封装 (通过 Antigravity)
- 消息发送与接收
- 任务执行框架
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import structlog
import yaml

logger = structlog.get_logger()


# ============================================
# 枚举定义
# ============================================

class CapabilityTier(str, Enum):
    """能力层级"""
    REASONING = "reasoning"   # 强推理/审查/权衡
    CODING = "coding"         # 代码/工程/调试
    REPORTING = "reporting"   # 报告/可读性/结构


class AgentStatus(str, Enum):
    """Agent 状态"""
    ACTIVE = "active"
    FROZEN = "frozen"
    DEACTIVATED = "deactivated"


class MessageType(str, Enum):
    """消息类型"""
    DM = "dm"           # 1v1 直接消息
    MEMO = "memo"       # 结构化备忘录
    MEETING = "meeting"  # 会议消息
    SYSTEM = "system"   # 系统消息


# ============================================
# 数据类
# ============================================

@dataclass
class Message:
    """消息"""
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    message_type: MessageType = MessageType.DM
    from_agent: str = ""
    to_agent: Optional[str] = None
    subject: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None


@dataclass
class Memo:
    """结构化备忘录"""
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    title: str = ""
    author: str = ""
    
    # 内容
    summary: str = ""
    body: str = ""
    conclusions: list[str] = field(default_factory=list)
    
    # 引用
    references: list[str] = field(default_factory=list)  # 引用的实验/产物 ID
    
    # 元数据
    tags: list[str] = field(default_factory=list)
    visibility: str = "department"  # department, company, board
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool = False
    output: Any = None
    error: Optional[str] = None
    compute_points_used: int = 0
    artifacts: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# ============================================
# Agent 配置
# ============================================

@dataclass
class AgentConfig:
    """Agent 配置"""
    id: str
    name: str
    name_en: str
    department: str
    is_lead: bool = False
    capability_tier: CapabilityTier = CapabilityTier.REASONING
    team: Optional[str] = None
    reports_to: Optional[str] = None
    veto_power: bool = False
    can_force_retest: bool = False
    thinking_enabled: bool = False  # 是否启用深度思考模式
    
    # 人设
    persona_style: str = ""
    persona_traits: list[str] = field(default_factory=list)
    persona_tone: str = "professional"
    system_prompt: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """从字典创建配置"""
        persona = data.get("persona", {})
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            department=data.get("department", ""),
            is_lead=data.get("is_lead", False),
            capability_tier=CapabilityTier(data.get("capability_tier", "reasoning")),
            team=data.get("team"),
            reports_to=data.get("reports_to"),
            veto_power=data.get("veto_power", False),
            can_force_retest=data.get("can_force_retest", False),
            thinking_enabled=data.get("thinking_enabled", False),
            persona_style=persona.get("style", ""),
            persona_traits=persona.get("traits", []),
            persona_tone=persona.get("tone", "professional"),
            system_prompt=data.get("system_prompt", ""),
        )


# ============================================
# LLM 客户端接口
# ============================================

class LLMClient(ABC):
    """LLM 客户端抽象基类"""
    
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_enabled: bool = False,
    ) -> str:
        """生成回复
        
        Args:
            messages: 消息列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            thinking_enabled: 是否启用深度思考模式
        """
        pass
    
    @abstractmethod
    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """带工具调用的生成"""
        pass
    
    @abstractmethod
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        """生成文本嵌入向量"""
        pass


class MockLLMClient(LLMClient):
    """模拟 LLM 客户端（用于测试）"""
    
    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_enabled: bool = False,
    ) -> str:
        if thinking_enabled:
            return "[Mock Response with Thinking] 经过深度思考分析...\n\n这是一个模拟的深度思考回复。"
        return "[Mock Response] This is a simulated response."
    
    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        return {"response": "[Mock Response]", "tool_calls": []}
    
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        # Return a mock embedding vector (1536 dimensions)
        import random
        return [random.uniform(-1, 1) for _ in range(1536)]


class AntigravityLLMClient(LLMClient):
    """Antigravity LLM 客户端
    
    通过 Antigravity 服务调用各种 LLM（OpenAI-compatible API）
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        timeout: float = 120.0,
        report_usage: bool = True,
        dashboard_url: Optional[str] = None,
    ):
        """初始化 Antigravity 客户端
        
        Args:
            api_key: API 密钥，默认从环境变量 ANTIGRAVITY_API_KEY 读取
            base_url: API 基础 URL，默认从环境变量 ANTIGRAVITY_BASE_URL 读取
            default_model: 默认使用的模型
            embedding_model: 默认的嵌入模型
            timeout: 请求超时时间（秒）
            report_usage: 是否报告 token 使用到 dashboard
            dashboard_url: Dashboard API URL
        """
        self.api_key = api_key or os.getenv("ANTIGRAVITY_API_KEY")
        self.base_url = base_url or os.getenv("ANTIGRAVITY_BASE_URL")
        self.default_model = default_model
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.timeout = timeout
        self.report_usage = report_usage
        self.dashboard_url = dashboard_url or os.getenv("DASHBOARD_API_URL", "http://localhost:8000")
        
        # 当前 agent_id（会被 BaseAgent 设置）
        self.current_agent_id: Optional[str] = None
        
        if not self.api_key:
            raise ValueError("ANTIGRAVITY_API_KEY is required")
        if not self.base_url:
            raise ValueError("ANTIGRAVITY_BASE_URL is required")
        
        # 延迟导入 openai 库
        self._client = None
        self._async_client = None
        self._http_client = None
        
        logger.info(
            "Antigravity LLM Client 初始化",
            base_url=self.base_url,
            default_model=self.default_model,
            report_usage=report_usage,
        )
    
    async def _report_token_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        thinking_enabled: bool = False,
        request_type: str = "think",
        latency_ms: int = 0,
    ):
        """报告 token 使用到 dashboard"""
        if not self.report_usage:
            return
        
        try:
            import aiohttp
            if self._http_client is None:
                self._http_client = aiohttp.ClientSession()
            
            await self._http_client.post(
                f"{self.dashboard_url}/api/system/record-tokens",
                json={
                    "agent_id": self.current_agent_id,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "thinking_enabled": thinking_enabled,
                    "request_type": request_type,
                    "latency_ms": latency_ms,
                },
                timeout=aiohttp.ClientTimeout(total=5),
            )
        except Exception as e:
            logger.debug(f"报告 token 使用失败: {e}")
    
    def _get_client(self):
        """获取同步 OpenAI 客户端"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client
    
    def _get_async_client(self):
        """获取异步 OpenAI 客户端"""
        if self._async_client is None:
            from openai import AsyncOpenAI
            self._async_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._async_client
    
    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_enabled: bool = False,
    ) -> str:
        """生成回复
        
        Args:
            messages: 消息列表
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            thinking_enabled: 是否启用深度思考模式
            
        Returns:
            生成的回复文本
        """
        client = self._get_async_client()
        model = model or self.default_model
        
        # 如果启用 thinking 模式，注入深度思考指令
        if thinking_enabled:
            thinking_instruction = """
在回答之前，请先进行深度思考：

<thinking>
1. 问题分析：这个问题的核心是什么？有哪些关键要素？
2. 多角度考量：从不同利益相关方的角度思考
3. 风险评估：有哪些潜在风险和边界条件？
4. 逻辑推理：我的推理链条是否完整、有无漏洞？
5. 反向验证：如果我的结论是错的，最可能是哪里出了问题？
</thinking>

请先在 <thinking> 标签中展示你的思考过程，然后给出最终回答。
深度思考对于这类问题尤为重要，请确保推理充分。
"""
            # 在用户消息前插入思考指令
            messages = messages.copy()
            if messages and messages[-1]["role"] == "user":
                messages[-1]["content"] = thinking_instruction + "\n\n" + messages[-1]["content"]
            
            # 使用更低的温度确保推理更严谨
            temperature = min(temperature, 0.5)
            # 增加 token 限制以容纳思考过程
            max_tokens = max(max_tokens, 8192)
        
        import time
        start_time = time.time()
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            result = response.choices[0].message.content or ""
            
            # 获取 token 使用量
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            
            logger.debug(
                "LLM 请求完成",
                model=model,
                thinking_enabled=thinking_enabled,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
            )
            
            # 报告 token 使用
            await self._report_token_usage(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                thinking_enabled=thinking_enabled,
                request_type="think",
                latency_ms=latency_ms,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "LLM 请求失败",
                model=model,
                error=str(e),
            )
            raise
    
    async def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """带工具调用的生成
        
        Args:
            messages: 消息列表
            tools: 工具定义列表（OpenAI function calling 格式）
            model: 使用的模型
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            
        Returns:
            包含 response 和 tool_calls 的字典
        """
        client = self._get_async_client()
        model = model or self.default_model
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            message = response.choices[0].message
            result = {
                "response": message.content or "",
                "tool_calls": [],
            }
            
            # 处理工具调用
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    })
            
            logger.debug(
                "LLM 工具调用请求完成",
                model=model,
                tool_calls_count=len(result["tool_calls"]),
                usage=response.usage.model_dump() if response.usage else None,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "LLM 工具调用请求失败",
                model=model,
                error=str(e),
            )
            raise
    
    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        """生成文本嵌入向量
        
        Args:
            text: 输入文本
            model: 嵌入模型
            
        Returns:
            嵌入向量
        """
        client = self._get_async_client()
        model = model or self.embedding_model
        
        try:
            response = await client.embeddings.create(
                model=model,
                input=text,
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(
                "嵌入请求完成",
                model=model,
                input_length=len(text),
                embedding_dim=len(embedding),
            )
            
            return embedding
            
        except Exception as e:
            logger.error(
                "嵌入请求失败",
                model=model,
                error=str(e),
            )
            raise
    
    async def embed_batch(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """批量生成文本嵌入向量
        
        Args:
            texts: 输入文本列表
            model: 嵌入模型
            
        Returns:
            嵌入向量列表
        """
        client = self._get_async_client()
        model = model or self.embedding_model
        
        try:
            response = await client.embeddings.create(
                model=model,
                input=texts,
            )
            
            embeddings = [item.embedding for item in response.data]
            
            logger.debug(
                "批量嵌入请求完成",
                model=model,
                batch_size=len(texts),
                embedding_dim=len(embeddings[0]) if embeddings else 0,
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(
                "批量嵌入请求失败",
                model=model,
                error=str(e),
            )
            raise


# ============================================
# LLM 客户端工厂
# ============================================

def create_llm_client(
    provider: str = "antigravity",
    **kwargs,
) -> LLMClient:
    """创建 LLM 客户端
    
    Args:
        provider: 提供商名称 ("antigravity" 或 "mock")
        **kwargs: 传递给客户端的参数
        
    Returns:
        LLM 客户端实例
    """
    if provider == "mock":
        return MockLLMClient()
    elif provider == "antigravity":
        return AntigravityLLMClient(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ============================================
# Agent 基类
# ============================================

class BaseAgent(ABC):
    """Agent 基类
    
    所有 Agent 都继承自此类，实现特定的业务逻辑。
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm_client: Optional[LLMClient] = None,
    ):
        """初始化 Agent
        
        Args:
            config: Agent 配置
            llm_client: LLM 客户端
        """
        self.config = config
        self.llm_client = llm_client or MockLLMClient()
        
        # 状态
        self.status = AgentStatus.ACTIVE
        self.budget_remaining: int = 0
        self.reputation_score: float = 0.5
        
        # 消息队列
        self._inbox: list[Message] = []
        self._outbox: list[Message] = []
        
        # 当前任务
        self._current_task: Optional[dict] = None
        
        logger.info(
            "Agent 初始化",
            agent_id=self.config.id,
            name=self.config.name,
            department=self.config.department,
        )
    
    @property
    def agent_id(self) -> str:
        return self.config.id
    
    @property
    def is_lead(self) -> bool:
        return self.config.is_lead
    
    @property
    def has_veto_power(self) -> bool:
        return self.config.veto_power
    
    @property
    def can_request_meeting(self) -> bool:
        """是否可以申请会议（只有 Lead 可以）"""
        return self.config.is_lead
    
    # ============================================
    # 消息方法
    # ============================================
    
    def send_dm(
        self,
        to_agent: str,
        content: str,
        subject: str = "",
    ) -> Message:
        """发送直接消息
        
        Args:
            to_agent: 接收者 agent_id
            content: 消息内容
            subject: 主题
            
        Returns:
            消息对象
        """
        message = Message(
            message_type=MessageType.DM,
            from_agent=self.agent_id,
            to_agent=to_agent,
            subject=subject,
            content=content,
        )
        self._outbox.append(message)
        
        logger.info(
            "发送 DM",
            from_agent=self.agent_id,
            to_agent=to_agent,
            subject=subject,
        )
        
        return message
    
    def receive_message(self, message: Message) -> None:
        """接收消息
        
        Args:
            message: 消息对象
        """
        self._inbox.append(message)
        logger.info(
            "收到消息",
            agent_id=self.agent_id,
            from_agent=message.from_agent,
            message_type=message.message_type,
        )
    
    def get_unread_messages(self) -> list[Message]:
        """获取未读消息"""
        return [m for m in self._inbox if m.read_at is None]
    
    def mark_as_read(self, message_id: str) -> None:
        """标记消息为已读"""
        for m in self._inbox:
            if m.id == message_id:
                m.read_at = datetime.utcnow()
                break
    
    # ============================================
    # Memo 方法
    # ============================================
    
    def submit_memo(self, memo: Memo) -> Message:
        """提交备忘录
        
        Args:
            memo: 备忘录
            
        Returns:
            包含 memo 的消息
        """
        memo.author = self.agent_id
        
        message = Message(
            message_type=MessageType.MEMO,
            from_agent=self.agent_id,
            subject=memo.title,
            content=memo.body,
            metadata={
                "memo_id": str(memo.id),
                "summary": memo.summary,
                "conclusions": memo.conclusions,
                "tags": memo.tags,
                "visibility": memo.visibility,
            },
        )
        self._outbox.append(message)
        
        logger.info(
            "提交 Memo",
            agent_id=self.agent_id,
            memo_title=memo.title,
            visibility=memo.visibility,
        )
        
        return message
    
    # ============================================
    # LLM 交互方法
    # ============================================
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        parts = [self.config.system_prompt]
        
        if self.config.persona_style:
            parts.append(f"\n你的风格: {self.config.persona_style}")
        
        if self.config.persona_traits:
            traits = "\n".join(f"- {t}" for t in self.config.persona_traits)
            parts.append(f"\n你的特点:\n{traits}")
        
        return "\n".join(parts)
    
    async def think(
        self, 
        prompt: str, 
        context: Optional[dict] = None,
        force_thinking: Optional[bool] = None,
    ) -> str:
        """思考并生成回复
        
        Args:
            prompt: 输入提示
            context: 上下文信息
            force_thinking: 强制启用/禁用深度思考（默认使用配置）
            
        Returns:
            生成的回复
        """
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]
        
        if context:
            context_str = yaml.dump(context, allow_unicode=True)
            messages.insert(1, {
                "role": "user",
                "content": f"上下文信息:\n```yaml\n{context_str}\n```",
            })
        
        # 确定是否启用深度思考
        thinking_enabled = force_thinking if force_thinking is not None else self.config.thinking_enabled
        
        response = await self.llm_client.complete(
            messages, 
            thinking_enabled=thinking_enabled,
        )
        
        logger.info(
            "Agent 思考",
            agent_id=self.agent_id,
            thinking_enabled=thinking_enabled,
            prompt_length=len(prompt),
            response_length=len(response),
        )
        
        return response
    
    async def analyze(
        self,
        data: Any,
        question: str,
        format_hint: Optional[str] = None,
    ) -> str:
        """分析数据并回答问题
        
        Args:
            data: 待分析数据
            question: 问题
            format_hint: 输出格式提示
            
        Returns:
            分析结果
        """
        prompt = f"请分析以下数据并回答问题。\n\n问题: {question}\n\n数据:\n{data}"
        
        if format_hint:
            prompt += f"\n\n请按以下格式输出:\n{format_hint}"
        
        return await self.think(prompt)
    
    # ============================================
    # 任务执行方法
    # ============================================
    
    @abstractmethod
    async def execute_task(self, task: dict) -> TaskResult:
        """执行任务（子类必须实现）
        
        Args:
            task: 任务定义
            
        Returns:
            任务结果
        """
        pass
    
    async def process_inbox(self) -> list[TaskResult]:
        """处理收件箱中的消息
        
        Returns:
            处理结果列表
        """
        results = []
        unread = self.get_unread_messages()
        
        for message in unread:
            self.mark_as_read(message.id)
            
            # 根据消息类型处理
            if message.message_type == MessageType.DM:
                result = await self._handle_dm(message)
            elif message.message_type == MessageType.MEMO:
                result = await self._handle_memo(message)
            elif message.message_type == MessageType.SYSTEM:
                result = await self._handle_system_message(message)
            else:
                result = TaskResult(success=True, output="消息已阅")
            
            results.append(result)
        
        return results
    
    async def _handle_dm(self, message: Message) -> TaskResult:
        """处理直接消息
        
        默认实现：使用 LLM 生成回复
        子类可以覆盖此方法
        """
        response = await self.think(
            f"收到来自 {message.from_agent} 的消息:\n\n{message.content}\n\n请回复。"
        )
        
        # 发送回复
        self.send_dm(
            to_agent=message.from_agent,
            content=response,
            subject=f"Re: {message.subject}",
        )
        
        return TaskResult(success=True, output=response)
    
    async def _handle_memo(self, message: Message) -> TaskResult:
        """处理备忘录
        
        默认实现：记录已收到
        子类可以覆盖此方法
        """
        logger.info(
            "收到 Memo",
            agent_id=self.agent_id,
            from_agent=message.from_agent,
            title=message.subject,
        )
        return TaskResult(success=True, output="Memo 已收到")
    
    async def _handle_system_message(self, message: Message) -> TaskResult:
        """处理系统消息
        
        子类可以覆盖此方法
        """
        logger.info(
            "收到系统消息",
            agent_id=self.agent_id,
            content=message.content[:100],
        )
        return TaskResult(success=True, output="系统消息已处理")
    
    # ============================================
    # 状态方法
    # ============================================
    
    def freeze(self, reason: str = "") -> None:
        """冻结 Agent"""
        self.status = AgentStatus.FROZEN
        logger.warning(
            "Agent 被冻结",
            agent_id=self.agent_id,
            reason=reason,
        )
    
    def unfreeze(self) -> None:
        """解冻 Agent"""
        self.status = AgentStatus.ACTIVE
        logger.info("Agent 已解冻", agent_id=self.agent_id)
    
    def deactivate(self, reason: str = "") -> None:
        """停用 Agent"""
        self.status = AgentStatus.DEACTIVATED
        logger.warning(
            "Agent 被停用",
            agent_id=self.agent_id,
            reason=reason,
        )
    
    def update_budget(self, points: int) -> None:
        """更新预算"""
        self.budget_remaining = points
    
    def update_reputation(self, score: float) -> None:
        """更新声誉分数"""
        self.reputation_score = max(0.0, min(1.0, score))
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.config.id,
            "name": self.config.name,
            "name_en": self.config.name_en,
            "department": self.config.department,
            "is_lead": self.config.is_lead,
            "capability_tier": self.config.capability_tier.value,
            "thinking_enabled": self.config.thinking_enabled,
            "status": self.status.value,
            "budget_remaining": self.budget_remaining,
            "reputation_score": self.reputation_score,
        }


# ============================================
# Agent 工厂
# ============================================

class AgentFactory:
    """Agent 工厂
    
    从配置文件创建 Agent 实例
    """
    
    def __init__(self, config_path: str = "configs/agents.yaml"):
        """初始化工厂
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self._configs: dict[str, AgentConfig] = {}
        self._load_configs()
    
    def _load_configs(self) -> None:
        """加载配置"""
        if not os.path.exists(self.config_path):
            logger.warning("Agent 配置文件不存在", path=self.config_path)
            return
        
        with open(self.config_path) as f:
            data = yaml.safe_load(f)
        
        agents_data = data.get("agents", {})
        for agent_id, agent_data in agents_data.items():
            agent_data["id"] = agent_id
            self._configs[agent_id] = AgentConfig.from_dict(agent_data)
        
        logger.info("加载 Agent 配置", count=len(self._configs))
    
    def get_config(self, agent_id: str) -> Optional[AgentConfig]:
        """获取 Agent 配置"""
        return self._configs.get(agent_id)
    
    def list_agents(self) -> list[str]:
        """列出所有 Agent ID"""
        return list(self._configs.keys())
    
    def list_by_department(self, department: str) -> list[str]:
        """按部门列出 Agent"""
        return [
            agent_id
            for agent_id, config in self._configs.items()
            if config.department == department
        ]
    
    def list_leads(self) -> list[str]:
        """列出所有 Lead"""
        return [
            agent_id
            for agent_id, config in self._configs.items()
            if config.is_lead
        ]


# ============================================
# 简单 Agent 实现（用于测试）
# ============================================

class SimpleAgent(BaseAgent):
    """简单 Agent 实现
    
    用于测试和演示
    """
    
    async def execute_task(self, task: dict) -> TaskResult:
        """执行任务"""
        task_type = task.get("type", "unknown")
        
        if task_type == "analyze":
            result = await self.analyze(
                data=task.get("data"),
                question=task.get("question", "请分析这些数据"),
            )
            return TaskResult(success=True, output=result)
        
        elif task_type == "respond":
            result = await self.think(task.get("prompt", ""))
            return TaskResult(success=True, output=result)
        
        else:
            return TaskResult(
                success=False,
                error=f"未知任务类型: {task_type}",
            )
