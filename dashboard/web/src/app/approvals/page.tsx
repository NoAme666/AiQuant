'use client'

import { useState } from 'react'
import Link from 'next/link'
import useSWR, { mutate } from 'swr'
import {
  CheckSquare,
  Clock,
  User,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Filter,
  ChevronRight,
  TrendingUp,
  FlaskConical,
  Shield,
  Settings,
  MessageSquare,
  ArrowRight,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface ApprovalItem {
  id: string
  title: string
  description: string
  type: 'trading' | 'research' | 'governance' | 'tool' | 'budget'
  urgency: 'normal' | 'high' | 'critical'
  requester: string
  requester_id: string
  responsible: string
  responsible_id: string
  created_at: string
  due_date?: string
  status: 'pending' | 'approved' | 'rejected'
  context?: string
}

// 审批数据从 API 获取

const typeConfig = {
  trading: { icon: TrendingUp, color: 'text-green-400', bgColor: 'bg-green-500/20', label: '交易' },
  research: { icon: FlaskConical, color: 'text-cyan-400', bgColor: 'bg-cyan-500/20', label: '研究' },
  governance: { icon: Shield, color: 'text-orange-400', bgColor: 'bg-orange-500/20', label: '治理' },
  tool: { icon: Settings, color: 'text-purple-400', bgColor: 'bg-purple-500/20', label: '工具' },
  budget: { icon: CheckSquare, color: 'text-blue-400', bgColor: 'bg-blue-500/20', label: '预算' },
}

function ApprovalCard({ item }: { item: ApprovalItem }) {
  const config = typeConfig[item.type]
  const Icon = config.icon

  return (
    <div className={`card-hover p-4 ${item.urgency === 'critical' ? 'border-l-2 border-accent-danger' : item.urgency === 'high' ? 'border-l-2 border-accent-warning' : ''}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-lg ${config.bgColor} flex items-center justify-center shrink-0`}>
            <Icon className={`w-5 h-5 ${config.color}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-mono">{item.id}</span>
              <span className={`badge ${config.bgColor} ${config.color} text-[10px]`}>{config.label}</span>
              {item.urgency === 'high' && (
                <span className="badge badge-warning text-[10px]">紧急</span>
              )}
              {item.urgency === 'critical' && (
                <span className="badge badge-danger text-[10px]">紧迫</span>
              )}
            </div>
            <h3 className="text-sm font-medium text-gray-200 mt-1">{item.title}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
          </div>
        </div>
      </div>

      {/* Context */}
      {item.context && (
        <div className="mb-3 p-2 bg-terminal-muted/30 rounded text-xs text-gray-400">
          <MessageSquare className="w-3 h-3 inline mr-1" />
          {item.context}
        </div>
      )}

      {/* Workflow */}
      <div className="flex items-center gap-4 py-2 border-y border-terminal-border/50 mb-3">
        <div className="flex items-center gap-2">
          <User className="w-3 h-3 text-gray-500" />
          <span className="text-xs text-gray-400">申请人:</span>
          <Link href={`/chat/${item.requester_id}`} className="text-xs text-accent-primary hover:underline">
            {item.requester}
          </Link>
        </div>
        <ChevronRight className="w-3 h-3 text-gray-600" />
        <div className="flex items-center gap-2">
          <CheckSquare className="w-3 h-3 text-gray-500" />
          <span className="text-xs text-gray-400">负责人:</span>
          <Link href={`/chat/${item.responsible_id}`} className="text-xs text-accent-warning hover:underline font-medium">
            {item.responsible}
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {item.created_at}
          </div>
          {item.due_date && (
            <div className="flex items-center gap-1 text-accent-warning">
              <AlertTriangle className="w-3 h-3" />
              截止 {item.due_date}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-danger btn-sm py-1 px-3 text-xs">
            <XCircle className="w-3 h-3 mr-1" />
            驳回
          </button>
          <button className="btn btn-success btn-sm py-1 px-3 text-xs">
            <CheckCircle className="w-3 h-3 mr-1" />
            批准
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ApprovalsPage() {
  const [filter, setFilter] = useState<string>('all')
  
  // 从 API 获取真实审批数据
  const { data: approvalsData, mutate: mutateApprovals } = useSWR(`${API_BASE}/api/v2/approvals`, fetcher, { refreshInterval: 5000 })
  const approvalItems: ApprovalItem[] = approvalsData?.approvals || []

  const pendingItems = approvalItems.filter(i => i.status === 'pending')
  const urgentItems = pendingItems.filter(i => i.urgency === 'high' || i.urgency === 'critical')

  const filteredItems = filter === 'all'
    ? pendingItems
    : filter === 'urgent'
    ? urgentItems
    : pendingItems.filter(i => i.type === filter)
    
  // 处理审批操作
  const handleApprove = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/v2/approvals/${id}/approve?approver=chairman`, { method: 'PUT' })
      mutateApprovals()
    } catch (e) {
      console.error('审批失败', e)
    }
  }
  
  const handleReject = async (id: string, reason?: string) => {
    try {
      const url = reason 
        ? `${API_BASE}/api/v2/approvals/${id}/reject?reason=${encodeURIComponent(reason)}`
        : `${API_BASE}/api/v2/approvals/${id}/reject`
      await fetch(url, { method: 'PUT' })
      mutateApprovals()
    } catch (e) {
      console.error('驳回失败', e)
    }
  }

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">审批队列</h1>
          <p className="page-subtitle">待处理的审批请求</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary btn-sm">
            <Filter className="w-4 h-4 mr-2" />
            筛选
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <div className="card">
          <div className="text-2xl font-bold text-gray-100">{pendingItems.length}</div>
          <div className="text-sm text-gray-500">待审批</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-accent-danger">{urgentItems.length}</div>
          <div className="text-sm text-gray-500">紧急</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-green-400">{pendingItems.filter(i => i.type === 'trading').length}</div>
          <div className="text-sm text-gray-500">交易相关</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-cyan-400">{pendingItems.filter(i => i.type === 'research').length}</div>
          <div className="text-sm text-gray-500">研究相关</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-orange-400">{pendingItems.filter(i => i.type === 'governance').length}</div>
          <div className="text-sm text-gray-500">治理相关</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
            filter === 'all' ? 'bg-accent-primary/20 text-accent-primary' : 'bg-terminal-muted/30 text-gray-400 hover:text-gray-200'
          }`}
        >
          全部 ({pendingItems.length})
        </button>
        <button
          onClick={() => setFilter('urgent')}
          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
            filter === 'urgent' ? 'bg-accent-danger/20 text-accent-danger' : 'bg-terminal-muted/30 text-gray-400 hover:text-gray-200'
          }`}
        >
          紧急 ({urgentItems.length})
        </button>
        {Object.entries(typeConfig).map(([type, config]) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors flex items-center gap-1 ${
              filter === type ? `${config.bgColor} ${config.color}` : 'bg-terminal-muted/30 text-gray-400 hover:text-gray-200'
            }`}
          >
            <config.icon className="w-3 h-3" />
            {config.label}
          </button>
        ))}
      </div>

      {/* Approval List */}
      <div className="space-y-4">
        {filteredItems.map((item) => (
          <ApprovalCard key={item.id} item={item} />
        ))}
        {filteredItems.length === 0 && (
          <div className="card text-center py-12">
            <CheckCircle className="w-12 h-12 text-accent-success mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-medium text-gray-300">暂无待审批项目</h3>
            <p className="text-sm text-gray-500 mt-1">所有审批请求已处理完毕</p>
          </div>
        )}
      </div>
    </div>
  )
}
