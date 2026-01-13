'use client'

import { useState } from 'react'
import Link from 'next/link'
import { 
  ArrowLeft, 
  GitBranch, 
  ChevronRight,
  Clock,
  User,
  AlertCircle,
  CheckCircle,
  XCircle,
  Loader2
} from 'lucide-react'

// 状态配置
const STATES = [
  { id: 'IDEA_INTAKE', name: '策略构思', color: 'text-gray-400', bgColor: 'bg-gray-400/20' },
  { id: 'DATA_GATE', name: '数据闸门', color: 'text-blue-400', bgColor: 'bg-blue-400/20' },
  { id: 'BACKTEST_GATE', name: '回测闸门', color: 'text-purple-400', bgColor: 'bg-purple-400/20' },
  { id: 'ROBUSTNESS_GATE', name: '鲁棒性闸门', color: 'text-indigo-400', bgColor: 'bg-indigo-400/20' },
  { id: 'RISK_SKEPTIC_GATE', name: '风控/质疑闸门', color: 'text-orange-400', bgColor: 'bg-orange-400/20' },
  { id: 'IC_REVIEW', name: '投委会审议', color: 'text-yellow-400', bgColor: 'bg-yellow-400/20' },
  { id: 'BOARD_PACK', name: '董事会材料', color: 'text-accent-primary', bgColor: 'bg-accent-primary/20' },
  { id: 'BOARD_DECISION', name: '董事会决策', color: 'text-accent-primary', bgColor: 'bg-accent-primary/20' },
  { id: 'ARCHIVE', name: '归档', color: 'text-gray-500', bgColor: 'bg-gray-500/20' },
]

// 模拟数据
const cycles = [
  {
    id: 'cycle-001',
    name: 'BTC 动量策略 v1',
    description: '基于价格动量的趋势跟随策略',
    currentState: 'ROBUSTNESS_GATE',
    team: 'alpha_a',
    proposer: 'Alpha A Lead',
    createdAt: '2024-01-10',
    updatedAt: '2024-01-15',
    experiments: 5,
    gatesPassed: ['IDEA_INTAKE', 'DATA_GATE', 'BACKTEST_GATE'],
  },
  {
    id: 'cycle-002',
    name: 'ETH 均值回归',
    description: 'ETH/USDT 均值回归策略',
    currentState: 'DATA_GATE',
    team: 'alpha_b',
    proposer: 'Alpha B Lead',
    createdAt: '2024-01-12',
    updatedAt: '2024-01-14',
    experiments: 2,
    gatesPassed: ['IDEA_INTAKE'],
  },
  {
    id: 'cycle-003',
    name: 'SOL 波动率策略',
    description: '基于隐含波动率的交易策略',
    currentState: 'BOARD_DECISION',
    team: 'alpha_a',
    proposer: 'Alpha A Lead',
    createdAt: '2024-01-05',
    updatedAt: '2024-01-14',
    experiments: 12,
    gatesPassed: ['IDEA_INTAKE', 'DATA_GATE', 'BACKTEST_GATE', 'ROBUSTNESS_GATE', 'RISK_SKEPTIC_GATE', 'IC_REVIEW', 'BOARD_PACK'],
  },
]

// 状态图标
function StateIcon({ state, passed }: { state: string; passed: boolean }) {
  if (passed) {
    return <CheckCircle className="w-4 h-4 text-accent-success" />
  }
  return <div className="w-4 h-4 rounded-full border-2 border-terminal-border" />
}

// 周期卡片
function CycleCard({ cycle }: { cycle: typeof cycles[0] }) {
  const currentStateConfig = STATES.find(s => s.id === cycle.currentState)
  const currentStateIndex = STATES.findIndex(s => s.id === cycle.currentState)
  
  return (
    <div className="card-hover">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-100">{cycle.name}</h3>
          <p className="text-sm text-gray-400">{cycle.description}</p>
        </div>
        <span className={`badge ${currentStateConfig?.bgColor} ${currentStateConfig?.color}`}>
          {currentStateConfig?.name}
        </span>
      </div>
      
      {/* 进度条 */}
      <div className="flex items-center gap-1 mb-4">
        {STATES.slice(0, -1).map((state, i) => {
          const isPassed = cycle.gatesPassed.includes(state.id)
          const isCurrent = state.id === cycle.currentState
          
          return (
            <div key={state.id} className="flex-1 flex items-center">
              <div 
                className={`h-2 flex-1 rounded-full ${
                  isPassed ? 'bg-accent-success' : 
                  isCurrent ? 'bg-accent-primary' : 
                  'bg-terminal-border'
                }`}
              />
              {i < STATES.length - 2 && (
                <div className={`w-2 h-2 rounded-full mx-0.5 ${
                  isPassed ? 'bg-accent-success' : 
                  isCurrent ? 'bg-accent-primary' : 
                  'bg-terminal-border'
                }`} />
              )}
            </div>
          )
        })}
      </div>
      
      {/* 元信息 */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4 text-gray-400">
          <span className="flex items-center gap-1">
            <User className="w-4 h-4" />
            {cycle.proposer}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {cycle.updatedAt}
          </span>
        </div>
        <span className="text-gray-500">{cycle.experiments} 个实验</span>
      </div>
      
      <Link 
        href={`/pipeline/${cycle.id}`}
        className="mt-4 flex items-center justify-center gap-2 text-accent-primary hover:underline"
      >
        查看详情
        <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  )
}

export default function PipelinePage() {
  const [filter, setFilter] = useState<string>('all')
  
  const filteredCycles = filter === 'all' 
    ? cycles 
    : cycles.filter(c => c.currentState === filter)

  return (
    <div className="min-h-screen p-6">
      {/* 顶部导航 */}
      <header className="flex items-center gap-4 mb-8">
        <Link href="/" className="p-2 rounded-lg hover:bg-terminal-muted transition-colors">
          <ArrowLeft className="w-5 h-5 text-gray-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
            <GitBranch className="w-6 h-6 text-accent-primary" />
            研究流水线
          </h1>
          <p className="text-gray-400">跟踪策略研究进度</p>
        </div>
      </header>

      {/* 状态筛选 */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
            filter === 'all' 
              ? 'bg-accent-primary text-terminal-bg' 
              : 'bg-terminal-muted text-gray-300 hover:bg-terminal-border'
          }`}
        >
          全部 ({cycles.length})
        </button>
        {STATES.slice(0, -1).map(state => {
          const count = cycles.filter(c => c.currentState === state.id).length
          if (count === 0) return null
          
          return (
            <button
              key={state.id}
              onClick={() => setFilter(state.id)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                filter === state.id 
                  ? `${state.bgColor} ${state.color}` 
                  : 'bg-terminal-muted text-gray-300 hover:bg-terminal-border'
              }`}
            >
              {state.name} ({count})
            </button>
          )
        })}
      </div>

      {/* 流水线视图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredCycles.map(cycle => (
          <CycleCard key={cycle.id} cycle={cycle} />
        ))}
      </div>

      {filteredCycles.length === 0 && (
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-400">没有符合条件的研究周期</p>
        </div>
      )}

      {/* 状态图例 */}
      <div className="mt-8 card">
        <h3 className="text-sm font-medium text-gray-300 mb-4">状态说明</h3>
        <div className="flex flex-wrap gap-4">
          {STATES.map(state => (
            <div key={state.id} className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${state.bgColor}`} />
              <span className={`text-sm ${state.color}`}>{state.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
