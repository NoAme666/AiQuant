'use client'

import { useState } from 'react'
import Link from 'next/link'
import useSWR from 'swr'
import {
  FileText,
  Shield,
  FlaskConical,
  Briefcase,
  Download,
  Eye,
  Clock,
  User,
  Filter,
  ChevronRight,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  BarChart3,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface Report {
  id: string
  title: string
  type: 'compliance' | 'research' | 'executive'
  author: string
  author_id: string
  created_at: string
  status: 'draft' | 'pending' | 'approved'
  summary?: string
  metrics?: Record<string, string | number>
}

// 报告数据从 API 获取

function ReportCard({ report }: { report: Report }) {
  const typeConfig = {
    compliance: { icon: Shield, color: 'text-orange-400', bgColor: 'bg-orange-500/20', label: '监督' },
    research: { icon: FlaskConical, color: 'text-cyan-400', bgColor: 'bg-cyan-500/20', label: '研究' },
    executive: { icon: Briefcase, color: 'text-purple-400', bgColor: 'bg-purple-500/20', label: '汇报' },
  }
  const config = typeConfig[report.type]
  const Icon = config.icon

  return (
    <div className="card-hover p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${config.color}`} />
          </div>
          <div>
            <span className="text-xs text-gray-500 font-mono">{report.id}</span>
            <h3 className="text-sm font-medium text-gray-200">{report.title}</h3>
          </div>
        </div>
        <span className={`badge ${
          report.status === 'approved' ? 'badge-success' :
          report.status === 'pending' ? 'badge-warning' :
          'badge-neutral'
        } text-[10px]`}>
          {report.status === 'approved' ? '已审批' : report.status === 'pending' ? '待审核' : '草稿'}
        </span>
      </div>

      {report.summary && (
        <p className="text-xs text-gray-500 mb-3 line-clamp-2">{report.summary}</p>
      )}

      {report.metrics && (
        <div className="flex items-center gap-3 mb-3 py-2 border-y border-terminal-border/50">
          {Object.entries(report.metrics).slice(0, 3).map(([key, value]) => (
            <div key={key} className="text-center flex-1">
              <div className="text-sm font-medium text-gray-200">{value}</div>
              <div className="text-[10px] text-gray-500">{key}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Link href={`/chat/${report.author_id}`} className="hover:text-accent-primary">
            {report.author}
          </Link>
          <span>•</span>
          <span>{report.created_at}</span>
        </div>
        <div className="flex items-center gap-1">
          <button className="btn btn-ghost btn-sm p-1.5" title="查看">
            <Eye className="w-4 h-4" />
          </button>
          <button className="btn btn-ghost btn-sm p-1.5" title="下载">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function ReportColumn({
  title,
  icon: Icon,
  color,
  reports,
}: {
  title: string
  icon: React.ElementType
  color: string
  reports: Report[]
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 pb-2 border-b border-terminal-border">
        <Icon className={`w-5 h-5 ${color}`} />
        <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
        <span className="badge badge-neutral text-xs ml-auto">{reports.length}</span>
      </div>
      <div className="space-y-3">
        {reports.map((report) => (
          <ReportCard key={report.id} report={report} />
        ))}
      </div>
    </div>
  )
}

export default function ReportsPage() {
  // 从 API 获取真实报告数据
  const { data: reportsData } = useSWR(`${API_BASE}/api/v2/reports`, fetcher, { refreshInterval: 5000 })
  const allReports: Report[] = reportsData?.reports || []
  
  // 按类型分组
  const complianceReports = allReports.filter(r => r.type === 'compliance')
  const researchReports = allReports.filter(r => r.type === 'research')
  const executiveReports = allReports.filter(r => r.type === 'executive')
  
  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">报告中心</h1>
          <p className="page-subtitle">监督报告 · 研究报告 · 工作汇报</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary btn-sm">
            <Filter className="w-4 h-4 mr-2" />
            筛选
          </button>
          <button className="btn btn-primary btn-sm">
            <FileText className="w-4 h-4 mr-2" />
            生成报告
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="text-2xl font-bold text-gray-100">
            {complianceReports.length + researchReports.length + executiveReports.length}
          </div>
          <div className="text-sm text-gray-500">总报告数</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-orange-400">{complianceReports.length}</div>
          <div className="text-sm text-gray-500">监督报告</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-cyan-400">{researchReports.length}</div>
          <div className="text-sm text-gray-500">研究报告</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-purple-400">{executiveReports.length}</div>
          <div className="text-sm text-gray-500">工作汇报</div>
        </div>
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-3 gap-6">
        <ReportColumn
          title="监督报告"
          icon={Shield}
          color="text-orange-400"
          reports={complianceReports}
        />
        <ReportColumn
          title="研究报告"
          icon={FlaskConical}
          color="text-cyan-400"
          reports={researchReports}
        />
        <ReportColumn
          title="给董事长的汇报"
          icon={Briefcase}
          color="text-purple-400"
          reports={executiveReports}
        />
      </div>
    </div>
  )
}
