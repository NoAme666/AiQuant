'use client'

import { useState } from 'react'
import Link from 'next/link'
import useSWR from 'swr'
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
  MessageSquare,
  Lightbulb,
  BarChart3,
  ExternalLink,
  BookOpen,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface AgentMessage {
  agent_id: string
  agent_name: string
  message: string
  timestamp: string
  type: 'comment' | 'question' | 'suggestion' | 'approval' | 'rejection'
}

interface Reference {
  id: string
  title: string
  source: string
  url?: string
  type: 'paper' | 'data' | 'strategy' | 'meeting'
  cited_by: string
}

interface ResearchCycle {
  id: string
  name: string
  strategy_type: string
  state: string
  progress: number
  owner: string
  team: string
  created_at: string
  updated_at?: string
  metrics?: {
    sharpe?: number
    max_dd?: number
    win_rate?: number
    calmar?: number
  }
  suggestions?: string[]
  discussion: AgentMessage[]
  references: Reference[]
  team_evaluation?: {
    score: number
    verdict: string
    improvements: string[]
  }
}

// 研究周期数据从 API 获取

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

function MessageTypeIcon({ type }: { type: AgentMessage['type'] }) {
  switch (type) {
    case 'suggestion':
      return <Lightbulb className="w-3 h-3 text-yellow-400" />
    case 'question':
      return <AlertTriangle className="w-3 h-3 text-orange-400" />
    case 'approval':
      return <CheckCircle className="w-3 h-3 text-accent-success" />
    case 'rejection':
      return <XCircle className="w-3 h-3 text-accent-danger" />
    default:
      return <MessageSquare className="w-3 h-3 text-gray-400" />
  }
}

function ReferenceTypeIcon({ type }: { type: Reference['type'] }) {
  switch (type) {
    case 'paper':
      return <BookOpen className="w-3 h-3 text-blue-400" />
    case 'data':
      return <BarChart3 className="w-3 h-3 text-green-400" />
    case 'strategy':
      return <FlaskConical className="w-3 h-3 text-purple-400" />
    case 'meeting':
      return <MessageSquare className="w-3 h-3 text-orange-400" />
    default:
      return <ExternalLink className="w-3 h-3 text-gray-400" />
  }
}

function CycleDetailCard({ cycle }: { cycle: ResearchCycle }) {
  const [expanded, setExpanded] = useState(false)
  const state = stateConfig[cycle.state] || stateConfig['IDEA_INTAKE']

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-mono">{cycle.id}</span>
            <span className={`badge badge-neutral text-[10px] ${state.color}`}>{state.label}</span>
          </div>
          <h3 className="text-lg font-medium text-gray-100 mt-1">{cycle.name}</h3>
          <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
            <span>{cycle.strategy_type}</span>
            <span>•</span>
            <span>{cycle.team}</span>
            <span>•</span>
            <span>负责人: {cycle.owner}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">{cycle.progress}%</div>
          <div className="text-xs text-gray-500">{cycle.updated_at}</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="h-2 bg-terminal-muted rounded-full overflow-hidden">
          <div
            className={`h-full ${state.bgColor} transition-all`}
            style={{ width: `${cycle.progress}%` }}
          />
        </div>
      </div>

      {/* Metrics */}
      {cycle.metrics && (
        <div className="grid grid-cols-4 gap-4 mb-4 py-3 border-y border-terminal-border/50">
          <div className="text-center">
            <div className="text-lg font-bold text-gray-200">{cycle.metrics.sharpe?.toFixed(2)}</div>
            <div className="text-[10px] text-gray-500">Sharpe</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-accent-danger">{(cycle.metrics.max_dd! * 100).toFixed(1)}%</div>
            <div className="text-[10px] text-gray-500">Max DD</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-gray-200">{(cycle.metrics.win_rate! * 100).toFixed(0)}%</div>
            <div className="text-[10px] text-gray-500">胜率</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-gray-200">{cycle.metrics.calmar?.toFixed(2)}</div>
            <div className="text-[10px] text-gray-500">Calmar</div>
          </div>
        </div>
      )}

      {/* Team Evaluation */}
      {cycle.team_evaluation && (
        <div className="mb-4 p-3 bg-terminal-muted/30 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-300">团队评价</span>
            <div className="flex items-center gap-2">
              <span className={`text-lg font-bold ${
                cycle.team_evaluation.score >= 80 ? 'text-accent-success' :
                cycle.team_evaluation.score >= 60 ? 'text-yellow-400' :
                'text-accent-danger'
              }`}>{cycle.team_evaluation.score}</span>
              <span className={`badge ${
                cycle.team_evaluation.verdict === '强烈推荐' ? 'badge-success' :
                cycle.team_evaluation.verdict === '推荐' ? 'badge-info' :
                'badge-neutral'
              } text-[10px]`}>{cycle.team_evaluation.verdict}</span>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            <span className="font-medium">改进建议:</span>
            <ul className="list-disc list-inside mt-1">
              {cycle.team_evaluation.improvements.map((imp, i) => (
                <li key={i}>{imp}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Agent Discussion */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-gray-300 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Agent 交流记录
          </h4>
          <span className="text-xs text-gray-500">{cycle.discussion.length} 条</span>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {cycle.discussion.map((msg, idx) => (
            <div key={idx} className="flex gap-3 p-2 bg-terminal-muted/20 rounded">
              <div className="shrink-0 mt-0.5">
                <MessageTypeIcon type={msg.type} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Link href={`/chat/${msg.agent_id}`} className="text-xs font-medium text-accent-primary hover:underline">
                    {msg.agent_name}
                  </Link>
                  <span className="text-[10px] text-gray-600">{msg.timestamp}</span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">{msg.message}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* References */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-gray-300 flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            引用来源
          </h4>
          <span className="text-xs text-gray-500">{cycle.references.length} 条</span>
        </div>
        <div className="space-y-1">
          {cycle.references.map((ref) => (
            <div key={ref.id} className="flex items-center justify-between py-1.5 px-2 bg-terminal-muted/20 rounded">
              <div className="flex items-center gap-2">
                <ReferenceTypeIcon type={ref.type} />
                <span className="text-xs text-gray-300">{ref.title}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-500">{ref.source}</span>
                <span className="text-[10px] text-gray-600">by {ref.cited_by}</span>
                {ref.url && (
                  <a href={ref.url} className="text-accent-primary hover:underline">
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 mt-4 pt-4 border-t border-terminal-border/50">
        <Link href={`/backtest/${cycle.id}`} className="btn btn-secondary btn-sm">
          <BarChart3 className="w-4 h-4 mr-1" />
          查看回测
        </Link>
        {cycle.state === 'IC_REVIEW' && (
          <button className="btn btn-primary btn-sm">
            审批
          </button>
        )}
      </div>
    </div>
  )
}

export default function ResearchPage() {
  const [filter, setFilter] = useState('all')
  
  // 从 API 获取真实数据
  const { data: cyclesData } = useSWR(`${API_BASE}/api/v2/research-cycles`, fetcher, { refreshInterval: 5000 })
  const cycles: ResearchCycle[] = cyclesData?.cycles || []

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
          <p className="page-subtitle">策略研究周期管理与 Agent 协作</p>
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

      {/* Cycle Details */}
      <div className="space-y-6">
        {filteredCycles.map((cycle) => (
          <CycleDetailCard key={cycle.id} cycle={cycle} />
        ))}
      </div>
    </div>
  )
}
