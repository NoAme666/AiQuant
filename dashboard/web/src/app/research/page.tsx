'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  FlaskConical,
  Plus,
  Filter,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  User,
  ArrowRight,
} from 'lucide-react'

interface ResearchCycle {
  id: string
  name: string
  strategy_type: string
  state: string
  progress: number
  owner: string
  team: string
  created_at: string
  updated_at: string
  metrics?: {
    sharpe?: number
    max_dd?: number
    win_rate?: number
  }
}

const cycles: ResearchCycle[] = [
  {
    id: 'RC-2026-001',
    name: 'BTC 动量突破策略',
    strategy_type: 'Momentum',
    state: 'RISK_SKEPTIC_GATE',
    progress: 75,
    owner: 'alpha_a_lead',
    team: 'Alpha A',
    created_at: '2026-01-10',
    updated_at: '2026-01-14',
    metrics: { sharpe: 1.85, max_dd: -0.12, win_rate: 0.58 },
  },
  {
    id: 'RC-2026-002',
    name: 'ETH 均值回归',
    strategy_type: 'Mean Reversion',
    state: 'BACKTEST_GATE',
    progress: 45,
    owner: 'alpha_a_researcher_1',
    team: 'Alpha A',
    created_at: '2026-01-12',
    updated_at: '2026-01-14',
    metrics: { sharpe: 1.42, max_dd: -0.08, win_rate: 0.62 },
  },
  {
    id: 'RC-2026-003',
    name: '跨市场资金流套利',
    strategy_type: 'Arbitrage',
    state: 'DATA_GATE',
    progress: 20,
    owner: 'alpha_b_lead',
    team: 'Alpha B',
    created_at: '2026-01-13',
    updated_at: '2026-01-14',
  },
  {
    id: 'RC-2026-004',
    name: '波动率策略 v2',
    strategy_type: 'Volatility',
    state: 'IC_REVIEW',
    progress: 85,
    owner: 'alpha_b_researcher_1',
    team: 'Alpha B',
    created_at: '2026-01-08',
    updated_at: '2026-01-13',
    metrics: { sharpe: 2.1, max_dd: -0.15, win_rate: 0.55 },
  },
  {
    id: 'RC-2025-089',
    name: '趋势跟踪组合',
    strategy_type: 'Trend Following',
    state: 'ARCHIVE',
    progress: 100,
    owner: 'alpha_a_lead',
    team: 'Alpha A',
    created_at: '2025-12-15',
    updated_at: '2026-01-05',
    metrics: { sharpe: 1.65, max_dd: -0.18, win_rate: 0.52 },
  },
]

const stateConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  'IDEA_INTAKE': { label: '构思中', color: 'text-gray-400', bgColor: 'bg-gray-500' },
  'DATA_GATE': { label: '数据闸门', color: 'text-blue-400', bgColor: 'bg-blue-500' },
  'BACKTEST_GATE': { label: '回测闸门', color: 'text-purple-400', bgColor: 'bg-purple-500' },
  'ROBUSTNESS_GATE': { label: '鲁棒性闸门', color: 'text-indigo-400', bgColor: 'bg-indigo-500' },
  'RISK_SKEPTIC_GATE': { label: '风控审核', color: 'text-orange-400', bgColor: 'bg-orange-500' },
  'IC_REVIEW': { label: '投委会审议', color: 'text-yellow-400', bgColor: 'bg-yellow-500' },
  'BOARD_PACK': { label: '董事会材料', color: 'text-accent-primary', bgColor: 'bg-accent-primary' },
  'BOARD_DECISION': { label: '董事会决策', color: 'text-accent-primary', bgColor: 'bg-accent-primary' },
  'ARCHIVE': { label: '已归档', color: 'text-gray-500', bgColor: 'bg-gray-600' },
}

function CycleCard({ cycle }: { cycle: ResearchCycle }) {
  const state = stateConfig[cycle.state] || stateConfig['IDEA_INTAKE']

  return (
    <div className="card-hover p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-mono">{cycle.id}</span>
            <span className={`badge badge-neutral text-[10px] ${state.color}`}>{state.label}</span>
          </div>
          <h3 className="text-base font-medium text-gray-100 mt-1">{cycle.name}</h3>
          <div className="text-xs text-gray-500 mt-0.5">{cycle.strategy_type}</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-gray-500">进度</span>
          <span className="text-gray-400">{cycle.progress}%</span>
        </div>
        <div className="h-1.5 bg-terminal-muted rounded-full overflow-hidden">
          <div
            className={`h-full ${state.bgColor} transition-all`}
            style={{ width: `${cycle.progress}%` }}
          />
        </div>
      </div>

      {/* Metrics */}
      {cycle.metrics && (
        <div className="grid grid-cols-3 gap-2 mb-3 py-2 border-t border-terminal-border/50">
          <div className="text-center">
            <div className="text-sm font-medium text-gray-200">{cycle.metrics.sharpe?.toFixed(2)}</div>
            <div className="text-[10px] text-gray-500">Sharpe</div>
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-accent-danger">{(cycle.metrics.max_dd! * 100).toFixed(1)}%</div>
            <div className="text-[10px] text-gray-500">Max DD</div>
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-gray-200">{(cycle.metrics.win_rate! * 100).toFixed(0)}%</div>
            <div className="text-[10px] text-gray-500">胜率</div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-terminal-border/50">
        <div className="flex items-center gap-2">
          <User className="w-3 h-3 text-gray-500" />
          <span className="text-xs text-gray-400">{cycle.team}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Clock className="w-3 h-3" />
          {cycle.updated_at}
        </div>
      </div>
    </div>
  )
}

export default function ResearchPage() {
  const [filter, setFilter] = useState('all')

  const filteredCycles = filter === 'all'
    ? cycles
    : cycles.filter((c) => c.state !== 'ARCHIVE')

  const stats = {
    total: cycles.length,
    active: cycles.filter((c) => c.state !== 'ARCHIVE').length,
    pending_review: cycles.filter((c) => ['IC_REVIEW', 'RISK_SKEPTIC_GATE'].includes(c.state)).length,
  }

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">研究中心</h1>
          <p className="page-subtitle">策略研究周期管理与追踪</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary btn-sm">
            <Filter className="w-4 h-4 mr-2" />
            筛选
          </button>
          <button className="btn btn-primary btn-sm">
            <Plus className="w-4 h-4 mr-2" />
            新建研究周期
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="text-2xl font-bold text-gray-100">{stats.total}</div>
          <div className="text-sm text-gray-500">总研究周期</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-accent-primary">{stats.active}</div>
          <div className="text-sm text-gray-500">进行中</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-orange-400">{stats.pending_review}</div>
          <div className="text-sm text-gray-500">待审核</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-gray-400">{stats.total - stats.active}</div>
          <div className="text-sm text-gray-500">已归档</div>
        </div>
      </div>

      {/* Pipeline Stages */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">研究流水线</h2>
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {Object.entries(stateConfig).filter(([key]) => key !== 'ARCHIVE').map(([key, config], idx) => (
            <div key={key} className="flex items-center">
              <div className={`px-3 py-1.5 rounded-lg text-xs ${config.bgColor}/20 ${config.color} whitespace-nowrap`}>
                {config.label}
                <span className="ml-1 opacity-60">
                  ({cycles.filter((c) => c.state === key).length})
                </span>
              </div>
              {idx < Object.keys(stateConfig).length - 2 && (
                <ChevronRight className="w-4 h-4 text-gray-600 mx-1" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-terminal-border">
        <button
          onClick={() => setFilter('all')}
          className={`pb-3 px-1 text-sm border-b-2 transition-colors ${
            filter === 'all'
              ? 'border-accent-primary text-accent-primary'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          全部 ({cycles.length})
        </button>
        <button
          onClick={() => setFilter('active')}
          className={`pb-3 px-1 text-sm border-b-2 transition-colors ${
            filter === 'active'
              ? 'border-accent-primary text-accent-primary'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          进行中 ({stats.active})
        </button>
      </div>

      {/* Cycle Grid */}
      <div className="grid grid-cols-3 gap-4">
        {filteredCycles.map((cycle) => (
          <CycleCard key={cycle.id} cycle={cycle} />
        ))}
      </div>
    </div>
  )
}
