# AI Quant Company - 研究员 Agent 实现
"""
研究员 Agent - 具有主动研究能力

能力：
- 主动寻找研究机会
- 分析市场数据
- 提出策略假设
- 运行回测实验
- 与团队讨论
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Optional

import structlog

from agents.base import AgentConfig, TaskResult
from agents.runtime import AgentTask, RuntimeAgent, TaskPriority
from orchestrator.message_bus import MessageBus

logger = structlog.get_logger()


class ResearcherAgent(RuntimeAgent):
    """研究员 Agent
    
    具有主动研究策略的能力
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm_client=None,
        message_bus: Optional[MessageBus] = None,
    ):
        super().__init__(config, llm_client, message_bus)
        
        # 研究状态
        self._current_research_topic: Optional[str] = None
        self._research_ideas: list[dict] = []
        self._experiments_run: int = 0
        self._last_research_check = datetime.utcnow()
        self._research_cooldown = timedelta(minutes=5)  # 每5分钟检查一次研究机会
        
        # 市场观察
        self._market_observations: list[dict] = []
        
    async def check_for_work(self) -> bool:
        """检查是否有研究工作需要做
        
        这是让 Agent "活"起来的核心方法
        """
        now = datetime.utcnow()
        
        # 冷却时间未到，跳过
        if now - self._last_research_check < self._research_cooldown:
            return False
        
        self._last_research_check = now
        added_task = False
        
        # 1. 如果没有当前研究主题，寻找新的研究机会
        if not self._current_research_topic:
            await self.add_task(
                task_type="find_research_opportunity",
                payload={"type": "find_research_opportunity"},
                priority=TaskPriority.NORMAL,
            )
            added_task = True
        
        # 2. 如果有研究想法但还没验证，进行验证
        elif self._research_ideas:
            idea = self._research_ideas[0]
            await self.add_task(
                task_type="validate_idea",
                payload={
                    "type": "validate_idea",
                    "idea": idea,
                },
                priority=TaskPriority.NORMAL,
            )
            added_task = True
        
        # 3. 定期观察市场
        elif random.random() < 0.3:  # 30% 概率观察市场
            await self.add_task(
                task_type="observe_market",
                payload={"type": "observe_market"},
                priority=TaskPriority.LOW,
            )
            added_task = True
        
        return added_task
    
    async def execute_task(self, task: dict) -> TaskResult:
        """执行研究任务"""
        task_type = task.get("type", "")
        
        if task_type == "find_research_opportunity":
            return await self._find_research_opportunity()
        
        elif task_type == "validate_idea":
            return await self._validate_idea(task.get("idea", {}))
        
        elif task_type == "observe_market":
            return await self._observe_market()
        
        elif task_type == "run_backtest":
            return await self._run_backtest(task)
        
        elif task_type == "propose_strategy":
            return await self._propose_strategy(task)
        
        # 默认使用父类处理
        return await super().execute_task(task)
    
    async def _find_research_opportunity(self) -> TaskResult:
        """寻找研究机会"""
        logger.info(f"[{self.agent_id}] 正在寻找研究机会...")
        
        # 让 LLM 分析并提出研究方向
        prompt = f"""
作为 {self.config.name}，你需要寻找新的研究机会。

你的专长领域：
{chr(10).join(f'- {t}' for t in self.config.persona_traits)}

最近的市场观察：
{json.dumps(self._market_observations[-5:], ensure_ascii=False, indent=2) if self._market_observations else "暂无"}

请思考：
1. 当前市场有什么值得研究的现象？
2. 有没有被忽视的 Alpha 来源？
3. 有什么假设值得验证？

请提出 1-2 个具体的研究方向，包括：
- 研究主题
- 核心假设
- 预期验证方法
- 预期收益来源

输出格式（JSON）：
{{
    "topic": "研究主题",
    "hypothesis": "核心假设",
    "method": "验证方法",
    "expected_alpha": "预期 Alpha 来源",
    "confidence": 0.0-1.0
}}
"""
        
        response = await self.think(prompt)
        
        # 尝试解析 JSON
        try:
            # 简单提取 JSON
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                idea = json.loads(json_match.group())
                self._research_ideas.append(idea)
                self._current_research_topic = idea.get("topic", "未命名研究")
                
                logger.info(
                    f"[{self.agent_id}] 发现研究机会",
                    topic=self._current_research_topic,
                )
                
                # 通知组长
                if self.config.reports_to:
                    await self.message_bus.send_direct(
                        from_agent=self.agent_id,
                        to_agent=self.config.reports_to,
                        content=f"我发现了一个研究机会：{self._current_research_topic}\n\n{response}",
                        subject="研究机会提案",
                    )
                
                return TaskResult(success=True, output=idea)
        except Exception as e:
            logger.warning(f"解析研究想法失败: {e}")
        
        return TaskResult(success=True, output=response)
    
    async def _validate_idea(self, idea: dict) -> TaskResult:
        """验证研究想法"""
        logger.info(f"[{self.agent_id}] 正在验证研究想法: {idea.get('topic', 'unknown')}")
        
        prompt = f"""
请对以下研究想法进行初步验证：

研究主题：{idea.get('topic', '')}
核心假设：{idea.get('hypothesis', '')}
验证方法：{idea.get('method', '')}

请评估：
1. 这个假设是否可证伪？
2. 需要什么数据来验证？
3. 可能的陷阱和风险是什么？
4. 是否值得进一步回测？

如果值得继续，请设计一个简单的回测方案。
"""
        
        response = await self.think(prompt)
        
        # 如果建议继续，添加回测任务
        if "值得" in response or "建议" in response or "可以" in response:
            await self.add_task(
                task_type="run_backtest",
                payload={
                    "type": "run_backtest",
                    "idea": idea,
                    "design": response,
                },
                priority=TaskPriority.HIGH,
            )
        
        # 从待验证列表移除
        if idea in self._research_ideas:
            self._research_ideas.remove(idea)
        
        return TaskResult(success=True, output=response)
    
    async def _observe_market(self) -> TaskResult:
        """观察市场"""
        logger.info(f"[{self.agent_id}] 正在观察市场...")
        
        # 获取市场数据（这里使用工具）
        try:
            from tools.market import get_market_tools
            market_tools = get_market_tools()
            
            # 获取 BTC 行情
            quote = await market_tools.get_quote("BTC/USDT")
            
            observation = {
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": "BTC/USDT",
                "price": quote.get("last", 0) if quote else 0,
                "change_24h": quote.get("change_24h", 0) if quote else 0,
            }
            
            self._market_observations.append(observation)
            
            # 限制观察历史长度
            if len(self._market_observations) > 100:
                self._market_observations = self._market_observations[-100:]
            
            # 让 LLM 分析观察结果
            prompt = f"""
市场观察：
{json.dumps(observation, indent=2)}

最近观察历史：
{json.dumps(self._market_observations[-10:], indent=2)}

请简要分析：
1. 当前市场状态如何？
2. 有没有值得注意的异常？
3. 是否有研究机会？

简洁回答，不超过 100 字。
"""
            
            analysis = await self.think(prompt)
            observation["analysis"] = analysis
            
            return TaskResult(success=True, output=observation)
            
        except Exception as e:
            logger.error(f"市场观察失败: {e}")
            return TaskResult(success=False, error=str(e))
    
    async def _run_backtest(self, task: dict) -> TaskResult:
        """运行回测"""
        idea = task.get("idea", {})
        logger.info(f"[{self.agent_id}] 正在运行回测: {idea.get('topic', 'unknown')}")
        
        # 这里应该调用实际的回测引擎
        # 现在先模拟结果
        
        prompt = f"""
假设你已经运行了以下策略的回测：

策略：{idea.get('topic', '')}
假设：{idea.get('hypothesis', '')}

请生成一个模拟的回测报告，包括：
1. 年化收益率
2. 夏普比率
3. 最大回撤
4. 胜率
5. 主要发现
6. 风险提示

以结构化格式输出。
"""
        
        response = await self.think(prompt)
        
        self._experiments_run += 1
        
        # 如果结果看起来不错，提出策略提案
        if "夏普" in response and ("1.5" in response or "2" in response):
            await self.add_task(
                task_type="propose_strategy",
                payload={
                    "type": "propose_strategy",
                    "idea": idea,
                    "backtest_result": response,
                },
                priority=TaskPriority.HIGH,
            )
        
        # 完成当前研究主题
        self._current_research_topic = None
        
        return TaskResult(success=True, output=response)
    
    async def _propose_strategy(self, task: dict) -> TaskResult:
        """提出策略提案"""
        idea = task.get("idea", {})
        backtest_result = task.get("backtest_result", "")
        
        logger.info(f"[{self.agent_id}] 正在提出策略提案: {idea.get('topic', 'unknown')}")
        
        # 向组长和研究总监汇报
        content = f"""
# 策略提案

## 策略概述
- 主题：{idea.get('topic', '')}
- 假设：{idea.get('hypothesis', '')}
- 预期 Alpha：{idea.get('expected_alpha', '')}

## 回测结果
{backtest_result}

## 建议
请审核此策略是否值得进入下一阶段审批。

提案人：{self.config.name}
"""
        
        # 发送给组长
        if self.config.reports_to:
            await self.message_bus.send_direct(
                from_agent=self.agent_id,
                to_agent=self.config.reports_to,
                content=content,
                subject=f"策略提案: {idea.get('topic', '未命名')}",
            )
        
        # 发送给研究总监
        await self.message_bus.send_direct(
            from_agent=self.agent_id,
            to_agent="head_of_research",
            content=content,
            subject=f"策略提案: {idea.get('topic', '未命名')}",
        )
        
        return TaskResult(success=True, output=content)
    
    async def daily_routine(self):
        """每日例行工作"""
        # 每日总结
        summary = f"""
## 每日研究总结 - {self.config.name}

- 当前研究主题：{self._current_research_topic or '无'}
- 待验证想法数：{len(self._research_ideas)}
- 已运行实验数：{self._experiments_run}
- 市场观察数：{len(self._market_observations)}
"""
        
        # 发送给组长
        if self.config.reports_to:
            await self.message_bus.send_direct(
                from_agent=self.agent_id,
                to_agent=self.config.reports_to,
                content=summary,
                subject="每日研究总结",
            )


class AlphaTeamLead(RuntimeAgent):
    """Alpha 团队组长
    
    负责：
    - 审核团队成员的研究提案
    - 汇总团队意见
    - 向研究总监汇报
    """
    
    def __init__(self, config: AgentConfig, llm_client=None, message_bus=None):
        super().__init__(config, llm_client, message_bus)
        
        self._pending_proposals: list[dict] = []
        self._team_updates: list[dict] = []
    
    async def check_for_work(self) -> bool:
        """检查是否有工作"""
        # 如果有待审核的提案，添加审核任务
        if self._pending_proposals:
            await self.add_task(
                task_type="review_proposal",
                payload={
                    "type": "review_proposal",
                    "proposal": self._pending_proposals[0],
                },
                priority=TaskPriority.HIGH,
            )
            return True
        
        return False
    
    async def execute_task(self, task: dict) -> TaskResult:
        """执行任务"""
        task_type = task.get("type", "")
        
        if task_type == "review_proposal":
            return await self._review_proposal(task.get("proposal", {}))
        
        return await super().execute_task(task)
    
    async def _review_proposal(self, proposal: dict) -> TaskResult:
        """审核提案"""
        prompt = f"""
作为 {self.config.name}，请审核以下策略提案：

{json.dumps(proposal, ensure_ascii=False, indent=2)}

审核要点：
1. 假设是否合理？
2. 方法是否可行？
3. 风险是否可控？
4. 是否值得推进？

请给出审核意见和建议（通过/退回/需要更多信息）。
"""
        
        response = await self.think(prompt)
        
        # 从待审核列表移除
        if proposal in self._pending_proposals:
            self._pending_proposals.remove(proposal)
        
        return TaskResult(success=True, output=response)
