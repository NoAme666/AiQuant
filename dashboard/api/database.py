"""
AI Quant Company - 数据库连接模块

提供异步数据库连接池和常用查询函数
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import asyncpg
from dotenv import load_dotenv
import structlog

load_dotenv()
logger = structlog.get_logger()

# 全局连接池
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """获取数据库连接池"""
    global _pool
    
    if _pool is None:
        db_url = os.getenv('DATABASE_URL', '')
        if not db_url:
            raise ValueError("DATABASE_URL not set")
        
        # 解析 URL
        parts = db_url.replace('postgresql+asyncpg://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        host_port = host_db[0].split(':')
        
        _pool = await asyncpg.create_pool(
            user=user_pass[0],
            password=user_pass[1],
            host=host_port[0],
            port=int(host_port[1]),
            database=host_db[1],
            min_size=2,
            max_size=10,
            command_timeout=30
        )
        logger.info("数据库连接池创建成功")
    
    return _pool


async def close_pool():
    """关闭连接池"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("数据库连接池已关闭")


@asynccontextmanager
async def get_connection():
    """获取数据库连接的上下文管理器"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


# ============================================
# Agent 查询
# ============================================

async def get_all_agents() -> List[Dict[str, Any]]:
    """获取所有 Agent"""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT 
                a.id, a.name, a.name_en, a.department, a.is_lead, 
                a.capability_tier, a.team, a.status,
                COALESCE(rs.overall_score, 0.5) as reputation_score,
                COALESCE(rs.grade, 'average') as reputation_grade
            FROM agents a
            LEFT JOIN LATERAL (
                SELECT overall_score, grade 
                FROM reputation_scores 
                WHERE agent_id = a.id 
                ORDER BY calculated_at DESC 
                LIMIT 1
            ) rs ON true
            ORDER BY a.department, a.is_lead DESC, a.name
        """)
        return [dict(row) for row in rows]


async def get_agent_by_id(agent_id: str) -> Optional[Dict[str, Any]]:
    """获取单个 Agent"""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT 
                a.*,
                COALESCE(rs.overall_score, 0.5) as reputation_score,
                COALESCE(rs.grade, 'average') as reputation_grade
            FROM agents a
            LEFT JOIN LATERAL (
                SELECT overall_score, grade 
                FROM reputation_scores 
                WHERE agent_id = a.id 
                ORDER BY calculated_at DESC 
                LIMIT 1
            ) rs ON true
            WHERE a.id = $1
        """, agent_id)
        return dict(row) if row else None


async def get_agents_by_department(department: str) -> List[Dict[str, Any]]:
    """按部门获取 Agent"""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT id, name, name_en, is_lead, capability_tier, status
            FROM agents
            WHERE department = $1
            ORDER BY is_lead DESC, name
        """, department)
        return [dict(row) for row in rows]


# ============================================
# 研究周期查询
# ============================================

async def get_research_cycles(
    state: Optional[str] = None,
    team: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """获取研究周期列表"""
    async with get_connection() as conn:
        query = """
            SELECT 
                rc.id, rc.name, rc.description, rc.current_state,
                rc.proposer, rc.team, rc.created_at, rc.updated_at,
                a.name as proposer_name
            FROM research_cycles rc
            LEFT JOIN agents a ON rc.proposer = a.id
            WHERE 1=1
        """
        params = []
        param_idx = 1
        
        if state:
            query += f" AND rc.current_state = ${param_idx}::research_cycle_state"
            params.append(state)
            param_idx += 1
        
        if team:
            query += f" AND rc.team = ${param_idx}"
            params.append(team)
            param_idx += 1
        
        query += f" ORDER BY rc.updated_at DESC LIMIT ${param_idx}"
        params.append(limit)
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def get_cycle_by_id(cycle_id: str) -> Optional[Dict[str, Any]]:
    """获取单个研究周期"""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT rc.*, a.name as proposer_name
            FROM research_cycles rc
            LEFT JOIN agents a ON rc.proposer = a.id
            WHERE rc.id = $1
        """, cycle_id)
        return dict(row) if row else None


# ============================================
# 事件查询
# ============================================

async def get_recent_events(limit: int = 20) -> List[Dict[str, Any]]:
    """获取最近事件"""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT 
                e.id, e.event_type, e.actor, e.action, e.details, e.created_at,
                a.name as actor_name
            FROM events e
            LEFT JOIN agents a ON e.actor = a.id
            ORDER BY e.created_at DESC
            LIMIT $1
        """, limit)
        return [dict(row) for row in rows]


async def create_event(
    event_type: str,
    action: str,
    actor: Optional[str] = None,
    details: Optional[Dict] = None
) -> str:
    """创建事件"""
    async with get_connection() as conn:
        event_id = await conn.fetchval("""
            INSERT INTO events (event_type, actor, action, details)
            VALUES ($1, $2, $3, $4::jsonb)
            RETURNING id
        """, event_type, actor, action, json.dumps(details or {}))
        return str(event_id)


# ============================================
# 审批查询
# ============================================

async def get_pending_approvals() -> List[Dict[str, Any]]:
    """获取待审批项目"""
    async with get_connection() as conn:
        # 获取待审批会议
        meetings = await conn.fetch("""
            SELECT 
                mr.id, mr.title, mr.requester, mr.status, mr.risk_level, mr.created_at,
                a.name as requester_name
            FROM meeting_requests mr
            LEFT JOIN agents a ON mr.requester = a.id
            WHERE mr.status IN ('PENDING_APPROVAL', 'DRAFT')
            ORDER BY mr.created_at DESC
        """)
        
        approvals = []
        for m in meetings:
            approvals.append({
                "id": str(m["id"]),
                "type": "meeting",
                "title": m["title"],
                "requester": m["requester"],
                "requester_name": m["requester_name"],
                "urgency": "high" if m["risk_level"] == "H" else "normal",
                "status": m["status"],
                "created_at": m["created_at"].isoformat() if m["created_at"] else None
            })
        
        return approvals


# ============================================
# 统计查询
# ============================================

async def get_lobby_stats() -> Dict[str, Any]:
    """获取 Lobby 统计数据"""
    async with get_connection() as conn:
        # 活跃研究周期
        active_cycles = await conn.fetchval("""
            SELECT COUNT(*) FROM research_cycles 
            WHERE current_state NOT IN ('ARCHIVE')
        """)
        
        # 待审批数量
        pending_approvals = await conn.fetchval("""
            SELECT COUNT(*) FROM meeting_requests 
            WHERE status IN ('PENDING_APPROVAL', 'DRAFT')
        """)
        
        # Agent 总数
        total_agents = await conn.fetchval("SELECT COUNT(*) FROM agents")
        
        # 平均声誉
        avg_reputation = await conn.fetchval("""
            SELECT AVG(overall_score) FROM (
                SELECT DISTINCT ON (agent_id) overall_score
                FROM reputation_scores
                ORDER BY agent_id, calculated_at DESC
            ) latest_scores
        """) or 0.5
        
        # 预算使用率
        budget_stats = await conn.fetchrow("""
            SELECT 
                SUM(current_period_points) as total,
                SUM(points_spent) as spent
            FROM budget_accounts
        """)
        budget_utilization = 0.0
        if budget_stats and budget_stats["total"]:
            budget_utilization = budget_stats["spent"] / budget_stats["total"]
        
        return {
            "active_cycles": active_cycles or 0,
            "pending_approvals": pending_approvals or 0,
            "total_experiments": 0,  # TODO: 从 experiments 表获取
            "total_agents": total_agents or 0,
            "budget_utilization": round(budget_utilization, 2),
            "avg_reputation": round(float(avg_reputation), 2)
        }


# ============================================
# 组织架构查询
# ============================================

async def get_org_chart() -> List[Dict[str, Any]]:
    """获取组织架构"""
    async with get_connection() as conn:
        # 获取所有部门
        agents = await conn.fetch("""
            SELECT 
                a.id, a.name, a.name_en, a.department, a.is_lead, 
                a.capability_tier, a.status,
                COALESCE(rs.overall_score, 0.5) as reputation_score,
                COALESCE(ba.current_period_points - ba.points_spent, 0) as budget_remaining
            FROM agents a
            LEFT JOIN LATERAL (
                SELECT overall_score FROM reputation_scores 
                WHERE agent_id = a.id ORDER BY calculated_at DESC LIMIT 1
            ) rs ON true
            LEFT JOIN budget_accounts ba ON ba.id = a.team OR ba.id = a.id
            ORDER BY a.department, a.is_lead DESC, a.name
        """)
        
        # 按部门分组
        departments = {}
        dept_names = {
            "board_office": ("董事会办公室", "Board Office"),
            "investment_committee": ("投资委员会", "Investment Committee"),
            "research_guild": ("研究部", "Research Guild"),
            "data_guild": ("数据部", "Data Guild"),
            "backtest_guild": ("回测部", "Backtest Guild"),
            "risk_guild": ("风控部", "Risk & Skeptic Guild"),
            "meta_governance": ("治理与组织进化部", "Meta-Governance"),
            "trading_guild": ("交易部", "Trading Guild"),
            "intelligence_guild": ("市场情报部", "Intelligence Guild"),
        }
        
        for agent in agents:
            dept = agent["department"]
            if dept not in departments:
                name, name_en = dept_names.get(dept, (dept, dept))
                departments[dept] = {
                    "id": dept,
                    "name": name,
                    "name_en": name_en,
                    "agents": []
                }
            
            departments[dept]["agents"].append({
                "id": agent["id"],
                "name": agent["name"],
                "name_en": agent["name_en"],
                "department": agent["department"],
                "is_lead": agent["is_lead"],
                "status": str(agent["status"]).lower() if agent["status"] else "active",
                "budget_remaining": agent["budget_remaining"] or 0,
                "reputation_score": float(agent["reputation_score"]) if agent["reputation_score"] else 0.5
            })
        
        return list(departments.values())
