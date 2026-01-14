'use client'

import { useState } from 'react'
import {
  CheckSquare,
  XCircle,
  CheckCircle,
  Clock,
  AlertTriangle,
  User,
  TrendingUp,
  Users,
  FileText,
  MessageSquare,
} from 'lucide-react'

interface ApprovalItem {
  id: string
  type: 'trading' | 'hiring' | 'strategy' | 'meeting' | 'experiment'
  title: string
  description: string
  requester: string
  department: string
  urgency: 'normal' | 'high' | 'critical'
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  expires_at?: string
  data?: Record<string, any>
}

const approvalItems: ApprovalItem[] = [
  {
    id: 'AP-001',
    type: 'trading',
    title: 'BTC/USDT 做多交易计划',
    description: '基于动量策略信号，建议建仓 BTC 30% 仓位。预计持仓周期 2-4 周。',
    requester: 'head_trader',
    department: 'Trading Guild',
    urgency: 'high',
    status: 'pending',
    created_at: '2026-01-14 14:20',
    expires_at: '2026-01-15 14:20',
    data: {
      symbol: 'BTC/USDT',
      target_weight: 0.3,
      stop_loss: -0.05,
      max_slippage: 50,
    },
  },
  {
    id: 'AP-002',
    type: 'hiring',
    title: '新增 ML Alpha 研究员',
    description: '当前研究团队负载较高，建议招聘一名专注机器学习策略的研究员。',
    requester: 'cpo',
    department: 'Meta-Governance',
    urgency: 'normal',
    status: 'pending',
    created_at: '2026-01-14 10:00',
    data: {
      role: 'ML Alpha Researcher',
      budget_impact: 5000,
      trial_period: '30 days',
    },
  },
  {
    id: 'AP-003',
    type: 'strategy',
    title: '波动率策略 v2 上线',
    description: '策略已通过所有闸门审核，Sharpe 2.1，Max DD -15%，建议批准上线。',
    requester: 'cio',
    department: 'Investment Committee',
    urgency: 'normal',
    status: 'pending',
    created_at: '2026-01-13 17:00',
    data: {
      sharpe: 2.1,
      max_dd: -0.15,
      initial_allocation: 0.1,
    },
  },
  {
    id: 'AP-004',
    type: 'trading',
    title: 'ETH 加仓计划',
    description: '均值回归信号触发，建议增加 ETH 持仓至 25%。',
    requester: 'head_trader',
    department: 'Trading Guild',
    urgency: 'high',
    status: 'approved',
    created_at: '2026-01-13 11:00',
    data: {
      symbol: 'ETH/USDT',
      current_weight: 0.15,
      target_weight: 0.25,
    },
  },
  {
    id: 'AP-005',
    type: 'experiment',
    title: '大规模参数扫描实验',
    description: '申请执行 500 组参数组合的回测实验，预计消耗 2500 CP。',
    requester: 'alpha_a_lead',
    department: 'Research Guild',
    urgency: 'normal',
    status: 'rejected',
    created_at: '2026-01-12 15:00',
    data: {
      param_combinations: 500,
      estimated_cp: 2500,
    },
  },
]

const typeConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  trading: { label: '交易', icon: TrendingUp, color: 'text-cyan-400' },
  hiring: { label: '招聘', icon: Users, color: 'text-purple-400' },
  strategy: { label: '策略', icon: FileText, color: 'text-accent-primary' },
  meeting: { label: '会议', icon: MessageSquare, color: 'text-blue-400' },
  experiment: { label: '实验', icon: AlertTriangle, color: 'text-orange-400' },
}

const urgencyConfig = {
  normal: { label: '普通', color: 'badge-neutral' },
  high: { label: '紧急', color: 'badge-warning' },
  critical: { label: '危急', color: 'badge-danger' },
}

function ApprovalCard({
  item,
  onApprove,
  onReject,
}: {
  item: ApprovalItem
  onApprove?: () => void
  onReject?: () => void
}) {
  const typeInfo = typeConfig[item.type]
  const Icon = typeInfo.icon
  const urgencyInfo = urgencyConfig[item.urgency]

  return (
    <div className={`card ${item.urgency === 'high' ? 'border-l-2 border-accent-warning' : ''}`}>
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-lg bg-terminal-muted flex items-center justify-center ${typeInfo.color}`}>
          <Icon className="w-5 h-5" />
        </div>
        
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500 font-mono">{item.id}</span>
            <span className={`badge ${urgencyInfo.color} text-[10px]`}>{urgencyInfo.label}</span>
            <span className={`badge badge-neutral text-[10px] ${typeInfo.color}`}>{typeInfo.label}</span>
          </div>
          
          <h3 className="text-base font-medium text-gray-100">{item.title}</h3>
          <p className="text-sm text-gray-400 mt-1">{item.description}</p>

          {/* Data Preview */}
          {item.data && (
            <div className="mt-3 p-3 bg-terminal-muted/50 rounded-lg">
              <div className="grid grid-cols-3 gap-4 text-sm">
                {Object.entries(item.data).slice(0, 3).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-xs text-gray-500">{key}</div>
                    <div className="text-gray-200 font-medium">
                      {typeof value === 'number' && value < 1 && value > -1
                        ? `${(value * 100).toFixed(1)}%`
                        : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between mt-4 pt-3 border-t border-terminal-border/50">
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <User className="w-3 h-3" />
                {item.requester}
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {item.created_at}
              </div>
              {item.expires_at && (
                <div className="flex items-center gap-1 text-accent-warning">
                  <AlertTriangle className="w-3 h-3" />
                  截止: {item.expires_at}
                </div>
              )}
            </div>

            {item.status === 'pending' && (
              <div className="flex items-center gap-2">
                <button
                  onClick={onReject}
                  className="btn btn-danger btn-sm"
                >
                  <XCircle className="w-4 h-4 mr-1" />
                  拒绝
                </button>
                <button
                  onClick={onApprove}
                  className="btn btn-primary btn-sm"
                >
                  <CheckCircle className="w-4 h-4 mr-1" />
                  批准
                </button>
              </div>
            )}

            {item.status !== 'pending' && (
              <span className={`badge ${item.status === 'approved' ? 'badge-success' : 'badge-danger'}`}>
                {item.status === 'approved' ? '已批准' : '已拒绝'}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function ApprovalsPage() {
  const [filter, setFilter] = useState('pending')

  const filteredItems = approvalItems.filter((item) => {
    if (filter === 'pending') return item.status === 'pending'
    if (filter === 'completed') return item.status !== 'pending'
    return true
  })

  const pendingCount = approvalItems.filter((i) => i.status === 'pending').length
  const urgentCount = approvalItems.filter((i) => i.status === 'pending' && i.urgency !== 'normal').length

  const handleApprove = (id: string) => {
    console.log('Approving:', id)
    // TODO: Call API
  }

  const handleReject = (id: string) => {
    console.log('Rejecting:', id)
    // TODO: Call API
  }

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">审批队列</h1>
          <p className="page-subtitle">待您决定的事项</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-400">待审批:</span>
            <span className="text-xl font-bold text-accent-warning">{pendingCount}</span>
          </div>
          {urgentCount > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-accent-danger" />
              <span className="text-accent-danger font-medium">{urgentCount} 紧急</span>
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 border-b border-terminal-border">
        <button
          onClick={() => setFilter('pending')}
          className={`pb-3 px-1 text-sm border-b-2 transition-colors ${
            filter === 'pending'
              ? 'border-accent-primary text-accent-primary'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          待处理 ({pendingCount})
        </button>
        <button
          onClick={() => setFilter('completed')}
          className={`pb-3 px-1 text-sm border-b-2 transition-colors ${
            filter === 'completed'
              ? 'border-accent-primary text-accent-primary'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          已处理 ({approvalItems.length - pendingCount})
        </button>
        <button
          onClick={() => setFilter('all')}
          className={`pb-3 px-1 text-sm border-b-2 transition-colors ${
            filter === 'all'
              ? 'border-accent-primary text-accent-primary'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          全部 ({approvalItems.length})
        </button>
      </div>

      {/* Approval Items */}
      <div className="space-y-4">
        {filteredItems.map((item) => (
          <ApprovalCard
            key={item.id}
            item={item}
            onApprove={() => handleApprove(item.id)}
            onReject={() => handleReject(item.id)}
          />
        ))}
      </div>

      {filteredItems.length === 0 && (
        <div className="text-center py-12">
          <CheckSquare className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500">
            {filter === 'pending' ? '没有待处理的审批项' : '没有审批记录'}
          </p>
        </div>
      )}
    </div>
  )
}
