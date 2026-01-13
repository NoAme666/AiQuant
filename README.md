# AI Quant Company

> Multi-Agent 量化公司仿真与自动研究系统

## 项目概述

AI Quant Company 是一个以 Multi-Agent AI 复刻真实量化基金组织与治理流程的系统。它由多个"岗位 Agent"组成（研究、数据、回测、风控、反对派、投委会、董事会办公室），在严格的制度约束下，自动完成量化策略的全流程研究。

### 核心能力

- **研究闭环**: Research Agents 独立提出策略假设、信号定义、交易规则
- **数据闭环**: Data Agents 接入市场数据、清洗、对齐、版本化
- **回测闭环**: Backtest Agents 运行可复现回测，输出标准化产物
- **成本/鲁棒性闭环**: 交易成本敏感性分析、样本外/Walk-Forward 验证
- **审查/否决闭环**: Data Auditor 和 CRO 一票否决权
- **报告闭环**: 自动生成董事会报告 + 技术研究报告
- **治理闭环**: 董事长 Dashboard 全程可视化监控

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Dashboard (Next.js)                          │
│   Lobby │ Org Chart │ Pipeline │ Chat │ Meetings │ Audit        │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│              REST API │ WebSocket Events                         │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestrator Core                              │
│  StateMachine │ Router │ Meeting │ Budget │ Reputation │ Audit  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Runtime                                 │
│  Board Office │ Investment Committee │ Research │ Data │ Risk   │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
┌─────────────────────┐             ┌─────────────────────┐
│    Data Layer       │             │   Backtest Engine   │
│ Crypto Providers    │             │   Core │ TCost      │
│ Feature Store       │             │   Robustness        │
└─────────────────────┘             └─────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       Storage                                    │
│              PostgreSQL │ Parquet Files                          │
└─────────────────────────────────────────────────────────────────┘
```

## 组织架构

| 部门 | 角色 | 职责 |
|------|------|------|
| **Board Office** | Chief of Staff | 会议初审、流程控制、周报 |
| | Audit & Compliance | 合规审计、可复现性检查 |
| **Investment Committee** | CIO | 跨部门汇总、投委建议 |
| | PM | 组合视角评估 |
| **Research Guild** | Head of Research | 研究路线图、预算分配 |
| | Alpha Team A/B | 策略研究（赛马竞争） |
| **Data Guild** | Data Engineering | 数据接入、清洗、版本化 |
| | Data Quality Auditor | 数据闸门（一票否决） |
| **Backtest Guild** | Backtest Engineering | 可复现实验 |
| | Transaction Cost | 成本敏感性分析 |
| | Robustness Lab | 鲁棒性实验 |
| **Risk Guild** | CRO Risk Manager | 风险闸门（一票否决） |
| | Skeptic | 强制质疑、退回补实验 |
| | Black Swan | 极端情景模拟 |

## 研究流程 (ResearchCycle)

```
IDEA_INTAKE → DATA_GATE → BACKTEST_GATE → ROBUSTNESS_GATE 
    → RISK_SKEPTIC_GATE → IC_REVIEW → BOARD_PACK → BOARD_DECISION → ARCHIVE
```

任何闸门失败 → 自动退回指定节点并带"补实验工单"

## 快速开始

### 环境要求

- Python >= 3.11
- PostgreSQL >= 15
- Node.js >= 20 (Dashboard)

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd ai-quant-company

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API keys
```

### 配置

1. 复制 `.env.example` 为 `.env`
2. 填入必要的 API Keys:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `GOOGLE_API_KEY`
   - `DATABASE_URL`

### 运行

```bash
# 启动后端服务
uvicorn dashboard.api.main:app --reload

# 启动前端 (另一个终端)
cd dashboard/web
npm install
npm run dev
```

## 目录结构

```
ai-quant-company/
├── configs/                 # 配置文件
│   ├── agents.yaml         # Agent 岗位定义
│   ├── models.yaml         # LLM 模型映射
│   ├── permissions.yaml    # 权限矩阵
│   ├── risk_limits.yaml    # 风险阈值
│   ├── scoring_weights.yaml # 声誉评分
│   └── budget_policy.yaml  # 预算策略
├── orchestrator/           # 编排器核心
│   ├── state_machine.py    # 状态机
│   ├── router.py           # 消息路由
│   ├── meeting.py          # 会议系统
│   ├── budget.py           # 预算管理
│   ├── reputation.py       # 声誉系统
│   └── audit.py            # 审计日志
├── agents/                 # Agent 实现
│   ├── base.py             # 基类
│   ├── leads/              # Lead 角色
│   ├── research/           # 研究团队
│   ├── data/               # 数据团队
│   ├── backtest/           # 回测团队
│   ├── risk/               # 风控团队
│   └── board/              # 董事会办公室
├── data/                   # 数据层
│   ├── providers/          # 数据源适配器
│   ├── pipeline.py         # 数据流水线
│   ├── quality_checks.py   # 质量检查
│   └── versioning.py       # 版本管理
├── backtest/               # 回测引擎
│   ├── engine.py           # 核心引擎
│   ├── metrics.py          # 指标计算
│   ├── tcost.py            # 交易成本
│   └── robustness.py       # 鲁棒性实验
├── reports/                # 报告生成
│   ├── templates/          # Jinja2 模板
│   └── generator.py        # 报告生成器
├── storage/                # 存储层
│   ├── db.py               # 数据库连接
│   ├── schema.sql          # 表结构
│   └── artifacts.py        # 产物管理
└── dashboard/              # Dashboard
    ├── api/                # FastAPI 后端
    └── web/                # Next.js 前端
```

## 核心约束（三铁律）

1. **资源稀缺**: Compute Points 预算限制回测与参数搜索
2. **可复现**: ExperimentID + DataVersionHash + CodeCommit + ConfigHash
3. **制衡机制**: 反对派 + 一票否决

## 开发路线

- [x] Phase 0: 核心骨架 (配置 + 状态机 + 数据库 + 最小 Dashboard)
- [ ] Phase 1: 闭环验证 (数据接入 + 回测 + 报告 + Agent Runtime)
- [ ] Phase 2: 增强 (重声誉 + PDF 报告 + 更多数据源)

## License

MIT
