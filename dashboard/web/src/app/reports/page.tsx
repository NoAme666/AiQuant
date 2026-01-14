'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  FileText,
  Download,
  Eye,
  Filter,
  Search,
  Calendar,
  User,
  Clock,
  TrendingUp,
  Shield,
  CheckCircle,
  Building2,
} from 'lucide-react'

interface Report {
  id: string
  title: string
  type: 'board_pack' | 'research' | 'trading' | 'compliance' | 'weekly'
  author: string
  created_at: string
  status: 'draft' | 'published' | 'archived'
  summary?: string
}

const reports: Report[] = [
  {
    id: 'WR-20260114-A1B2C3',
    title: '周度董事会汇报 (01/08 - 01/14)',
    type: 'weekly',
    author: 'Chief of Staff',
    created_at: '2026-01-14 16:00',
    status: 'published',
    summary: '本周研究进展显著，3个策略进入风控审核阶段...',
  },
  {
    id: 'RR-20260113-D4E5F6',
    title: 'BTC 动量突破策略研究报告',
    type: 'research',
    author: 'Alpha A Lead',
    created_at: '2026-01-13 14:30',
    status: 'published',
    summary: 'Sharpe 1.85, Max DD -12%, 建议进入投委会审议...',
  },
  {
    id: 'TR-20260113-G7H8I9',
    title: '交易执行报告 - TP-001',
    type: 'trading',
    author: 'Head Trader',
    created_at: '2026-01-13 18:00',
    status: 'published',
    summary: '执行3笔订单，总成交$47,500，平均滑点12bps...',
  },
  {
    id: 'CR-20260113-J0K1L2',
    title: '每日合规审计报告',
    type: 'compliance',
    author: 'CGO',
    created_at: '2026-01-13 20:00',
    status: 'published',
    summary: '审计完成，未发现违规行为...',
  },
  {
    id: 'BP-20260112-M3N4O5',
    title: '波动率策略 v2 董事会报告',
    type: 'board_pack',
    author: 'CIO',
    created_at: '2026-01-12 17:00',
    status: 'published',
    summary: '策略通过所有闸门审核，建议批准上线...',
  },
  {
    id: 'RR-20260110-P6Q7R8',
    title: 'ETH 均值回归策略研究报告',
    type: 'research',
    author: 'Alpha A Researcher 1',
    created_at: '2026-01-10 11:00',
    status: 'draft',
    summary: '初步回测结果，待完善...',
  },
]

const typeConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  'board_pack': { label: '董事会报告', icon: Building2, color: 'text-accent-primary' },
  'research': { label: '研究报告', icon: FileText, color: 'text-purple-400' },
  'trading': { label: '交易报告', icon: TrendingUp, color: 'text-cyan-400' },
  'compliance': { label: '合规报告', icon: Shield, color: 'text-orange-400' },
  'weekly': { label: '周报', icon: Calendar, color: 'text-green-400' },
}

function ReportCard({ report }: { report: Report }) {
  const config = typeConfig[report.type]
  const Icon = config.icon

  return (
    <div className="card-hover p-4">
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg bg-terminal-muted flex items-center justify-center ${config.color}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-mono">{report.id}</span>
            {report.status === 'draft' && (
              <span className="badge badge-warning text-[10px]">草稿</span>
            )}
          </div>
          <h3 className="text-sm font-medium text-gray-100 mt-1 line-clamp-2">{report.title}</h3>
          {report.summary && (
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{report.summary}</p>
          )}
          
          <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
            <div className="flex items-center gap-1">
              <User className="w-3 h-3" />
              {report.author}
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {report.created_at}
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-terminal-border/50">
        <button className="btn btn-ghost btn-sm flex-1">
          <Eye className="w-4 h-4 mr-1" />
          查看
        </button>
        <button className="btn btn-ghost btn-sm flex-1">
          <Download className="w-4 h-4 mr-1" />
          PDF
        </button>
      </div>
    </div>
  )
}

export default function ReportsPage() {
  const [filter, setFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredReports = reports.filter((r) => {
    if (filter !== 'all' && r.type !== filter) return false
    if (searchQuery && !r.title.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  const typeCounts = {
    all: reports.length,
    board_pack: reports.filter((r) => r.type === 'board_pack').length,
    research: reports.filter((r) => r.type === 'research').length,
    trading: reports.filter((r) => r.type === 'trading').length,
    compliance: reports.filter((r) => r.type === 'compliance').length,
    weekly: reports.filter((r) => r.type === 'weekly').length,
  }

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">报告中心</h1>
          <p className="page-subtitle">查看和管理所有系统报告</p>
        </div>
        <button className="btn btn-primary btn-sm">
          <FileText className="w-4 h-4 mr-2" />
          生成报告
        </button>
      </div>

      {/* Search and Filter */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="搜索报告..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-9"
          />
        </div>
      </div>

      {/* Type Filters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-colors ${
            filter === 'all'
              ? 'bg-accent-primary/20 text-accent-primary border border-accent-primary/30'
              : 'bg-terminal-muted text-gray-400 hover:text-gray-200'
          }`}
        >
          全部 ({typeCounts.all})
        </button>
        {Object.entries(typeConfig).map(([key, config]) => {
          const Icon = config.icon
          return (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-colors ${
                filter === key
                  ? 'bg-terminal-muted border border-terminal-border ' + config.color
                  : 'bg-terminal-muted/50 text-gray-400 hover:text-gray-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              {config.label} ({typeCounts[key as keyof typeof typeCounts]})
            </button>
          )
        })}
      </div>

      {/* Reports Grid */}
      <div className="grid grid-cols-2 gap-4">
        {filteredReports.map((report) => (
          <ReportCard key={report.id} report={report} />
        ))}
      </div>

      {filteredReports.length === 0 && (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500">没有找到匹配的报告</p>
        </div>
      )}
    </div>
  )
}
