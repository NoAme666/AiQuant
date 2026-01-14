"""
数据管理器 - 管理所有业务数据的持久化存储

提供:
- 交易信号、持仓、交易计划
- 研究周期、Agent交流、引用来源
- 报告列表
- 审批队列
- 会议和对话
- 回测结果
- Agent任务状态
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()

# 数据存储路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _load_json(filename: str, default: Any = None) -> Any:
    """加载 JSON 文件"""
    filepath = DATA_DIR / filename
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载 {filename} 失败: {e}")
    return default if default is not None else {}


def _save_json(filename: str, data: Any) -> bool:
    """保存 JSON 文件"""
    filepath = DATA_DIR / filename
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"保存 {filename} 失败: {e}")
        return False


# ============================================
# 交易信号管理
# ============================================

class SignalManager:
    """交易信号管理"""
    
    FILENAME = "trading_signals.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有信号"""
        data = _load_json(cls.FILENAME, {"signals": []})
        return data.get("signals", [])
    
    @classmethod
    def get_pending(cls) -> List[Dict]:
        """获取待执行信号"""
        return [s for s in cls.get_all() if s.get("status") == "pending"]
    
    @classmethod
    def create(cls, signal: Dict) -> Dict:
        """创建新信号"""
        data = _load_json(cls.FILENAME, {"signals": []})
        signal["id"] = f"SIG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        signal["created_at"] = datetime.now().isoformat()
        signal["status"] = signal.get("status", "pending")
        data["signals"].insert(0, signal)
        # 只保留最近100条
        data["signals"] = data["signals"][:100]
        _save_json(cls.FILENAME, data)
        return signal
    
    @classmethod
    def update_status(cls, signal_id: str, status: str, pnl: float = None) -> Optional[Dict]:
        """更新信号状态"""
        data = _load_json(cls.FILENAME, {"signals": []})
        for s in data["signals"]:
            if s["id"] == signal_id:
                s["status"] = status
                s["updated_at"] = datetime.now().isoformat()
                if pnl is not None:
                    s["pnl"] = pnl
                _save_json(cls.FILENAME, data)
                return s
        return None


# ============================================
# 持仓管理
# ============================================

class PositionManager:
    """持仓管理"""
    
    FILENAME = "positions.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有持仓"""
        data = _load_json(cls.FILENAME, {"positions": []})
        return data.get("positions", [])
    
    @classmethod
    def update(cls, positions: List[Dict]) -> bool:
        """更新持仓列表"""
        data = {"positions": positions, "updated_at": datetime.now().isoformat()}
        return _save_json(cls.FILENAME, data)
    
    @classmethod
    def add(cls, position: Dict) -> Dict:
        """添加持仓"""
        data = _load_json(cls.FILENAME, {"positions": []})
        position["id"] = f"POS-{uuid.uuid4().hex[:8].upper()}"
        position["created_at"] = datetime.now().isoformat()
        data["positions"].append(position)
        _save_json(cls.FILENAME, data)
        return position


# ============================================
# 交易计划管理
# ============================================

class TradingPlanManager:
    """交易计划管理"""
    
    FILENAME = "trading_plans.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有计划"""
        data = _load_json(cls.FILENAME, {"plans": []})
        return data.get("plans", [])
    
    @classmethod
    def get_by_id(cls, plan_id: str) -> Optional[Dict]:
        """根据ID获取计划"""
        for p in cls.get_all():
            if p["id"] == plan_id:
                return p
        return None
    
    @classmethod
    def create(cls, plan: Dict) -> Dict:
        """创建新计划"""
        data = _load_json(cls.FILENAME, {"plans": []})
        plan["id"] = f"TP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        plan["created_at"] = datetime.now().isoformat()
        plan["state"] = plan.get("state", "DRAFT")
        plan["signals"] = []
        plan["realized_pnl"] = 0
        plan["total_trades"] = 0
        data["plans"].insert(0, plan)
        _save_json(cls.FILENAME, data)
        return plan
    
    @classmethod
    def update_state(cls, plan_id: str, state: str) -> Optional[Dict]:
        """更新计划状态"""
        data = _load_json(cls.FILENAME, {"plans": []})
        for p in data["plans"]:
            if p["id"] == plan_id:
                p["state"] = state
                p["updated_at"] = datetime.now().isoformat()
                _save_json(cls.FILENAME, data)
                return p
        return None


# ============================================
# 研究周期管理
# ============================================

class ResearchCycleManager:
    """研究周期管理"""
    
    FILENAME = "research_cycles.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有研究周期"""
        data = _load_json(cls.FILENAME, {"cycles": []})
        return data.get("cycles", [])
    
    @classmethod
    def get_by_id(cls, cycle_id: str) -> Optional[Dict]:
        """根据ID获取周期"""
        for c in cls.get_all():
            if c["id"] == cycle_id:
                return c
        return None
    
    @classmethod
    def create(cls, cycle: Dict) -> Dict:
        """创建新周期"""
        data = _load_json(cls.FILENAME, {"cycles": []})
        cycle["id"] = f"RC-{datetime.now().strftime('%Y')}-{str(len(data['cycles']) + 1).zfill(3)}"
        cycle["created_at"] = datetime.now().isoformat()
        cycle["state"] = cycle.get("state", "IDEA_INTAKE")
        cycle["progress"] = 0
        cycle["discussion"] = []
        cycle["references"] = []
        cycle["team_evaluation"] = None
        data["cycles"].insert(0, cycle)
        _save_json(cls.FILENAME, data)
        return cycle
    
    @classmethod
    def add_discussion(cls, cycle_id: str, message: Dict) -> Optional[Dict]:
        """添加讨论消息"""
        data = _load_json(cls.FILENAME, {"cycles": []})
        for c in data["cycles"]:
            if c["id"] == cycle_id:
                message["timestamp"] = datetime.now().strftime("%H:%M")
                message["created_at"] = datetime.now().isoformat()
                c["discussion"].append(message)
                _save_json(cls.FILENAME, data)
                return c
        return None
    
    @classmethod
    def add_reference(cls, cycle_id: str, reference: Dict) -> Optional[Dict]:
        """添加引用"""
        data = _load_json(cls.FILENAME, {"cycles": []})
        for c in data["cycles"]:
            if c["id"] == cycle_id:
                reference["id"] = f"REF-{uuid.uuid4().hex[:6].upper()}"
                c["references"].append(reference)
                _save_json(cls.FILENAME, data)
                return c
        return None
    
    @classmethod
    def update_state(cls, cycle_id: str, state: str, progress: int = None) -> Optional[Dict]:
        """更新周期状态"""
        data = _load_json(cls.FILENAME, {"cycles": []})
        for c in data["cycles"]:
            if c["id"] == cycle_id:
                c["state"] = state
                if progress is not None:
                    c["progress"] = progress
                c["updated_at"] = datetime.now().isoformat()
                _save_json(cls.FILENAME, data)
                return c
        return None


# ============================================
# 报告管理
# ============================================

class ReportManager:
    """报告管理"""
    
    FILENAME = "reports.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有报告"""
        data = _load_json(cls.FILENAME, {"reports": []})
        return data.get("reports", [])
    
    @classmethod
    def get_by_type(cls, report_type: str) -> List[Dict]:
        """按类型获取报告"""
        return [r for r in cls.get_all() if r.get("type") == report_type]
    
    @classmethod
    def create(cls, report: Dict) -> Dict:
        """创建新报告"""
        data = _load_json(cls.FILENAME, {"reports": []})
        prefix = {"compliance": "CR", "research": "RR", "executive": "ER"}.get(report.get("type"), "RP")
        report["id"] = f"{prefix}-{datetime.now().strftime('%Y')}-{str(len(data['reports']) + 1).zfill(3)}"
        report["created_at"] = datetime.now().isoformat()
        report["status"] = report.get("status", "draft")
        data["reports"].insert(0, report)
        _save_json(cls.FILENAME, data)
        return report
    
    @classmethod
    def update_status(cls, report_id: str, status: str) -> Optional[Dict]:
        """更新报告状态"""
        data = _load_json(cls.FILENAME, {"reports": []})
        for r in data["reports"]:
            if r["id"] == report_id:
                r["status"] = status
                r["updated_at"] = datetime.now().isoformat()
                _save_json(cls.FILENAME, data)
                return r
        return None


# ============================================
# 审批管理
# ============================================

class ApprovalManager:
    """审批管理"""
    
    FILENAME = "approvals.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有审批项"""
        data = _load_json(cls.FILENAME, {"approvals": []})
        return data.get("approvals", [])
    
    @classmethod
    def get_pending(cls) -> List[Dict]:
        """获取待审批项"""
        return [a for a in cls.get_all() if a.get("status") == "pending"]
    
    @classmethod
    def create(cls, approval: Dict) -> Dict:
        """创建新审批项"""
        data = _load_json(cls.FILENAME, {"approvals": []})
        approval["id"] = f"APR-{str(len(data['approvals']) + 1).zfill(3)}"
        approval["created_at"] = datetime.now().isoformat()
        approval["status"] = "pending"
        data["approvals"].insert(0, approval)
        _save_json(cls.FILENAME, data)
        return approval
    
    @classmethod
    def approve(cls, approval_id: str, approver: str = None) -> Optional[Dict]:
        """批准"""
        data = _load_json(cls.FILENAME, {"approvals": []})
        for a in data["approvals"]:
            if a["id"] == approval_id:
                a["status"] = "approved"
                a["approved_at"] = datetime.now().isoformat()
                a["approved_by"] = approver
                _save_json(cls.FILENAME, data)
                return a
        return None
    
    @classmethod
    def reject(cls, approval_id: str, reason: str = None) -> Optional[Dict]:
        """驳回"""
        data = _load_json(cls.FILENAME, {"approvals": []})
        for a in data["approvals"]:
            if a["id"] == approval_id:
                a["status"] = "rejected"
                a["rejected_at"] = datetime.now().isoformat()
                a["reject_reason"] = reason
                _save_json(cls.FILENAME, data)
                return a
        return None


# ============================================
# 会议管理
# ============================================

class MeetingManager:
    """会议管理"""
    
    FILENAME = "meetings.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有会议"""
        data = _load_json(cls.FILENAME, {"meetings": []})
        return data.get("meetings", [])
    
    @classmethod
    def get_by_status(cls, status: str) -> List[Dict]:
        """按状态获取会议"""
        return [m for m in cls.get_all() if m.get("status") == status]
    
    @classmethod
    def get_by_id(cls, meeting_id: str) -> Optional[Dict]:
        """根据ID获取会议"""
        for m in cls.get_all():
            if m["id"] == meeting_id:
                return m
        return None
    
    @classmethod
    def create(cls, meeting: Dict) -> Dict:
        """创建新会议"""
        data = _load_json(cls.FILENAME, {"meetings": []})
        meeting["id"] = f"MEET-{str(len(data['meetings']) + 1).zfill(3)}"
        meeting["created_at"] = datetime.now().isoformat()
        meeting["status"] = meeting.get("status", "scheduled")
        meeting["messages"] = []
        meeting["decisions"] = []
        data["meetings"].insert(0, meeting)
        _save_json(cls.FILENAME, data)
        return meeting
    
    @classmethod
    def add_message(cls, meeting_id: str, message: Dict) -> Optional[Dict]:
        """添加消息"""
        data = _load_json(cls.FILENAME, {"meetings": []})
        for m in data["meetings"]:
            if m["id"] == meeting_id:
                message["timestamp"] = datetime.now().strftime("%H:%M")
                message["created_at"] = datetime.now().isoformat()
                m["messages"].append(message)
                _save_json(cls.FILENAME, data)
                return m
        return None
    
    @classmethod
    def update_status(cls, meeting_id: str, status: str) -> Optional[Dict]:
        """更新会议状态"""
        data = _load_json(cls.FILENAME, {"meetings": []})
        for m in data["meetings"]:
            if m["id"] == meeting_id:
                m["status"] = status
                m["updated_at"] = datetime.now().isoformat()
                _save_json(cls.FILENAME, data)
                return m
        return None


# ============================================
# 回测结果管理
# ============================================

class BacktestManager:
    """回测结果管理"""
    
    FILENAME = "backtests.json"
    
    @classmethod
    def get_all(cls) -> List[Dict]:
        """获取所有回测"""
        data = _load_json(cls.FILENAME, {"backtests": []})
        return data.get("backtests", [])
    
    @classmethod
    def get_by_id(cls, backtest_id: str) -> Optional[Dict]:
        """根据ID获取回测"""
        for b in cls.get_all():
            if b["id"] == backtest_id:
                return b
        return None
    
    @classmethod
    def create(cls, backtest: Dict) -> Dict:
        """创建新回测"""
        data = _load_json(cls.FILENAME, {"backtests": []})
        backtest["id"] = backtest.get("id") or f"BT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        backtest["created_at"] = datetime.now().isoformat()
        backtest["status"] = backtest.get("status", "running")
        data["backtests"].insert(0, backtest)
        _save_json(cls.FILENAME, data)
        return backtest
    
    @classmethod
    def update(cls, backtest_id: str, updates: Dict) -> Optional[Dict]:
        """更新回测"""
        data = _load_json(cls.FILENAME, {"backtests": []})
        for b in data["backtests"]:
            if b["id"] == backtest_id:
                b.update(updates)
                b["updated_at"] = datetime.now().isoformat()
                _save_json(cls.FILENAME, data)
                return b
        return None


# ============================================
# Agent 状态管理
# ============================================

class AgentStatusManager:
    """Agent 状态管理"""
    
    FILENAME = "agent_status.json"
    
    @classmethod
    def get_all(cls) -> Dict:
        """获取所有 Agent 状态"""
        return _load_json(cls.FILENAME, {"agents": {}, "updated_at": None})
    
    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[Dict]:
        """获取单个 Agent 状态"""
        data = cls.get_all()
        return data.get("agents", {}).get(agent_id)
    
    @classmethod
    def update_agent(cls, agent_id: str, status: Dict) -> Dict:
        """更新 Agent 状态"""
        data = _load_json(cls.FILENAME, {"agents": {}, "updated_at": None})
        status["updated_at"] = datetime.now().isoformat()
        data["agents"][agent_id] = status
        data["updated_at"] = datetime.now().isoformat()
        _save_json(cls.FILENAME, data)
        return status
    
    @classmethod
    def set_all_offline(cls) -> bool:
        """设置所有 Agent 为离线"""
        data = _load_json(cls.FILENAME, {"agents": {}, "updated_at": None})
        for agent_id in data.get("agents", {}):
            data["agents"][agent_id]["status"] = "offline"
            data["agents"][agent_id]["current_task"] = None
        data["updated_at"] = datetime.now().isoformat()
        return _save_json(cls.FILENAME, data)


# ============================================
# 初始化示例数据
# ============================================

def init_sample_data():
    """初始化示例数据（如果数据文件不存在）"""
    
    # 交易信号
    if not (DATA_DIR / SignalManager.FILENAME).exists():
        signals = [
            {
                "type": "buy", "symbol": "BTC/USDT", "price": 94850,
                "stop_loss": 93500, "take_profit": 98000, "quantity": 0.1,
                "confidence": 0.78, "strategy": "BTC 动量突破",
                "win_probability": 0.65, "risk_reward": 2.3, "position_size_pct": 0.1
            },
            {
                "type": "buy", "symbol": "ETH/USDT", "price": 3480,
                "stop_loss": 3380, "take_profit": 3650, "quantity": 2,
                "confidence": 0.72, "strategy": "ETH 均值回归",
                "win_probability": 0.58, "risk_reward": 1.7, "position_size_pct": 0.08
            },
        ]
        for s in signals:
            SignalManager.create(s)
    
    # 交易计划
    if not (DATA_DIR / TradingPlanManager.FILENAME).exists():
        plans = [
            {"name": "BTC 动量策略", "strategy_type": "Momentum", "state": "MONITORING", "win_rate": 0.62, "sharpe": 1.85},
            {"name": "ETH 均值回归", "strategy_type": "Mean Reversion", "state": "PENDING_CHAIRMAN", "win_rate": 0.58, "sharpe": 1.42},
            {"name": "波动率策略 v2", "strategy_type": "Volatility", "state": "SIMULATION", "win_rate": 0.55, "sharpe": 2.1},
        ]
        for p in plans:
            TradingPlanManager.create(p)
    
    # 研究周期
    if not (DATA_DIR / ResearchCycleManager.FILENAME).exists():
        cycles = [
            {
                "name": "BTC 动量突破策略", "strategy_type": "Momentum", "state": "RISK_SKEPTIC_GATE",
                "progress": 75, "owner": "alpha_a_lead", "team": "Alpha A",
                "metrics": {"sharpe": 1.85, "max_dd": -0.12, "win_rate": 0.58, "calmar": 1.42}
            },
            {
                "name": "ETH 均值回归", "strategy_type": "Mean Reversion", "state": "BACKTEST_GATE",
                "progress": 45, "owner": "alpha_a_researcher_1", "team": "Alpha A",
                "metrics": {"sharpe": 1.42, "max_dd": -0.08, "win_rate": 0.62, "calmar": 1.78}
            },
        ]
        for c in cycles:
            cycle = ResearchCycleManager.create(c)
            # 添加讨论
            ResearchCycleManager.add_discussion(cycle["id"], {
                "agent_id": "alpha_a_lead", "agent_name": "Alpha A 组长",
                "message": "回测显示 Sharpe 良好，等待风控审核。", "type": "comment"
            })
    
    # 报告
    if not (DATA_DIR / ReportManager.FILENAME).exists():
        reports = [
            {"type": "compliance", "title": "周度风控合规报告", "author": "CRO", "author_id": "cro", "status": "approved", "summary": "本周所有交易符合风控规则。"},
            {"type": "research", "title": "BTC 动量策略研究报告", "author": "Alpha A 组长", "author_id": "alpha_a_lead", "status": "approved", "summary": "策略回测显示 Sharpe 1.85。"},
            {"type": "executive", "title": "周度工作汇报", "author": "CEO", "author_id": "chief_of_staff", "status": "approved", "summary": "本周公司运营正常。"},
        ]
        for r in reports:
            ReportManager.create(r)
    
    # 审批
    if not (DATA_DIR / ApprovalManager.FILENAME).exists():
        approvals = [
            {"title": "BTC 动量策略执行计划", "type": "trading", "urgency": "high", "requester": "交易主管", "requester_id": "head_trader", "responsible": "CRO", "responsible_id": "cro", "description": "请求批准执行 BTC 动量策略"},
            {"title": "新增情绪分析工具", "type": "tool", "urgency": "normal", "requester": "Alpha A 组长", "requester_id": "alpha_a_lead", "responsible": "量化开发", "responsible_id": "quant_dev", "description": "请求授权开发新工具"},
        ]
        for a in approvals:
            ApprovalManager.create(a)
    
    # 会议
    if not (DATA_DIR / MeetingManager.FILENAME).exists():
        meeting = MeetingManager.create({
            "title": "投委会策略审议",
            "topic": "波动率策略 v2 小额测试申请",
            "status": "in_progress",
            "start_time": "14:00",
            "attendees": ["cio", "cro", "pm", "alpha_b_lead"]
        })
        MeetingManager.add_message(meeting["id"], {
            "agent_id": "cio", "agent_name": "CIO",
            "content": "会议开始，今天的议题是波动率策略 v2 的小额测试申请。",
            "type": "message"
        })
    
    logger.info("示例数据初始化完成")


# 模块加载时初始化
init_sample_data()
