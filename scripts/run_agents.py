#!/usr/bin/env python3
# AI Quant Company - 启动 Agent 系统
"""
启动脚本 - 让 Agent 们"活"起来

用法:
    python scripts/run_agents.py              # 使用真实 LLM
    python scripts/run_agents.py --mock       # 使用 Mock LLM（测试）
    python scripts/run_agents.py --demo       # 演示模式（简化输出）
"""

import asyncio
import os
import sys

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import structlog
from agents.runtime import AgentRuntime, init_agent_runtime, RuntimeAgent
from agents.research.researcher import ResearcherAgent
from agents.intention import get_topic_manager, get_intention_detector, Topic, TopicType
from orchestrator.scheduler import AgentScheduler
from orchestrator.message_bus import get_message_bus

logger = structlog.get_logger()


class EnhancedAgentRuntime(AgentRuntime):
    """增强版 Agent Runtime
    
    使用具体的 Agent 实现替代通用 RuntimeAgent
    """
    
    async def start(self):
        """启动运行时"""
        await super().start()
        
        # 替换研究员为具体实现
        researcher_ids = [
            "alpha_a_researcher_1",
            "alpha_a_researcher_2", 
            "alpha_b_researcher_1",
            "alpha_b_researcher_2",
        ]
        
        for agent_id in researcher_ids:
            if agent_id in self._agents:
                old_agent = self._agents[agent_id]
                # 创建新的研究员 Agent
                new_agent = ResearcherAgent(
                    config=old_agent.config,
                    llm_client=self._llm_client,
                    message_bus=self._message_bus,
                )
                self._agents[agent_id] = new_agent
                logger.info(f"升级 Agent: {agent_id} -> ResearcherAgent")


async def run_demo():
    """演示模式 - 展示 Agent 自动研究"""
    print("\n" + "="*60)
    print("🏢 AI Quant Company - Agent 系统演示")
    print("="*60 + "\n")
    
    # 初始化
    runtime = EnhancedAgentRuntime(use_mock_llm=True)
    await runtime.start()
    
    print(f"✅ 已加载 {len(runtime.list_agents())} 个 Agent\n")
    
    # 获取一个研究员
    researcher = runtime.get_agent("alpha_a_researcher_1")
    if not researcher:
        print("❌ 找不到研究员 Agent")
        return
    
    print(f"🔬 激活研究员: {researcher.config.name}")
    print(f"   部门: {researcher.config.department}")
    print(f"   汇报给: {researcher.config.reports_to}")
    print()
    
    # 模拟研究循环
    print("📊 开始研究循环...")
    print("-" * 40)
    
    for i in range(3):
        print(f"\n⏰ 第 {i+1} 轮迭代:")
        
        # 运行一次
        stats = await researcher.run_once()
        
        print(f"   消息处理: {stats['messages_processed']}")
        print(f"   任务完成: {stats['tasks_completed']}")
        
        # 获取状态
        status = researcher.get_status()
        print(f"   待处理任务: {status['pending_tasks']}")
        print(f"   当前任务: {status['running_task'] or '无'}")
        
        # 检查活动日志
        activities = researcher.get_activity_log(limit=3)
        if activities:
            print(f"   最近活动:")
            for act in activities:
                print(f"      - {act['type']}: {act.get('details', {})}")
        
        await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("演示结束")
    print("="*60)
    
    await runtime.stop()


async def run_full_system(use_mock: bool = False):
    """运行完整系统"""
    print("\n" + "="*60)
    print("🏢 AI Quant Company - 启动完整 Agent 系统")
    print("="*60 + "\n")
    
    # 检查环境变量
    if not use_mock:
        api_key = os.getenv("ANTIGRAVITY_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  未检测到 API Key，切换到 Mock 模式")
            use_mock = True
    
    print(f"🔧 LLM 模式: {'Mock (测试)' if use_mock else '真实 LLM'}")
    print()
    
    # 初始化调度器
    scheduler = AgentScheduler(
        use_mock_llm=use_mock,
        agent_interval=2.0,      # Agent 每 2 秒迭代一次
        scheduler_interval=10.0,  # 调度器每 10 秒检查一次
    )
    
    print("📋 正在初始化...")
    await scheduler.start()
    
    print(f"✅ 系统启动成功!")
    print(f"   活跃 Agent 数: {len(scheduler._runtime.list_agents())}")
    print()
    
    print("💡 系统现在运行中，Agent 会自动:")
    print("   - 寻找研究机会")
    print("   - 分析市场数据")
    print("   - 相互沟通协作")
    print("   - 提出策略建议")
    print()
    print("按 Ctrl+C 停止系统")
    print("-" * 40)
    
    try:
        # 持续运行
        iteration = 0
        while True:
            iteration += 1
            
            # 每 30 秒打印一次状态
            if iteration % 15 == 0:
                stats = scheduler.get_stats()
                print(f"\n📊 系统状态 (运行 {iteration * 2} 秒)")
                print(f"   总迭代: {stats['total_iterations']}")
                print(f"   Agent 运行次数: {stats['total_agent_runs']}")
                print(f"   消息数: {stats['total_messages']}")
                print(f"   错误数: {stats['errors']}")
                
                # 打印活跃 Agent 状态
                statuses = scheduler._runtime.get_agent_statuses()
                active_count = sum(1 for s in statuses if s['pending_tasks'] > 0)
                print(f"   有任务的 Agent: {active_count}/{len(statuses)}")
            
            await asyncio.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  收到停止信号...")
    finally:
        await scheduler.stop()
        print("✅ 系统已停止")


async def test_intention_detection():
    """测试意愿检测"""
    print("\n" + "="*60)
    print("🧪 测试意愿检测系统")
    print("="*60 + "\n")
    
    detector = get_intention_detector()
    
    test_cases = [
        "我发现市场波动率异常升高，可能存在风险，需要讨论应对方案。",
        "我有一个新的策略想法：基于动量和均值回归的混合策略，希望团队讨论可行性。",
        "我们的预算快用完了，需要申请额外的计算资源来完成回测。",
        "当前的审批流程效率太低，建议优化。",
        "紧急！检测到策略出现异常亏损，需要立即讨论是否止损。",
        "今天天气不错。",  # 不应触发
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"测试 {i}: {text[:50]}...")
        topic = detector.detect_intention(
            agent_id="test_agent",
            department="research_guild",
            text=text,
        )
        
        if topic:
            print(f"   ✅ 检测到意愿:")
            print(f"      类型: {topic.topic_type.value}")
            print(f"      标题: {topic.title}")
            print(f"      紧急: {topic.urgency.value}")
        else:
            print(f"   ❌ 未检测到意愿")
        print()
    
    print("测试完成!")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Quant Company Agent 系统")
    parser.add_argument("--mock", action="store_true", help="使用 Mock LLM")
    parser.add_argument("--demo", action="store_true", help="演示模式")
    parser.add_argument("--test-intention", action="store_true", help="测试意愿检测")
    
    args = parser.parse_args()
    
    if args.test_intention:
        asyncio.run(test_intention_detection())
    elif args.demo:
        asyncio.run(run_demo())
    else:
        asyncio.run(run_full_system(use_mock=args.mock))


if __name__ == "__main__":
    main()
