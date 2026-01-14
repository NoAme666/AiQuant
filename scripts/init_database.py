#!/usr/bin/env python3
"""
AI Quant Company - 数据库初始化脚本

功能：
1. 从 agents.yaml 导入所有 Agent
2. 创建示例研究周期
3. 创建示例事件和消息
4. 初始化预算账户
"""

import asyncio
import os
import sys
import yaml
from datetime import datetime, timedelta
from uuid import uuid4

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def get_connection():
    """获取数据库连接"""
    import asyncpg
    db_url = os.getenv('DATABASE_URL', '')
    parts = db_url.replace('postgresql+asyncpg://', '').split('@')
    user_pass = parts[0].split(':')
    host_db = parts[1].split('/')
    host_port = host_db[0].split(':')
    
    return await asyncpg.connect(
        user=user_pass[0],
        password=user_pass[1],
        host=host_port[0],
        port=int(host_port[1]),
        database=host_db[1],
        timeout=10
    )


async def init_agents(conn):
    """从 agents.yaml 导入所有 Agent"""
    print("\n📥 导入 Agents...")
    
    with open('configs/agents.yaml', 'r') as f:
        data = yaml.safe_load(f)
    
    agents = data.get('agents', {})
    count = 0
    
    for agent_id, agent in agents.items():
        try:
            await conn.execute("""
                INSERT INTO agents (id, name, name_en, department, is_lead, capability_tier, team, reports_to, status, veto_power, can_force_retest)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'ACTIVE', $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    name_en = EXCLUDED.name_en,
                    department = EXCLUDED.department,
                    is_lead = EXCLUDED.is_lead,
                    capability_tier = EXCLUDED.capability_tier,
                    updated_at = NOW()
            """,
                agent_id,
                agent.get('name', agent_id),
                agent.get('name_en', agent_id),
                agent.get('department', 'unknown'),
                agent.get('is_lead', False),
                agent.get('capability_tier', 'reasoning'),
                agent.get('team'),
                agent.get('reports_to'),
                agent.get('veto_power', False),
                agent.get('can_force_retest', False)
            )
            count += 1
        except Exception as e:
            print(f"  ❌ {agent_id}: {e}")
    
    print(f"  ✅ 导入 {count} 个 Agent")
    return count


async def init_research_cycles(conn):
    """创建示例研究周期"""
    print("\n📥 创建研究周期...")
    
    cycles = [
        {
            "name": "BTC 动量策略 v1",
            "description": "基于价格动量的 BTC 趋势跟踪策略",
            "state": "RISK_SKEPTIC_GATE",
            "proposer": "alpha_a_lead",
            "team": "alpha_a"
        },
        {
            "name": "ETH 均值回归策略",
            "description": "ETH/USDT 基于布林带的均值回归策略",
            "state": "BACKTEST_GATE",
            "proposer": "alpha_b_lead",
            "team": "alpha_b"
        },
        {
            "name": "跨市场套利策略",
            "description": "BTC 现货-期货基差套利",
            "state": "DATA_GATE",
            "proposer": "alpha_a_researcher_1",
            "team": "alpha_a"
        },
        {
            "name": "市场情绪策略",
            "description": "基于 Fear & Greed 指数的择时策略",
            "state": "IDEA_INTAKE",
            "proposer": "sentiment_analyst",
            "team": "alpha_b"
        },
    ]
    
    count = 0
    for cycle in cycles:
        try:
            await conn.execute("""
                INSERT INTO research_cycles (id, name, description, current_state, proposer, team, created_at, updated_at)
                VALUES ($1, $2, $3, $4::research_cycle_state, $5, $6, $7, $8)
            """,
                uuid4(),
                cycle["name"],
                cycle["description"],
                cycle["state"],
                cycle["proposer"],
                cycle["team"],
                datetime.utcnow() - timedelta(days=count * 2),
                datetime.utcnow()
            )
            count += 1
            print(f"  ✅ {cycle['name']} ({cycle['state']})")
        except Exception as e:
            print(f"  ❌ {cycle['name']}: {e}")
    
    return count


async def init_events(conn):
    """创建示例事件"""
    print("\n📥 创建事件记录...")
    
    import json
    
    events = [
        {"type": "research.cycle_created", "actor": "alpha_a_lead", "action": "创建研究周期", "target": "BTC 动量策略 v1"},
        {"type": "gate.passed", "actor": "data_quality_auditor", "action": "通过数据闸门", "target": "BTC 动量策略 v1"},
        {"type": "gate.passed", "actor": "backtest_lead", "action": "通过回测闸门", "target": "BTC 动量策略 v1"},
        {"type": "gate.review", "actor": "cro", "action": "开始风控审核", "target": "BTC 动量策略 v1"},
        {"type": "research.cycle_created", "actor": "alpha_b_lead", "action": "创建研究周期", "target": "ETH 均值回归策略"},
        {"type": "gate.passed", "actor": "data_quality_auditor", "action": "通过数据闸门", "target": "ETH 均值回归策略"},
        {"type": "meeting.requested", "actor": "alpha_a_lead", "action": "申请策略评审会议", "target": None},
        {"type": "approval.pending", "actor": "head_trader", "action": "提交交易计划审批", "target": "BTC 做多计划"},
        {"type": "intelligence.alert", "actor": "news_analyst", "action": "发现重要新闻", "target": "美联储利率决议"},
        {"type": "system.startup", "actor": None, "action": "系统启动", "target": None},
    ]
    
    count = 0
    for i, event in enumerate(events):
        try:
            details = json.dumps({"target": event["target"]} if event["target"] else {})
            await conn.execute("""
                INSERT INTO events (id, event_type, actor, action, details, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            """,
                uuid4(),
                event["type"],
                event["actor"],
                event["action"],
                details,
                datetime.utcnow() - timedelta(minutes=(len(events) - i) * 5)
            )
            count += 1
        except Exception as e:
            print(f"  ❌ {event['action']}: {e}")
    
    print(f"  ✅ 创建 {count} 条事件")
    return count


async def init_budget_accounts(conn):
    """初始化预算账户"""
    print("\n📥 初始化预算账户...")
    
    teams = [
        {"id": "alpha_a", "type": "team", "points": 1000},
        {"id": "alpha_b", "type": "team", "points": 1000},
        {"id": "data_guild", "type": "team", "points": 500},
        {"id": "backtest_guild", "type": "team", "points": 800},
    ]
    
    count = 0
    for team in teams:
        try:
            await conn.execute("""
                INSERT INTO budget_accounts (id, account_type, base_weekly_points, current_period_start, current_period_points, points_spent)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    current_period_points = EXCLUDED.current_period_points,
                    updated_at = NOW()
            """,
                team["id"],
                team["type"],
                team["points"],
                datetime.utcnow().date(),
                team["points"],
                int(team["points"] * 0.3)  # 假设已消耗 30%
            )
            count += 1
        except Exception as e:
            print(f"  ❌ {team['id']}: {e}")
    
    print(f"  ✅ 创建 {count} 个预算账户")
    return count


async def init_approvals(conn):
    """创建待审批项目"""
    print("\n📥 创建待审批项目...")
    
    # 创建会议申请
    meetings = [
        {
            "title": "BTC 动量策略投委会评审",
            "goal": "评审 BTC 动量策略是否可以进入 Board Pack 阶段",
            "requester": "alpha_a_lead",
            "participants": ["cio", "cro", "head_of_research", "pm"],
            "risk_level": "M",
            "status": "PENDING_APPROVAL"
        },
        {
            "title": "Q1 研究方向讨论",
            "goal": "确定 Q1 研究重点和资源分配",
            "requester": "head_of_research",
            "participants": ["cio", "alpha_a_lead", "alpha_b_lead"],
            "risk_level": "L",
            "status": "DRAFT"
        }
    ]
    
    import json
    
    for meeting in meetings:
        try:
            agenda = json.dumps(["议程项 1", "议程项 2"])
            await conn.execute("""
                INSERT INTO meeting_requests (id, title, goal, agenda, requester, participants, risk_level, status, created_at)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7::risk_level, $8::meeting_status, $9)
            """,
                uuid4(),
                meeting["title"],
                meeting["goal"],
                agenda,
                meeting["requester"],
                meeting["participants"],
                meeting["risk_level"],
                meeting["status"],
                datetime.utcnow() - timedelta(hours=2)
            )
            print(f"  ✅ 会议: {meeting['title']}")
        except Exception as e:
            print(f"  ❌ {meeting['title']}: {e}")
    
    return len(meetings)


async def init_reputation(conn):
    """初始化声誉评分"""
    print("\n📥 初始化声誉评分...")
    
    # 获取所有 Agent
    agents = await conn.fetch("SELECT id, department FROM agents")
    
    count = 0
    import random
    
    for agent in agents:
        try:
            score = round(random.uniform(0.6, 0.95), 4)
            grade = "excellent" if score > 0.85 else "good" if score > 0.7 else "average"
            
            await conn.execute("""
                INSERT INTO reputation_scores (id, agent_id, overall_score, grade, sample_count, period_start, period_end, calculated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                uuid4(),
                agent["id"],
                score,
                grade,
                random.randint(10, 50),
                datetime.utcnow().date() - timedelta(days=30),
                datetime.utcnow().date(),
                datetime.utcnow()
            )
            count += 1
        except Exception as e:
            print(f"  ❌ {agent['id']}: {e}")
    
    print(f"  ✅ 创建 {count} 个声誉评分")
    return count


async def main():
    """主函数"""
    print("=" * 50)
    print("🚀 AI Quant Company 数据库初始化")
    print("=" * 50)
    
    conn = await get_connection()
    print(f"✅ 连接数据库成功")
    
    try:
        # 1. 导入 Agents
        await init_agents(conn)
        
        # 2. 创建研究周期
        await init_research_cycles(conn)
        
        # 3. 创建事件记录
        await init_events(conn)
        
        # 4. 初始化预算账户
        await init_budget_accounts(conn)
        
        # 5. 创建待审批项目
        await init_approvals(conn)
        
        # 6. 初始化声誉评分
        await init_reputation(conn)
        
        print("\n" + "=" * 50)
        print("✅ 数据库初始化完成!")
        print("=" * 50)
        
        # 统计
        for table in ['agents', 'research_cycles', 'events', 'budget_accounts', 'meeting_requests', 'reputation_scores']:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"  📊 {table}: {count} 条")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
