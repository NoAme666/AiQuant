# AI Quant Company - Message Bus
"""
Agent 间消息总线

基于内存队列（可选 Redis）实现 Agent 间通信：
- 点对点消息 (DM)
- 广播消息 (Broadcast)
- 主题订阅 (Pub/Sub)
- 会议消息 (Meeting Room)
"""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class ChannelType(str, Enum):
    """频道类型"""
    DIRECT = "direct"           # 点对点
    BROADCAST = "broadcast"     # 全员广播
    DEPARTMENT = "department"   # 部门频道
    TEAM = "team"               # 团队频道
    MEETING = "meeting"         # 会议室
    SYSTEM = "system"           # 系统通知


@dataclass
class BusMessage:
    """总线消息"""
    id: str = field(default_factory=lambda: str(uuid4()))
    channel_type: ChannelType = ChannelType.DIRECT
    channel_id: str = ""  # 频道标识（agent_id, department_id, meeting_id 等）
    
    from_agent: str = ""
    to_agent: Optional[str] = None  # 点对点消息的接收者
    
    subject: str = ""
    content: str = ""
    message_type: str = "text"  # text, memo, task, approval, system
    metadata: dict = field(default_factory=dict)
    
    priority: int = 0  # 0=normal, 1=high, 2=urgent
    requires_ack: bool = False
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None


@dataclass
class Subscription:
    """订阅"""
    subscriber_id: str
    channel_type: ChannelType
    channel_id: str
    callback: Optional[Callable] = None
    filter_func: Optional[Callable] = None


class MessageBus:
    """消息总线
    
    负责 Agent 间的消息路由和投递
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """初始化消息总线
        
        Args:
            redis_url: Redis 连接 URL（可选，不提供则使用内存队列）
        """
        self.redis_url = redis_url
        self._redis_client = None
        
        # 内存存储
        self._queues: dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue())
        self._subscriptions: list[Subscription] = []
        self._message_history: list[BusMessage] = []
        self._max_history = 10000
        
        # 活跃会议
        self._active_meetings: dict[str, dict] = {}
        
        # 消息处理器
        self._handlers: dict[str, Callable] = {}
        
        # 统计
        self._stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
        }
        
        logger.info("MessageBus 初始化", use_redis=bool(redis_url))
    
    async def start(self):
        """启动消息总线"""
        if self.redis_url:
            try:
                import redis.asyncio as redis
                self._redis_client = redis.from_url(self.redis_url)
                await self._redis_client.ping()
                logger.info("Redis 连接成功", url=self.redis_url)
            except Exception as e:
                logger.warning(f"Redis 连接失败，使用内存队列: {e}")
                self._redis_client = None
        
        logger.info("MessageBus 已启动")
    
    async def stop(self):
        """停止消息总线"""
        if self._redis_client:
            await self._redis_client.close()
        logger.info("MessageBus 已停止")
    
    # ============================================
    # 发送消息
    # ============================================
    
    async def send_direct(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        subject: str = "",
        message_type: str = "text",
        metadata: dict = None,
        priority: int = 0,
    ) -> BusMessage:
        """发送点对点消息
        
        Args:
            from_agent: 发送者 agent_id
            to_agent: 接收者 agent_id
            content: 消息内容
            subject: 主题
            message_type: 消息类型
            metadata: 元数据
            priority: 优先级
            
        Returns:
            消息对象
        """
        message = BusMessage(
            channel_type=ChannelType.DIRECT,
            channel_id=to_agent,
            from_agent=from_agent,
            to_agent=to_agent,
            subject=subject,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            priority=priority,
        )
        
        await self._deliver_message(message)
        return message
    
    async def send_to_department(
        self,
        from_agent: str,
        department_id: str,
        content: str,
        subject: str = "",
        message_type: str = "text",
        metadata: dict = None,
    ) -> BusMessage:
        """发送部门消息"""
        message = BusMessage(
            channel_type=ChannelType.DEPARTMENT,
            channel_id=department_id,
            from_agent=from_agent,
            subject=subject,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        
        await self._deliver_message(message)
        return message
    
    async def send_to_team(
        self,
        from_agent: str,
        team_id: str,
        content: str,
        subject: str = "",
        metadata: dict = None,
    ) -> BusMessage:
        """发送团队消息"""
        message = BusMessage(
            channel_type=ChannelType.TEAM,
            channel_id=team_id,
            from_agent=from_agent,
            subject=subject,
            content=content,
            metadata=metadata or {},
        )
        
        await self._deliver_message(message)
        return message
    
    async def broadcast(
        self,
        from_agent: str,
        content: str,
        subject: str = "",
        message_type: str = "announcement",
        metadata: dict = None,
    ) -> BusMessage:
        """广播消息"""
        message = BusMessage(
            channel_type=ChannelType.BROADCAST,
            channel_id="all",
            from_agent=from_agent,
            subject=subject,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        
        await self._deliver_message(message)
        return message
    
    async def send_system_message(
        self,
        to_agent: str,
        content: str,
        subject: str = "系统通知",
        metadata: dict = None,
    ) -> BusMessage:
        """发送系统消息"""
        message = BusMessage(
            channel_type=ChannelType.SYSTEM,
            channel_id=to_agent,
            from_agent="system",
            to_agent=to_agent,
            subject=subject,
            content=content,
            message_type="system",
            metadata=metadata or {},
            priority=2,  # 系统消息高优先级
        )
        
        await self._deliver_message(message)
        return message
    
    # ============================================
    # 会议室
    # ============================================
    
    async def create_meeting_room(
        self,
        meeting_id: str,
        title: str,
        host: str,
        participants: list[str],
        metadata: dict = None,
    ) -> dict:
        """创建会议室"""
        room = {
            "meeting_id": meeting_id,
            "title": title,
            "host": host,
            "participants": participants,
            "messages": [],
            "artifacts": [],
            "started_at": datetime.utcnow().isoformat(),
            "ended_at": None,
            "metadata": metadata or {},
        }
        
        self._active_meetings[meeting_id] = room
        
        # 通知参与者
        for agent_id in participants:
            await self.send_system_message(
                to_agent=agent_id,
                content=f"会议「{title}」已开始",
                subject="会议邀请",
                metadata={"meeting_id": meeting_id},
            )
        
        logger.info(
            "会议室创建",
            meeting_id=meeting_id,
            title=title,
            participants=participants,
        )
        
        return room
    
    async def send_to_meeting(
        self,
        meeting_id: str,
        from_agent: str,
        content: str,
        message_type: str = "discussion",
        metadata: dict = None,
    ) -> Optional[BusMessage]:
        """发送会议消息"""
        if meeting_id not in self._active_meetings:
            logger.warning(f"会议 {meeting_id} 不存在或已结束")
            return None
        
        message = BusMessage(
            channel_type=ChannelType.MEETING,
            channel_id=meeting_id,
            from_agent=from_agent,
            subject=self._active_meetings[meeting_id]["title"],
            content=content,
            message_type=message_type,
            metadata=metadata or {},
        )
        
        # 记录到会议消息列表
        self._active_meetings[meeting_id]["messages"].append({
            "id": message.id,
            "from_agent": from_agent,
            "content": content,
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        await self._deliver_message(message)
        return message
    
    async def add_meeting_artifact(
        self,
        meeting_id: str,
        artifact_type: str,
        data: Any,
        title: str = "",
    ) -> bool:
        """添加会议产物（图表、表格等）"""
        if meeting_id not in self._active_meetings:
            return False
        
        artifact = {
            "id": str(uuid4()),
            "type": artifact_type,
            "title": title,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self._active_meetings[meeting_id]["artifacts"].append(artifact)
        return True
    
    async def end_meeting(self, meeting_id: str) -> Optional[dict]:
        """结束会议"""
        if meeting_id not in self._active_meetings:
            return None
        
        room = self._active_meetings[meeting_id]
        room["ended_at"] = datetime.utcnow().isoformat()
        
        # 通知参与者
        for agent_id in room["participants"]:
            await self.send_system_message(
                to_agent=agent_id,
                content=f"会议「{room['title']}」已结束",
                subject="会议结束",
                metadata={"meeting_id": meeting_id},
            )
        
        # 移出活跃会议
        del self._active_meetings[meeting_id]
        
        logger.info(
            "会议结束",
            meeting_id=meeting_id,
            message_count=len(room["messages"]),
            artifact_count=len(room["artifacts"]),
        )
        
        return room
    
    # ============================================
    # 订阅管理
    # ============================================
    
    def subscribe(
        self,
        subscriber_id: str,
        channel_type: ChannelType,
        channel_id: str = "*",
        callback: Callable = None,
        filter_func: Callable = None,
    ) -> str:
        """订阅频道
        
        Args:
            subscriber_id: 订阅者 ID
            channel_type: 频道类型
            channel_id: 频道 ID，"*" 表示订阅该类型所有频道
            callback: 消息回调函数
            filter_func: 过滤函数
            
        Returns:
            订阅 ID
        """
        subscription = Subscription(
            subscriber_id=subscriber_id,
            channel_type=channel_type,
            channel_id=channel_id,
            callback=callback,
            filter_func=filter_func,
        )
        
        self._subscriptions.append(subscription)
        
        logger.info(
            "订阅频道",
            subscriber=subscriber_id,
            channel_type=channel_type.value,
            channel_id=channel_id,
        )
        
        return f"{subscriber_id}:{channel_type.value}:{channel_id}"
    
    def unsubscribe(self, subscriber_id: str, channel_type: ChannelType = None):
        """取消订阅"""
        self._subscriptions = [
            s for s in self._subscriptions
            if not (s.subscriber_id == subscriber_id and 
                   (channel_type is None or s.channel_type == channel_type))
        ]
    
    # ============================================
    # 消息接收
    # ============================================
    
    async def get_messages(
        self,
        agent_id: str,
        timeout: float = 0.1,
        max_messages: int = 10,
    ) -> list[BusMessage]:
        """获取 Agent 的待处理消息
        
        Args:
            agent_id: Agent ID
            timeout: 等待超时（秒）
            max_messages: 最大消息数
            
        Returns:
            消息列表
        """
        messages = []
        queue = self._queues[agent_id]
        
        try:
            while len(messages) < max_messages:
                message = await asyncio.wait_for(
                    queue.get(),
                    timeout=timeout
                )
                messages.append(message)
        except asyncio.TimeoutError:
            pass
        
        return messages
    
    async def peek_messages(self, agent_id: str) -> int:
        """查看消息队列大小"""
        return self._queues[agent_id].qsize()
    
    # ============================================
    # 内部方法
    # ============================================
    
    async def _deliver_message(self, message: BusMessage):
        """投递消息"""
        self._stats["messages_sent"] += 1
        
        # 记录历史
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]
        
        # 根据频道类型投递
        if message.channel_type == ChannelType.DIRECT:
            await self._deliver_direct(message)
        elif message.channel_type == ChannelType.BROADCAST:
            await self._deliver_broadcast(message)
        elif message.channel_type in (ChannelType.DEPARTMENT, ChannelType.TEAM):
            await self._deliver_to_subscribers(message)
        elif message.channel_type == ChannelType.MEETING:
            await self._deliver_to_meeting(message)
        elif message.channel_type == ChannelType.SYSTEM:
            await self._deliver_direct(message)
        
        message.delivered_at = datetime.utcnow()
        self._stats["messages_delivered"] += 1
        
        logger.debug(
            "消息已投递",
            message_id=message.id,
            channel_type=message.channel_type.value,
            from_agent=message.from_agent,
        )
    
    async def _deliver_direct(self, message: BusMessage):
        """投递点对点消息"""
        if message.to_agent:
            await self._queues[message.to_agent].put(message)
    
    async def _deliver_broadcast(self, message: BusMessage):
        """投递广播消息"""
        for subscriber_id in self._queues.keys():
            if subscriber_id != message.from_agent:
                await self._queues[subscriber_id].put(message)
        
        # 也投递给订阅者
        for sub in self._subscriptions:
            if sub.channel_type == ChannelType.BROADCAST:
                if sub.filter_func is None or sub.filter_func(message):
                    await self._queues[sub.subscriber_id].put(message)
    
    async def _deliver_to_subscribers(self, message: BusMessage):
        """投递给订阅者"""
        for sub in self._subscriptions:
            if (sub.channel_type == message.channel_type and 
                (sub.channel_id == "*" or sub.channel_id == message.channel_id)):
                if sub.filter_func is None or sub.filter_func(message):
                    await self._queues[sub.subscriber_id].put(message)
                    if sub.callback:
                        try:
                            await sub.callback(message)
                        except Exception as e:
                            logger.error(f"订阅回调失败: {e}")
    
    async def _deliver_to_meeting(self, message: BusMessage):
        """投递会议消息"""
        meeting_id = message.channel_id
        if meeting_id in self._active_meetings:
            for agent_id in self._active_meetings[meeting_id]["participants"]:
                if agent_id != message.from_agent:
                    await self._queues[agent_id].put(message)
    
    # ============================================
    # 查询和统计
    # ============================================
    
    def get_message_history(
        self,
        channel_type: ChannelType = None,
        from_agent: str = None,
        to_agent: str = None,
        limit: int = 100,
    ) -> list[BusMessage]:
        """获取消息历史"""
        messages = self._message_history
        
        if channel_type:
            messages = [m for m in messages if m.channel_type == channel_type]
        if from_agent:
            messages = [m for m in messages if m.from_agent == from_agent]
        if to_agent:
            messages = [m for m in messages if m.to_agent == to_agent]
        
        return messages[-limit:]
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            "active_queues": len(self._queues),
            "active_meetings": len(self._active_meetings),
            "subscriptions": len(self._subscriptions),
            "history_size": len(self._message_history),
        }
    
    def get_active_meetings(self) -> list[dict]:
        """获取活跃会议列表"""
        return [
            {
                "meeting_id": m["meeting_id"],
                "title": m["title"],
                "host": m["host"],
                "participants": m["participants"],
                "message_count": len(m["messages"]),
                "started_at": m["started_at"],
            }
            for m in self._active_meetings.values()
        ]


# 全局单例
_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """获取消息总线单例"""
    global _message_bus
    if _message_bus is None:
        import os
        redis_url = os.getenv("REDIS_URL")
        _message_bus = MessageBus(redis_url=redis_url)
    return _message_bus
