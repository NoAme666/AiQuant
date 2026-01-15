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

#### LLM 配置 (SiliconFlow - 推荐)

使用 [SiliconFlow](https://siliconflow.cn) 作为 LLM 提供商，支持国产模型：

```bash
SILICONFLOW_API_KEY=your-api-key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# 模型配置
DEFAULT_MODEL=Qwen/Qwen2.5-32B-Instruct      # 通用对话
THINKING_MODEL=Qwen/QwQ-32B                   # 深度推理 (用于需要 thinking 的 Agent)
CODING_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct  # 代码任务
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B       # 向量嵌入
```

**推荐模型** (Qwen3 + GLM 4.5+ 系列):

| 模型 | 价格 (¥/M tokens) | 适用场景 | 使用的 Agent |
|------|------------------|---------|-------------|
| `Qwen/QwQ-32B` | ¥1.26 | **深度推理、决策** | CIO, CRO, PM, CGO, Data Auditor |
| `THUDM/GLM-Z1-32B-0414` | ¥2.0 | **推理增强、质疑** | Skeptic, Alpha B Lead |
| `Qwen/Qwen3-30B-A3B-Thinking` | ¥1.26 | **思考链推理** | Alpha A Lead, Black Swan |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | ¥1.26 | **代码工程** | 数据工程、回测、交易执行 |
| `Qwen/Qwen3-32B` | ¥1.26 | **通用推理** | Chief of Staff, 情报总监等 |
| `THUDM/GLM-4-32B-0414` | ¥2.0 | **GLM 通用** | News Analyst |
| `Qwen/Qwen3-14B` | ¥0.7 | **轻量研究** | Alpha A 研究员 |
| `THUDM/GLM-4-9B-0414` | ¥0 (免费) | **免费测试** | Alpha B 研究员 |

**自动模型选择**: 系统会根据 Agent 角色自动选择最优模型，无需手动配置。

**自动 API 端点选择**: 首次调用时自动 ping 测试国内站/国际站，选择延迟最低的端点。

#### 其他配置

```bash
DATABASE_URL=postgresql+asyncpg://...
OKX_API_KEY=...                    # 交易所 API
OKX_API_SECRET=...
OKX_PASSPHRASE=...
```

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
- [ ] Phase 3: RDAgent 集成 (自动因子挖掘 + 模型优化)

## RDAgent 集成方案

[RD-Agent](https://github.com/microsoft/RD-Agent) 是微软研究院的开源自动化研发框架，可以显著增强我们的研究能力。

### 为什么要集成

| 功能 | 当前系统 | + RDAgent |
|------|---------|-----------|
| 因子发现 | 研究员手动提出假设 | **自动生成并验证因子假设** |
| 回测循环 | 人工触发回测 | **自动迭代: 假设→代码→回测→反馈** |
| 模型优化 | 固定模型架构 | **因子+模型联合优化** |
| 成本 | 依赖 Agent 对话 | **单次实验 <$10** |

### 集成架构

```
┌─────────────────────────────────────────────────────────┐
│                   AI Quant Company                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ CIO / PM    │  │ Risk Guild  │  │ Board       │      │
│  │ (决策审批)   │  │ (风险审查)   │  │ (最终批准)   │      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
│         │                │                │              │
│  ┌──────┴────────────────┴────────────────┴──────┐      │
│  │              Research Guild                    │      │
│  │  ┌─────────────────────────────────────────┐  │      │
│  │  │           RD-Agent (研究员)              │  │      │
│  │  │  ┌───────────┐    ┌───────────┐         │  │      │
│  │  │  │ Factor    │    │ Model     │         │  │      │
│  │  │  │ Mining    │◄──►│ Evolution │         │  │      │
│  │  │  └─────┬─────┘    └─────┬─────┘         │  │      │
│  │  │        │                │               │  │      │
│  │  │  ┌─────┴────────────────┴─────┐         │  │      │
│  │  │  │    Co-STEER (代码生成)      │         │  │      │
│  │  │  └─────────────┬───────────────┘         │  │      │
│  │  └────────────────┼────────────────────────┘  │      │
│  └───────────────────┼───────────────────────────┘      │
│                      │                                   │
│  ┌───────────────────┴───────────────────┐              │
│  │        Qlib (回测引擎)                 │              │
│  │  Data Pipeline │ Backtest │ Metrics    │              │
│  └────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 集成步骤

1. **安装 RDAgent 和 Qlib**
   ```bash
   pip install rdagent qlib
   ```

2. **创建 RDAgent 研究员 Agent** (`agents/research/rdagent_researcher.py`)
   - 继承 `BaseAgent`
   - 封装 `rdagent fin_factor` 和 `rdagent fin_model` 命令
   - 将 RDAgent 的输出转换为公司标准的 `ResearchCycleMemo`

3. **集成到研究流程**
   - Alpha Team A/B 可以调用 RDAgent 自动生成因子候选
   - 生成的因子仍需通过 Data Auditor 审核
   - 回测结果仍需通过 CRO/Skeptic 审查

4. **数据对接**
   - 使用 Qlib 的数据格式
   - 复用现有的 OKX/Binance 数据管道

### 示例用法

```python
# RDAgent 研究员自动因子挖掘
class RDAgentResearcher(BaseAgent):
    async def auto_factor_mining(self, hypothesis: str):
        """自动因子挖掘"""
        # 1. 调用 RDAgent 生成因子
        result = await self.run_rdagent("fin_factor", hypothesis)
        
        # 2. 转换为公司标准格式
        memo = self.create_research_memo(result)
        
        # 3. 提交给 Data Auditor 审核
        await self.submit_to_data_gate(memo)
        
        return memo
```

### 预期收益

- **研究效率提升 10x**: 自动化假设生成和验证
- **成本降低**: 单次完整实验 <$10 (vs 人工对话成本)
- **质量保证**: 仍保留人工审核流程 (Data Auditor + CRO)
- **可复现性**: RDAgent 的 ExperimentID 与公司系统对接

## License

MIT
