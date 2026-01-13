-- AI Quant Company - 数据库 Schema
-- PostgreSQL 15+

-- ============================================
-- 扩展
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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
    'TEAM_SYNTHESIS_MEMO'
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
-- 初始数据（可选）
-- ============================================

-- 注释掉，由应用程序根据 agents.yaml 初始化
-- INSERT INTO agents (id, name, name_en, department, is_lead, capability_tier) VALUES
-- ('chief_of_staff', '办公室主任', 'Chief of Staff', 'board_office', true, 'reasoning'),
-- ...
