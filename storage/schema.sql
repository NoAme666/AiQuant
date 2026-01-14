-- AI Quant Company - 数据库 Schema
-- PostgreSQL 15+

-- ============================================
-- 扩展
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for memory embedding search

-- ============================================
-- 枚举类型
-- ============================================

-- 研究周期状态
CREATE TYPE research_cycle_state AS ENUM (
    'IDEA_INTAKE',
    'DATA_GATE',
    'BACKTEST_GATE',
    'ROBUSTNESS_GATE',
    'RISK_SKEPTIC_GATE',
    'IC_REVIEW',
    'BOARD_PACK',
    'BOARD_DECISION',
    'ARCHIVE'
);

-- 闸门决策
CREATE TYPE gate_decision AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'RETURNED'  -- 退回补实验
);

-- 消息类型
CREATE TYPE message_type AS ENUM (
    'DM',           -- 1v1 直接消息
    'MEMO',         -- 结构化备忘录
    'MEETING',      -- 会议消息
    'SYSTEM'        -- 系统消息
);

-- 会议状态
CREATE TYPE meeting_status AS ENUM (
    'DRAFT',
    'PENDING_APPROVAL',
    'APPROVED',
    'REJECTED',
    'SCHEDULED',
    'IN_PROGRESS',
    'COMPLETED',
    'CANCELLED'
);

-- 风险等级
CREATE TYPE risk_level AS ENUM ('L', 'M', 'H');

-- Agent 状态
CREATE TYPE agent_status AS ENUM (
    'ACTIVE',
    'FROZEN',       -- 冻结
    'DEACTIVATED'   -- 停用
);

-- 审批状态
CREATE TYPE approval_status AS ENUM (
    'PENDING',
    'APPROVED',
    'REJECTED',
    'SKIPPED'       -- 条件不满足，跳过
);

-- 产物类型
CREATE TYPE artifact_type AS ENUM (
    'STRATEGY_IDEA_MEMO',
    'DATA_QA_REPORT',
    'BACKTEST_REPORT',
    'ROBUSTNESS_REPORT',
    'RISK_MEMO',
    'IC_MINUTES',
    'BOARD_PACK',
    'RESEARCH_REPORT',
    'CHAIRMAN_DIRECTIVE',
    'MEETING_MINUTES',
    'TEAM_SYNTHESIS_MEMO',
    'MEETING_CARD',
    'MEETING_PLOT',
    'MEETING_TABLE'
);

-- 记忆范围
CREATE TYPE memory_scope AS ENUM (
    'private',   -- 仅自己可见
    'team',      -- 团队可见
    'org'        -- 全组织可见
);

-- 工具调用状态
CREATE TYPE tool_call_status AS ENUM (
    'requested',
    'approved',
    'executing',
    'completed',
    'failed',
    'rejected'
);

-- 会议卡片类型
CREATE TYPE meeting_card_type AS ENUM (
    'metric',    -- 指标卡
    'plot',      -- 图表
    'table',     -- 表格
    'summary'    -- 摘要文本
);

-- ============================================
-- 核心表
-- ============================================

-- Agent 表
CREATE TABLE agents (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    name_en VARCHAR(128),
    department VARCHAR(64) NOT NULL,
    is_lead BOOLEAN DEFAULT FALSE,
    capability_tier VARCHAR(32) NOT NULL,
    team VARCHAR(64),
    reports_to VARCHAR(64) REFERENCES agents(id),
    status agent_status DEFAULT 'ACTIVE',
    veto_power BOOLEAN DEFAULT FALSE,
    can_force_retest BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建 Agent 索引
CREATE INDEX idx_agents_department ON agents(department);
CREATE INDEX idx_agents_team ON agents(team);
CREATE INDEX idx_agents_status ON agents(status);

-- ============================================
-- 消息系统
-- ============================================

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_type message_type NOT NULL,
    from_agent VARCHAR(64) NOT NULL REFERENCES agents(id),
    to_agent VARCHAR(64) REFERENCES agents(id),  -- NULL 表示广播
    subject VARCHAR(256),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- 关联
    research_cycle_id UUID,
    meeting_id UUID,
    parent_message_id UUID REFERENCES messages(id),
    
    -- 审计
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ,
    
    -- 全文搜索
    search_vector TSVECTOR
);

-- 消息索引
CREATE INDEX idx_messages_from ON messages(from_agent);
CREATE INDEX idx_messages_to ON messages(to_agent);
CREATE INDEX idx_messages_type ON messages(message_type);
CREATE INDEX idx_messages_created ON messages(created_at DESC);
CREATE INDEX idx_messages_cycle ON messages(research_cycle_id);
CREATE INDEX idx_messages_search ON messages USING GIN(search_vector);

-- 更新搜索向量触发器
CREATE OR REPLACE FUNCTION update_message_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.subject, '') || ' ' || NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_search_update
    BEFORE INSERT OR UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_message_search_vector();

-- ============================================
-- 事件流
-- ============================================

-- 事件表（审计日志）
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(128) NOT NULL,
    actor VARCHAR(64) REFERENCES agents(id),
    target_type VARCHAR(64),  -- 'research_cycle', 'agent', 'meeting', etc.
    target_id UUID,
    action VARCHAR(128) NOT NULL,
    details JSONB DEFAULT '{}',
    
    -- 可复现性
    experiment_id VARCHAR(128),
    data_version_hash VARCHAR(64),
    code_commit VARCHAR(40),
    config_hash VARCHAR(64),
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 签名（防篡改）
    signature VARCHAR(128)
);

-- 事件索引
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_actor ON events(actor);
CREATE INDEX idx_events_target ON events(target_type, target_id);
CREATE INDEX idx_events_created ON events(created_at DESC);
CREATE INDEX idx_events_experiment ON events(experiment_id);

-- ============================================
-- 研究周期
-- ============================================

-- 研究周期表
CREATE TABLE research_cycles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(256) NOT NULL,
    description TEXT,
    
    -- 状态
    current_state research_cycle_state DEFAULT 'IDEA_INTAKE',
    previous_state research_cycle_state,
    
    -- 归属
    proposer VARCHAR(64) REFERENCES agents(id),
    team VARCHAR(64),
    
    -- 时间追踪
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- 闸门通过记录
    gates_passed JSONB DEFAULT '{}',
    
    -- 最终决策
    final_decision gate_decision,
    decision_reason TEXT,
    
    -- 关联的实验和产物
    experiment_ids VARCHAR(128)[],
    artifact_ids UUID[]
);

-- 研究周期索引
CREATE INDEX idx_cycles_state ON research_cycles(current_state);
CREATE INDEX idx_cycles_team ON research_cycles(team);
CREATE INDEX idx_cycles_created ON research_cycles(created_at DESC);

-- 研究周期状态历史
CREATE TABLE research_cycle_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id UUID NOT NULL REFERENCES research_cycles(id),
    from_state research_cycle_state,
    to_state research_cycle_state NOT NULL,
    triggered_by VARCHAR(64) REFERENCES agents(id),
    reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cycle_history_cycle ON research_cycle_history(cycle_id);
CREATE INDEX idx_cycle_history_created ON research_cycle_history(created_at DESC);

-- ============================================
-- 闸门审批
-- ============================================

-- 闸门审批表
CREATE TABLE gate_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id UUID NOT NULL REFERENCES research_cycles(id),
    gate research_cycle_state NOT NULL,
    
    -- 审批者
    approver VARCHAR(64) NOT NULL REFERENCES agents(id),
    decision approval_status DEFAULT 'PENDING',
    
    -- 详情
    comments TEXT,
    required_experiments TEXT[],  -- 要求补充的实验
    veto_used BOOLEAN DEFAULT FALSE,
    force_retest_used BOOLEAN DEFAULT FALSE,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    deadline_at TIMESTAMPTZ
);

CREATE INDEX idx_gate_approvals_cycle ON gate_approvals(cycle_id);
CREATE INDEX idx_gate_approvals_gate ON gate_approvals(gate);
CREATE INDEX idx_gate_approvals_approver ON gate_approvals(approver);

-- ============================================
-- 会议系统
-- ============================================

-- 会议申请表
CREATE TABLE meeting_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 基本信息
    title VARCHAR(256) NOT NULL,
    goal TEXT NOT NULL,
    agenda JSONB NOT NULL,  -- ["议程1", "议程2", ...]
    
    -- 参与者
    requester VARCHAR(64) NOT NULL REFERENCES agents(id),
    participants VARCHAR(64)[] NOT NULL,
    
    -- 预期产物
    expected_artifacts TEXT[],
    
    -- 风险与资源
    risk_level risk_level DEFAULT 'L',
    compute_cost_estimate INTEGER DEFAULT 0,
    duration_minutes INTEGER DEFAULT 20,
    
    -- 状态
    status meeting_status DEFAULT 'DRAFT',
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    scheduled_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    
    -- 关联
    research_cycle_id UUID REFERENCES research_cycles(id)
);

CREATE INDEX idx_meeting_requests_status ON meeting_requests(status);
CREATE INDEX idx_meeting_requests_requester ON meeting_requests(requester);
CREATE INDEX idx_meeting_requests_scheduled ON meeting_requests(scheduled_at);

-- 会议审批链
CREATE TABLE meeting_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES meeting_requests(id),
    
    -- 审批步骤
    step INTEGER NOT NULL,
    approver VARCHAR(64) NOT NULL REFERENCES agents(id),
    status approval_status DEFAULT 'PENDING',
    
    -- 详情
    comments TEXT,
    modifications JSONB,  -- 对会议申请的修改建议
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    
    UNIQUE(meeting_id, step)
);

CREATE INDEX idx_meeting_approvals_meeting ON meeting_approvals(meeting_id);
CREATE INDEX idx_meeting_approvals_status ON meeting_approvals(status);

-- ============================================
-- 实验记录
-- ============================================

-- 实验表
CREATE TABLE experiments (
    id VARCHAR(128) PRIMARY KEY,  -- ExperimentID
    
    -- 关联
    research_cycle_id UUID REFERENCES research_cycles(id),
    
    -- 可复现四件套
    data_version_hash VARCHAR(64) NOT NULL,
    code_commit VARCHAR(40) NOT NULL,
    config_hash VARCHAR(64) NOT NULL,
    random_seed BIGINT,
    
    -- 实验类型
    experiment_type VARCHAR(64) NOT NULL,  -- 'backtest', 'robustness', 'stress_test'
    
    -- 配置
    config JSONB NOT NULL,
    
    -- 结果
    metrics JSONB,  -- {sharpe, returns, max_dd, ...}
    status VARCHAR(32) DEFAULT 'PENDING',  -- PENDING, RUNNING, COMPLETED, FAILED
    
    -- 产物路径
    artifacts_path TEXT,
    
    -- 资源消耗
    compute_points_used INTEGER DEFAULT 0,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- 执行者
    executed_by VARCHAR(64) REFERENCES agents(id)
);

CREATE INDEX idx_experiments_cycle ON experiments(research_cycle_id);
CREATE INDEX idx_experiments_type ON experiments(experiment_type);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_experiments_created ON experiments(created_at DESC);

-- ============================================
-- 产物归档
-- ============================================

-- 产物表
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 类型与名称
    artifact_type artifact_type NOT NULL,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    
    -- 关联
    research_cycle_id UUID REFERENCES research_cycles(id),
    experiment_id VARCHAR(128) REFERENCES experiments(id),
    meeting_id UUID REFERENCES meeting_requests(id),
    
    -- 创建者
    created_by VARCHAR(64) REFERENCES agents(id),
    
    -- 内容
    content_type VARCHAR(64),  -- 'markdown', 'json', 'pdf', 'parquet'
    content TEXT,  -- 或存储路径
    file_path TEXT,
    file_size_bytes BIGINT,
    checksum VARCHAR(64),
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 版本
    version INTEGER DEFAULT 1,
    parent_artifact_id UUID REFERENCES artifacts(id),
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX idx_artifacts_cycle ON artifacts(research_cycle_id);
CREATE INDEX idx_artifacts_created_by ON artifacts(created_by);
CREATE INDEX idx_artifacts_created ON artifacts(created_at DESC);

-- ============================================
-- 预算系统
-- ============================================

-- 预算账户
CREATE TABLE budget_accounts (
    id VARCHAR(64) PRIMARY KEY,  -- team_id 或 agent_id
    account_type VARCHAR(32) NOT NULL,  -- 'team' 或 'agent'
    
    -- 基础预算
    base_weekly_points INTEGER NOT NULL,
    
    -- 当前周期
    current_period_start DATE NOT NULL,
    current_period_points INTEGER NOT NULL,
    points_spent INTEGER DEFAULT 0,
    
    -- 声誉调整
    reputation_multiplier DECIMAL(3,2) DEFAULT 1.00,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 预算流水
CREATE TABLE budget_ledger (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id VARCHAR(64) NOT NULL REFERENCES budget_accounts(id),
    
    -- 交易
    transaction_type VARCHAR(32) NOT NULL,  -- 'allocation', 'spend', 'refund', 'bonus'
    amount INTEGER NOT NULL,  -- 正数增加，负数减少
    balance_after INTEGER NOT NULL,
    
    -- 关联
    experiment_id VARCHAR(128) REFERENCES experiments(id),
    operation VARCHAR(128),  -- 'backtest', 'grid_search', etc.
    
    -- 详情
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_budget_ledger_account ON budget_ledger(account_id);
CREATE INDEX idx_budget_ledger_created ON budget_ledger(created_at DESC);

-- ============================================
-- 声誉系统
-- ============================================

-- 声誉评分
CREATE TABLE reputation_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 分数
    overall_score DECIMAL(5,4) NOT NULL,  -- 0.0000 - 1.0000
    
    -- 各维度得分
    pass_rate DECIMAL(5,4),
    return_rate DECIMAL(5,4),
    budget_efficiency DECIMAL(5,4),
    post_launch_performance DECIMAL(5,4),
    collaboration_score DECIMAL(5,4),
    
    -- 等级
    grade VARCHAR(32),  -- 'excellent', 'good', 'average', 'poor', 'critical'
    
    -- 采样数
    sample_count INTEGER DEFAULT 0,
    
    -- 时间
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    period_start DATE,
    period_end DATE
);

CREATE INDEX idx_reputation_agent ON reputation_scores(agent_id);
CREATE INDEX idx_reputation_calculated ON reputation_scores(calculated_at DESC);

-- 声誉事件
CREATE TABLE reputation_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 事件
    event_type VARCHAR(64) NOT NULL,  -- 'proposal_passed', 'strategy_launched', etc.
    points_change INTEGER NOT NULL,
    
    -- 关联
    research_cycle_id UUID REFERENCES research_cycles(id),
    experiment_id VARCHAR(128) REFERENCES experiments(id),
    
    -- 详情
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reputation_events_agent ON reputation_events(agent_id);
CREATE INDEX idx_reputation_events_created ON reputation_events(created_at DESC);

-- ============================================
-- 董事长指令
-- ============================================

-- 董事长指令表
CREATE TABLE chairman_directives (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 指令内容
    directive_type VARCHAR(64) NOT NULL,  -- 'constraint_adjustment', 'request_experiment', etc.
    target_type VARCHAR(64),  -- 'agent', 'team', 'research_cycle', 'global'
    target_id VARCHAR(128),
    content TEXT NOT NULL,
    
    -- 范围与期限
    scope VARCHAR(32) DEFAULT 'global',  -- 'specific', 'global'
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_until TIMESTAMPTZ,
    
    -- 原因
    reason TEXT NOT NULL,
    
    -- 状态
    status VARCHAR(32) DEFAULT 'ACTIVE',  -- 'ACTIVE', 'EXPIRED', 'REVOKED'
    
    -- 审计
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT
);

CREATE INDEX idx_directives_type ON chairman_directives(directive_type);
CREATE INDEX idx_directives_target ON chairman_directives(target_type, target_id);
CREATE INDEX idx_directives_status ON chairman_directives(status);

-- ============================================
-- 数据版本
-- ============================================

-- 数据版本表
CREATE TABLE data_versions (
    hash VARCHAR(64) PRIMARY KEY,
    
    -- 数据范围
    symbols TEXT[] NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    frequency VARCHAR(16) NOT NULL,  -- '1d', '1h', '1m'
    
    -- 数据源
    provider VARCHAR(64) NOT NULL,
    
    -- 统计
    row_count BIGINT,
    
    -- 存储
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_data_versions_created ON data_versions(created_at DESC);

-- ============================================
-- Agent 记忆系统 (pgvector)
-- ============================================

-- Agent 记忆表
CREATE TABLE agent_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 内容 (限制500字)
    content TEXT NOT NULL CHECK (LENGTH(content) <= 500),
    
    -- 结构化元数据
    tags TEXT[] NOT NULL DEFAULT '{}',
    scope memory_scope NOT NULL DEFAULT 'private',
    confidence FLOAT NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    
    -- TTL
    ttl INTERVAL,
    expires_at TIMESTAMPTZ,
    
    -- 向量嵌入 (1536维，text-embedding-3-small)
    embedding vector(1536),
    
    -- 强制引用 (必须指向 experiment_id, data_version_hash, artifact)
    refs JSONB NOT NULL DEFAULT '{}',  -- {"experiment_id": "...", "data_version_hash": "...", "artifact_id": "..."}
    
    -- 审批状态 (private 自动批准)
    approval_status approval_status DEFAULT 'APPROVED',
    approved_by VARCHAR(64) REFERENCES agents(id),
    approved_at TIMESTAMPTZ,
    
    -- 全文搜索
    search_vector TSVECTOR,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent 记忆索引
CREATE INDEX idx_agent_memory_agent ON agent_memory(agent_id);
CREATE INDEX idx_agent_memory_scope ON agent_memory(scope);
CREATE INDEX idx_agent_memory_tags ON agent_memory USING GIN(tags);
CREATE INDEX idx_agent_memory_expires ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_agent_memory_embedding ON agent_memory USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_agent_memory_search ON agent_memory USING GIN(search_vector);
CREATE INDEX idx_agent_memory_approval ON agent_memory(approval_status) WHERE approval_status = 'PENDING';

-- 更新记忆搜索向量触发器
CREATE OR REPLACE FUNCTION update_memory_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', NEW.content);
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER agent_memory_search_update
    BEFORE INSERT OR UPDATE ON agent_memory
    FOR EACH ROW EXECUTE FUNCTION update_memory_search_vector();

-- 记忆审批表 (team/org 范围需要审批)
CREATE TABLE memory_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES agent_memory(id) ON DELETE CASCADE,
    
    -- 审批步骤
    step INTEGER NOT NULL,
    approver VARCHAR(64) NOT NULL REFERENCES agents(id),
    status approval_status DEFAULT 'PENDING',
    
    -- 详情
    comments TEXT,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    
    UNIQUE(memory_id, step)
);

CREATE INDEX idx_memory_approvals_memory ON memory_approvals(memory_id);
CREATE INDEX idx_memory_approvals_status ON memory_approvals(status);
CREATE INDEX idx_memory_approvals_approver ON memory_approvals(approver);

-- ============================================
-- 工具调用系统
-- ============================================

-- 工具调用记录表
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 调用者
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 工具信息
    tool_name VARCHAR(128) NOT NULL,  -- e.g., 'market.get_ohlcv', 'backtest.run'
    tool_args JSONB NOT NULL DEFAULT '{}',
    
    -- 状态
    status tool_call_status DEFAULT 'requested',
    
    -- 权限审批 (如果需要)
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(64) REFERENCES agents(id),
    approval_reason TEXT,
    
    -- 预算
    estimated_cost INTEGER DEFAULT 0,
    actual_cost INTEGER DEFAULT 0,
    
    -- 结果
    result JSONB,
    error_message TEXT,
    
    -- 可追溯性
    data_version_hash VARCHAR(64),
    experiment_id VARCHAR(128),
    artifact_ids UUID[],
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- 关联
    meeting_id UUID REFERENCES meeting_requests(id),
    research_cycle_id UUID REFERENCES research_cycles(id)
);

-- 工具调用索引
CREATE INDEX idx_tool_calls_agent ON tool_calls(agent_id);
CREATE INDEX idx_tool_calls_tool ON tool_calls(tool_name);
CREATE INDEX idx_tool_calls_status ON tool_calls(status);
CREATE INDEX idx_tool_calls_created ON tool_calls(created_at DESC);
CREATE INDEX idx_tool_calls_meeting ON tool_calls(meeting_id) WHERE meeting_id IS NOT NULL;

-- ============================================
-- 会议展示系统
-- ============================================

-- 会议展示卡片表
CREATE TABLE meeting_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID NOT NULL REFERENCES meeting_requests(id),
    
    -- 展示者
    presenter VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 卡片信息
    title VARCHAR(256) NOT NULL,
    card_type meeting_card_type NOT NULL,
    
    -- 内容
    data JSONB NOT NULL,  -- 卡片具体内容
    
    -- 引用的数据/实验
    data_ref JSONB,  -- {"artifact_path": "...", "parquet_path": "...", "preview_rows": 20}
    experiment_id VARCHAR(128) REFERENCES experiments(id),
    data_version_hash VARCHAR(64),
    
    -- 排序
    display_order INTEGER DEFAULT 0,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 会议展示索引
CREATE INDEX idx_meeting_artifacts_meeting ON meeting_artifacts(meeting_id);
CREATE INDEX idx_meeting_artifacts_presenter ON meeting_artifacts(presenter);
CREATE INDEX idx_meeting_artifacts_type ON meeting_artifacts(card_type);

-- ============================================
-- 治理与组织进化系统 (Meta-Governance)
-- ============================================

-- 提案状态
CREATE TYPE proposal_status AS ENUM (
    'draft',
    'pending_cgo',
    'pending_chairman',
    'approved',
    'rejected',
    'withdrawn'
);

-- 反馈类别
CREATE TYPE feedback_category AS ENUM (
    'tool_request',
    'process_improvement',
    'org_issue',
    'collaboration',
    'capability_gap'
);

-- 告警严重程度
CREATE TYPE alert_severity AS ENUM (
    'info',
    'warning',
    'critical',
    'red_alert'
);

-- 冻结状态
CREATE TYPE freeze_status AS ENUM (
    'active',
    'lifted',
    'expired'
);

-- 招聘提案表
CREATE TABLE hiring_proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 基本信息
    role_name VARCHAR(128) NOT NULL,
    role_id VARCHAR(64),  -- 建议的 agent_id
    department VARCHAR(64) NOT NULL,
    
    -- 发起人
    proposed_by VARCHAR(64) NOT NULL REFERENCES agents(id),  -- 通常是 CPO
    suggested_by VARCHAR(64) REFERENCES agents(id),  -- 原始建议来源（CIO/CRO/HoR等）
    
    -- 理由
    justification JSONB NOT NULL,  -- ["原因1", "原因2", ...]
    expected_roi TEXT,
    
    -- 试用规则
    trial_rules JSONB,  -- {"duration": "30 days", "success_metrics": [...]}
    
    -- 岗位定义
    job_spec JSONB,  -- {"persona": {...}, "capability_tier": "...", ...}
    
    -- 预算影响
    estimated_weekly_budget INTEGER,
    
    -- 状态
    status proposal_status DEFAULT 'draft',
    
    -- 审批记录
    cgo_review JSONB,  -- {"approved": true/false, "comments": "...", "at": "..."}
    chairman_review JSONB,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ
);

CREATE INDEX idx_hiring_proposals_status ON hiring_proposals(status);
CREATE INDEX idx_hiring_proposals_proposed_by ON hiring_proposals(proposed_by);
CREATE INDEX idx_hiring_proposals_created ON hiring_proposals(created_at DESC);

-- 终止/冻结提案表
CREATE TABLE termination_proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 目标 Agent
    target_agent VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 发起人
    proposed_by VARCHAR(64) NOT NULL REFERENCES agents(id),  -- 通常是 CPO
    
    -- 类型
    proposal_type VARCHAR(32) NOT NULL,  -- 'freeze', 'terminate'
    
    -- 证据（必须来自 2+ 独立部门）
    evidence JSONB NOT NULL,  -- [{"source": "dept", "type": "...", "content": "..."}]
    negative_feedback_count INTEGER DEFAULT 0,
    independent_sources INTEGER DEFAULT 0,  -- 必须 >= 2
    
    -- 绩效记录
    scorecard JSONB,  -- Agent 的综合评分卡
    
    -- 理由
    justification TEXT NOT NULL,
    
    -- 状态
    status proposal_status DEFAULT 'draft',
    
    -- 审批记录
    cgo_review JSONB,
    chairman_review JSONB,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ
);

CREATE INDEX idx_termination_proposals_target ON termination_proposals(target_agent);
CREATE INDEX idx_termination_proposals_status ON termination_proposals(status);

-- Agent 冻结记录表
CREATE TABLE agent_freezes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 被冻结的 Agent
    agent_id VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 冻结者（通常是 CGO）
    frozen_by VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 原因
    reason TEXT NOT NULL,
    evidence_refs JSONB,  -- 引用的证据
    
    -- 关联的终止提案（如果有）
    termination_proposal_id UUID REFERENCES termination_proposals(id),
    
    -- 冻结期限
    duration INTERVAL,
    expires_at TIMESTAMPTZ,
    
    -- 状态
    status freeze_status DEFAULT 'active',
    
    -- 解冻信息
    lifted_by VARCHAR(64) REFERENCES agents(id),
    lifted_reason TEXT,
    lifted_at TIMESTAMPTZ,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_freezes_agent ON agent_freezes(agent_id);
CREATE INDEX idx_agent_freezes_status ON agent_freezes(status);
CREATE INDEX idx_agent_freezes_created ON agent_freezes(created_at DESC);

-- 治理告警表
CREATE TABLE governance_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 发起者（通常是 CGO）
    issued_by VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 严重程度
    severity alert_severity NOT NULL,
    
    -- 告警内容
    title VARCHAR(256) NOT NULL,
    content TEXT NOT NULL,
    
    -- 涉及的对象
    target_type VARCHAR(64),  -- 'agent', 'department', 'process', 'system'
    target_id VARCHAR(128),
    
    -- 类别
    category VARCHAR(64),  -- 'collusion', 'budget_abuse', 'process_bypass', 'manipulation'
    
    -- 证据
    evidence JSONB,
    
    -- 建议行动
    recommended_action TEXT,
    
    -- 状态
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(64) REFERENCES agents(id),
    acknowledged_at TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT FALSE,
    resolution TEXT,
    resolved_at TIMESTAMPTZ,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_governance_alerts_severity ON governance_alerts(severity);
CREATE INDEX idx_governance_alerts_acknowledged ON governance_alerts(acknowledged);
CREATE INDEX idx_governance_alerts_created ON governance_alerts(created_at DESC);

-- 反馈通道表
CREATE TABLE feedback_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 提交者
    submitted_by VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 类别
    category feedback_category NOT NULL,
    
    -- 内容
    title VARCHAR(256),
    content TEXT NOT NULL,
    
    -- 紧急程度
    urgency VARCHAR(16) DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
    
    -- 引用（证据）
    refs JSONB,  -- {"experiment_id": "...", "conversation_id": "..."}
    
    -- 自动提取 vs 主动提交
    source VARCHAR(32) DEFAULT 'manual',  -- 'manual', 'auto_extracted'
    extraction_context JSONB,  -- 自动提取时的上下文
    
    -- 处理状态
    status VARCHAR(32) DEFAULT 'open',  -- 'open', 'in_review', 'accepted', 'rejected', 'implemented'
    reviewed_by VARCHAR(64) REFERENCES agents(id),
    review_notes TEXT,
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX idx_feedback_entries_category ON feedback_entries(category);
CREATE INDEX idx_feedback_entries_status ON feedback_entries(status);
CREATE INDEX idx_feedback_entries_submitted_by ON feedback_entries(submitted_by);
CREATE INDEX idx_feedback_entries_created ON feedback_entries(created_at DESC);

-- 工具请求表（从反馈中提取的具体工具需求）
CREATE TABLE tool_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 来源反馈
    feedback_id UUID REFERENCES feedback_entries(id),
    
    -- 请求者
    requested_by VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 工具信息
    tool_name VARCHAR(128) NOT NULL,
    tool_description TEXT NOT NULL,
    
    -- 预期收益
    expected_benefit TEXT,
    use_case TEXT,
    
    -- 紧急程度
    urgency VARCHAR(16) DEFAULT 'medium',
    
    -- 技术评估（CTO* 填写）
    feasibility_score FLOAT,  -- 0-1
    estimated_effort VARCHAR(32),  -- 'small', 'medium', 'large', 'epic'
    technical_notes TEXT,
    
    -- 优先级（CTO* 计算）
    priority_score FLOAT,
    
    -- 状态
    status VARCHAR(32) DEFAULT 'requested',  -- 'requested', 'evaluated', 'approved', 'in_development', 'deployed', 'rejected'
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    evaluated_at TIMESTAMPTZ,
    deployed_at TIMESTAMPTZ
);

CREATE INDEX idx_tool_requests_status ON tool_requests(status);
CREATE INDEX idx_tool_requests_priority ON tool_requests(priority_score DESC);
CREATE INDEX idx_tool_requests_created ON tool_requests(created_at DESC);

-- 能力缺口报告表
CREATE TABLE capability_gap_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 报告者（通常是 CTO*）
    reported_by VARCHAR(64) NOT NULL REFERENCES agents(id),
    
    -- 报告期间
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- 内容
    summary TEXT NOT NULL,
    
    -- 工具使用统计
    tool_usage_stats JSONB,  -- {"tool_name": {"calls": N, "cost": N, "success_rate": 0.xx}}
    
    -- 最常请求的工具
    most_requested_tools JSONB,  -- [{"name": "...", "request_count": N, "urgency_avg": "..."}]
    
    -- 能力缺口
    capability_gaps JSONB,  -- [{"gap": "...", "impact": "...", "recommended_action": "..."}]
    
    -- 工具淘汰建议
    deprecation_candidates JSONB,  -- [{"tool": "...", "reason": "...", "usage_rate": 0.xx}]
    
    -- 招聘建议（如果能力缺口需要人而非工具）
    hiring_recommendations JSONB,
    
    -- 优先级排序的开发建议
    development_priorities JSONB,  -- [{"priority": 1, "item": "...", "justification": "..."}]
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_capability_gap_reports_period ON capability_gap_reports(period_start, period_end);
CREATE INDEX idx_capability_gap_reports_created ON capability_gap_reports(created_at DESC);

-- ============================================
-- 治理系统视图
-- ============================================

-- 待处理提案视图
CREATE VIEW pending_proposals AS
SELECT 
    'hiring' as proposal_type,
    hp.id,
    hp.role_name as title,
    hp.proposed_by,
    hp.status,
    hp.created_at
FROM hiring_proposals hp
WHERE hp.status IN ('draft', 'pending_cgo', 'pending_chairman')
UNION ALL
SELECT 
    'termination' as proposal_type,
    tp.id,
    'Terminate: ' || tp.target_agent as title,
    tp.proposed_by,
    tp.status,
    tp.created_at
FROM termination_proposals tp
WHERE tp.status IN ('draft', 'pending_cgo', 'pending_chairman');

-- 活跃冻结视图
CREATE VIEW active_freezes AS
SELECT 
    af.*,
    a.name as agent_name,
    fb.name as frozen_by_name
FROM agent_freezes af
JOIN agents a ON af.agent_id = a.id
JOIN agents fb ON af.frozen_by = fb.id
WHERE af.status = 'active'
  AND (af.expires_at IS NULL OR af.expires_at > NOW());

-- 未解决告警视图
CREATE VIEW unresolved_alerts AS
SELECT ga.*
FROM governance_alerts ga
WHERE ga.resolved = FALSE
ORDER BY 
    CASE ga.severity 
        WHEN 'red_alert' THEN 1 
        WHEN 'critical' THEN 2 
        WHEN 'warning' THEN 3 
        ELSE 4 
    END,
    ga.created_at DESC;

-- ============================================
-- 视图
-- ============================================

-- 活跃研究周期视图
CREATE VIEW active_research_cycles AS
SELECT 
    rc.*,
    a.name as proposer_name,
    a.department as proposer_department
FROM research_cycles rc
LEFT JOIN agents a ON rc.proposer = a.id
WHERE rc.current_state != 'ARCHIVE';

-- Agent 当前状态视图
CREATE VIEW agent_current_status AS
SELECT 
    a.*,
    COALESCE(rs.overall_score, 0.5) as reputation_score,
    COALESCE(rs.grade, 'average') as reputation_grade,
    COALESCE(ba.current_period_points - ba.points_spent, 0) as budget_remaining
FROM agents a
LEFT JOIN LATERAL (
    SELECT overall_score, grade 
    FROM reputation_scores 
    WHERE agent_id = a.id 
    ORDER BY calculated_at DESC 
    LIMIT 1
) rs ON true
LEFT JOIN budget_accounts ba ON ba.id = a.id OR ba.id = a.team;

-- 待审批会议视图
CREATE VIEW pending_meetings AS
SELECT 
    mr.*,
    a.name as requester_name,
    ma.step as current_approval_step,
    ma.approver as current_approver
FROM meeting_requests mr
JOIN agents a ON mr.requester = a.id
LEFT JOIN meeting_approvals ma ON ma.meeting_id = mr.id AND ma.status = 'PENDING'
WHERE mr.status IN ('PENDING_APPROVAL', 'DRAFT');

-- ============================================
-- 函数
-- ============================================

-- 生成 ExperimentID
CREATE OR REPLACE FUNCTION generate_experiment_id()
RETURNS VARCHAR(128) AS $$
DECLARE
    timestamp_part VARCHAR(20);
    random_part VARCHAR(8);
BEGIN
    timestamp_part := TO_CHAR(NOW(), 'YYYYMMDD_HH24MISS');
    random_part := UPPER(SUBSTR(MD5(RANDOM()::TEXT), 1, 8));
    RETURN 'EXP_' || timestamp_part || '_' || random_part;
END;
$$ LANGUAGE plpgsql;

-- 计算配置哈希
CREATE OR REPLACE FUNCTION compute_config_hash(config JSONB)
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN ENCODE(DIGEST(config::TEXT, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- 检查预算是否足够
CREATE OR REPLACE FUNCTION check_budget(account_id VARCHAR(64), required_points INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    available INTEGER;
BEGIN
    SELECT current_period_points - points_spent INTO available
    FROM budget_accounts
    WHERE id = account_id;
    
    RETURN COALESCE(available, 0) >= required_points;
END;
$$ LANGUAGE plpgsql;

-- 扣除预算
CREATE OR REPLACE FUNCTION deduct_budget(
    p_account_id VARCHAR(64),
    p_amount INTEGER,
    p_operation VARCHAR(128),
    p_experiment_id VARCHAR(128) DEFAULT NULL,
    p_description TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_balance INTEGER;
BEGIN
    -- 检查并扣除
    UPDATE budget_accounts
    SET points_spent = points_spent + p_amount,
        updated_at = NOW()
    WHERE id = p_account_id
      AND (current_period_points - points_spent) >= p_amount
    RETURNING (current_period_points - points_spent) INTO v_balance;
    
    IF v_balance IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- 记录流水
    INSERT INTO budget_ledger (account_id, transaction_type, amount, balance_after, operation, experiment_id, description)
    VALUES (p_account_id, 'spend', -p_amount, v_balance, p_operation, p_experiment_id, p_description);
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 混合搜索 Agent 记忆 (向量 + 关键词 + 标签，RRF 排序)
CREATE OR REPLACE FUNCTION search_agent_memory(
    p_agent_id VARCHAR(64),
    p_query_embedding vector(1536),
    p_query_text TEXT DEFAULT NULL,
    p_tags TEXT[] DEFAULT NULL,
    p_scopes memory_scope[] DEFAULT ARRAY['private']::memory_scope[],
    p_top_k INTEGER DEFAULT 10
)
RETURNS TABLE (
    memory_id UUID,
    content TEXT,
    tags TEXT[],
    scope memory_scope,
    confidence FLOAT,
    refs JSONB,
    rrf_score FLOAT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    WITH filtered AS (
        -- 基础过滤：scope、tags、过期、审批状态
        SELECT m.*
        FROM agent_memory m
        WHERE m.agent_id = p_agent_id
          AND m.scope = ANY(p_scopes)
          AND m.approval_status = 'APPROVED'
          AND (m.expires_at IS NULL OR m.expires_at > NOW())
          AND (p_tags IS NULL OR m.tags && p_tags)
    ),
    vector_ranked AS (
        -- 向量相似度排序
        SELECT 
            f.id,
            f.embedding <=> p_query_embedding AS vec_dist,
            ROW_NUMBER() OVER (ORDER BY f.embedding <=> p_query_embedding) AS vec_rank
        FROM filtered f
        WHERE f.embedding IS NOT NULL
    ),
    text_ranked AS (
        -- 全文搜索排序
        SELECT 
            f.id,
            ts_rank_cd(f.search_vector, plainto_tsquery('english', p_query_text)) AS text_score,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(f.search_vector, plainto_tsquery('english', p_query_text)) DESC) AS text_rank
        FROM filtered f
        WHERE p_query_text IS NOT NULL 
          AND f.search_vector @@ plainto_tsquery('english', p_query_text)
    ),
    combined AS (
        -- RRF (Reciprocal Rank Fusion) 合并
        SELECT 
            COALESCE(v.id, t.id) AS id,
            COALESCE(1.0 / (60 + v.vec_rank), 0) + COALESCE(1.0 / (60 + t.text_rank), 0) AS rrf_score
        FROM vector_ranked v
        FULL OUTER JOIN text_ranked t ON v.id = t.id
    )
    SELECT 
        f.id AS memory_id,
        f.content,
        f.tags,
        f.scope,
        f.confidence,
        f.refs,
        c.rrf_score,
        f.created_at
    FROM combined c
    JOIN filtered f ON f.id = c.id
    ORDER BY c.rrf_score DESC
    LIMIT p_top_k;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 触发器
-- ============================================

-- ============================================
-- 交易系统表
-- ============================================

-- 交易计划状态
CREATE TYPE trading_plan_state AS ENUM (
    'DRAFT',
    'SIMULATION_PENDING',
    'SIMULATION_RUNNING',
    'SIMULATION_COMPLETED',
    'REVIEW_BY_TRADER',
    'PENDING_CHAIRMAN',
    'APPROVED',
    'LIVE_PENDING',
    'LIVE_EXECUTING',
    'LIVE_COMPLETED',
    'MONITORING',
    'CLOSED',
    'REJECTED',
    'CANCELLED'
);

-- 订单类型
CREATE TYPE order_type AS ENUM (
    'MARKET',
    'LIMIT',
    'STOP',
    'STOP_LIMIT'
);

-- 订单方向
CREATE TYPE order_side AS ENUM (
    'BUY',
    'SELL'
);

-- 订单状态
CREATE TYPE order_status AS ENUM (
    'PENDING',
    'SUBMITTED',
    'FILLED',
    'PARTIAL',
    'CANCELLED',
    'FAILED'
);

-- 交易计划表
CREATE TABLE trading_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 关联
    strategy_id UUID,
    experiment_id UUID REFERENCES experiments(id),
    cycle_id UUID REFERENCES research_cycles(id),
    
    -- 基本信息
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by VARCHAR(64) NOT NULL,  -- agent_id
    
    -- 交易目标
    target_portfolio JSONB DEFAULT '{}',
    current_portfolio JSONB DEFAULT '{}',
    
    -- 风险参数
    max_position_size DECIMAL(5, 4) DEFAULT 0.1,
    max_total_exposure DECIMAL(5, 4) DEFAULT 1.0,
    stop_loss_pct DECIMAL(5, 4) DEFAULT 0.05,
    take_profit_pct DECIMAL(5, 4),
    max_slippage_bps INT DEFAULT 50,
    
    -- 执行参数
    execution_style VARCHAR(32) DEFAULT 'twap',
    execution_window_minutes INT DEFAULT 60,
    
    -- 状态
    state trading_plan_state DEFAULT 'DRAFT',
    
    -- 模拟结果
    simulation_result JSONB,
    
    -- 审批信息
    trader_approval JSONB,
    chairman_approval JSONB,
    
    -- 执行结果
    execution_summary JSONB,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

-- 交易订单表
CREATE TABLE trading_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID REFERENCES trading_plans(id),
    
    -- 订单参数
    symbol VARCHAR(32) NOT NULL,
    side order_side NOT NULL,
    order_type order_type DEFAULT 'MARKET',
    quantity DECIMAL(24, 8) NOT NULL,
    price DECIMAL(24, 8),
    stop_price DECIMAL(24, 8),
    
    -- 执行参数
    execution_type VARCHAR(32) DEFAULT 'simulation',
    time_in_force VARCHAR(10) DEFAULT 'GTC',
    max_slippage_bps INT DEFAULT 50,
    
    -- 执行结果
    status order_status DEFAULT 'PENDING',
    filled_quantity DECIMAL(24, 8) DEFAULT 0,
    average_price DECIMAL(24, 8) DEFAULT 0,
    commission DECIMAL(20, 8) DEFAULT 0,
    slippage_bps DECIMAL(10, 4) DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    filled_at TIMESTAMPTZ,
    
    -- 交易所信息
    exchange VARCHAR(32),
    exchange_order_id VARCHAR(64),
    execution_log JSONB DEFAULT '[]'
);

-- 持仓表
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID REFERENCES trading_plans(id),
    
    -- 持仓信息
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- long, short
    quantity DECIMAL(24, 8) NOT NULL,
    entry_price DECIMAL(24, 8) NOT NULL,
    current_price DECIMAL(24, 8),
    
    -- 盈亏
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    unrealized_pnl_pct DECIMAL(10, 6) DEFAULT 0,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    
    -- 风控
    stop_loss DECIMAL(24, 8),
    take_profit DECIMAL(24, 8),
    
    -- 状态
    is_open BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- 交易执行日志
CREATE TABLE trade_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES trading_orders(id),
    plan_id UUID REFERENCES trading_plans(id),
    
    -- 执行信息
    symbol VARCHAR(32) NOT NULL,
    side order_side NOT NULL,
    quantity DECIMAL(24, 8) NOT NULL,
    price DECIMAL(24, 8) NOT NULL,
    
    -- 成本
    commission DECIMAL(20, 8) DEFAULT 0,
    slippage_bps DECIMAL(10, 4) DEFAULT 0,
    
    -- 时间
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 元数据
    exchange VARCHAR(32),
    exchange_trade_id VARCHAR(64),
    metadata JSONB DEFAULT '{}'
);

-- 索引
CREATE INDEX idx_trading_plans_state ON trading_plans(state);
CREATE INDEX idx_trading_plans_created_by ON trading_plans(created_by);
CREATE INDEX idx_trading_orders_plan ON trading_orders(plan_id);
CREATE INDEX idx_trading_orders_status ON trading_orders(status);
CREATE INDEX idx_positions_plan ON positions(plan_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_open ON positions(is_open) WHERE is_open = TRUE;
CREATE INDEX idx_trade_executions_plan ON trade_executions(plan_id);

-- ============================================
-- 触发器
-- ============================================

-- 更新时间戳触发器
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER research_cycles_updated_at
    BEFORE UPDATE ON research_cycles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER budget_accounts_updated_at
    BEFORE UPDATE ON budget_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 研究周期状态变更记录触发器
CREATE OR REPLACE FUNCTION log_cycle_state_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.current_state IS DISTINCT FROM NEW.current_state THEN
        INSERT INTO research_cycle_history (cycle_id, from_state, to_state)
        VALUES (NEW.id, OLD.current_state, NEW.current_state);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER research_cycles_state_log
    AFTER UPDATE ON research_cycles
    FOR EACH ROW EXECUTE FUNCTION log_cycle_state_change();

-- ============================================
-- LLM 使用追踪
-- ============================================

-- LLM 调用记录表
CREATE TABLE llm_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 调用者
    agent_id VARCHAR(64) REFERENCES agents(id),
    
    -- 模型信息
    model VARCHAR(64) NOT NULL,
    provider VARCHAR(32) DEFAULT 'antigravity',
    
    -- Token 使用
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    
    -- 成本计算 (USD, 精确到小数点后 6 位)
    input_cost DECIMAL(12, 6) DEFAULT 0,
    output_cost DECIMAL(12, 6) DEFAULT 0,
    total_cost DECIMAL(12, 6) GENERATED ALWAYS AS (input_cost + output_cost) STORED,
    
    -- 调用详情
    thinking_enabled BOOLEAN DEFAULT FALSE,
    request_type VARCHAR(32),  -- 'think', 'review', 'report', 'meeting', etc.
    
    -- 时间
    created_at TIMESTAMPTZ DEFAULT NOW(),
    latency_ms INTEGER,  -- 响应延迟（毫秒）
    
    -- 关联
    tool_call_id UUID REFERENCES tool_calls(id),
    meeting_id UUID REFERENCES meeting_requests(id)
);

-- 索引
CREATE INDEX idx_llm_usage_agent ON llm_usage(agent_id);
CREATE INDEX idx_llm_usage_model ON llm_usage(model);
CREATE INDEX idx_llm_usage_created ON llm_usage(created_at DESC);
CREATE INDEX idx_llm_usage_date ON llm_usage(DATE(created_at));

-- 每日汇总视图
CREATE VIEW llm_usage_daily AS
SELECT 
    DATE(created_at) as date,
    model,
    COUNT(*) as total_calls,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_tokens) as total_tokens,
    SUM(total_cost) as total_cost_usd,
    AVG(latency_ms) as avg_latency_ms
FROM llm_usage
GROUP BY DATE(created_at), model
ORDER BY date DESC, model;

-- 每个 Agent 汇总视图
CREATE VIEW llm_usage_by_agent AS
SELECT 
    agent_id,
    COUNT(*) as total_calls,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(total_cost) as total_cost_usd,
    SUM(CASE WHEN thinking_enabled THEN 1 ELSE 0 END) as thinking_calls
FROM llm_usage
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY agent_id
ORDER BY total_cost_usd DESC;

-- LLM 价格配置表
CREATE TABLE llm_pricing (
    id SERIAL PRIMARY KEY,
    model VARCHAR(64) NOT NULL UNIQUE,
    provider VARCHAR(32) NOT NULL,
    input_price_per_million DECIMAL(10, 4) NOT NULL,  -- $/M tokens
    output_price_per_million DECIMAL(10, 4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 初始化价格数据 (2026年1月)
INSERT INTO llm_pricing (model, provider, input_price_per_million, output_price_per_million) VALUES
    ('gpt-4o', 'openai', 2.50, 10.00),
    ('gpt-4o-mini', 'openai', 0.15, 0.60),
    ('claude-4.5-opus', 'anthropic', 5.00, 25.00),
    ('claude-4.5-sonnet', 'anthropic', 3.00, 15.00),
    ('claude-3.5-haiku', 'anthropic', 0.80, 4.00),
    ('deepseek-v3', 'deepseek', 0.27, 1.10),
    ('antigravity', 'antigravity', 1.00, 3.00)
ON CONFLICT (model) DO UPDATE SET
    input_price_per_million = EXCLUDED.input_price_per_million,
    output_price_per_million = EXCLUDED.output_price_per_million,
    updated_at = NOW();

-- ============================================
-- 初始数据（可选）
-- ============================================

-- 注释掉，由应用程序根据 agents.yaml 初始化
-- INSERT INTO agents (id, name, name_en, department, is_lead, capability_tier) VALUES
-- ('chief_of_staff', '办公室主任', 'Chief of Staff', 'board_office', true, 'reasoning'),
-- ...
