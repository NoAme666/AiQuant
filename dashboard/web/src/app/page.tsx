'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  TrendingUp,
  TrendingDown,
  Users,
  FlaskConical,
  FileText,
  CheckSquare,
  Activity,
  Zap,
  Clock,
  ArrowRight,
  DollarSign,
  AlertTriangle,
  Building2,
  Brain,
  Target,
  MessageSquare,
  Shield,
} from 'lucide-react'
import useSWR from 'swr'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

// Stats Card Component
function StatCard({
  title,
  value,
  change,
  changeType,
  icon: Icon,
  suffix = '',
}: {
  title: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon: React.ElementType
  suffix?: string
}) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <span className="stat-label">{title}</span>
        <Icon className="w-5 h-5 text-gray-500" />
      </div>
      <div className="stat-value number-highlight">
        {value}{suffix}
      </div>
      {change && (
        <div className={`stat-change ${changeType}`}>
          {changeType === 'positive' && <TrendingUp className="w-3 h-3 inline mr-1" />}
          {changeType === 'negative' && <TrendingDown className="w-3 h-3 inline mr-1" />}
          {change}
        </div>
      )}
    </div>
  )
}

// 部门卡片
function DepartmentCard({
  name,
  nameEn,
  agentCount,
  activeCount,
  icon: Icon,
  color,
  href,
}: {
  name: string
  nameEn: string
  agentCount: number
  activeCount: number
  icon: React.ElementType
  color: string
  href: string
}) {
  return (
    <Link href={href} className="card-hover p-4">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex items-center gap-1">
          <span className="status-dot active"></span>
          <span className="text-xs text-gray-500">{activeCount}/{agentCount}</span>
        </div>
      </div>
      <h3 className="text-base font-medium text-gray-100">{name}</h3>
      <p className="text-xs text-gray-500">{nameEn}</p>
    </Link>
  )
}

// 待审批项
function ApprovalItem({ item }: { item: any }) {
  return (
    <div className="p-3 bg-terminal-muted/30 rounded-lg border-l-2 border-accent-warning hover:bg-terminal-muted/50 transition-colors cursor-pointer">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-200 truncate flex-1 mr-2">{item.title}</span>
        {item.urgency === 'high' && (
          <span className="badge badge-danger text-[10px] shrink-0">紧急</span>
        )}
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>来自 {item.from}</span>
          <span className="text-accent-warning">{item.type}</span>
        </div>
        <span className="text-xs text-gray-400 font-medium">{item.owner || 'CIO'} 负责</span>
      </div>
    </div>
  )
}

// Agent 活动卡片
function AgentActivityCard({ agent }: { agent: any }) {
  const statusDot = agent.status === 'active' ? 'active' : 
                    agent.status === 'off' ? 'bg-gray-600' : 'idle'
  const isOff = agent.status === 'off'
  
  return (
    <Link
      href={`/chat/${agent.id}`}
      className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
        isOff ? 'bg-terminal-muted/10 opacity-60' : 'bg-terminal-muted/30 hover:bg-terminal-muted/50'
      }`}
    >
      <span className={`w-2 h-2 rounded-full ${
        agent.status === 'active' ? 'bg-accent-success' :
        agent.status === 'off' ? 'bg-gray-600' : 'bg-gray-400'
      }`}></span>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium ${isOff ? 'text-gray-400' : 'text-gray-200'}`}>{agent.name}</div>
        <div className={`text-xs truncate ${isOff ? 'text-gray-600' : 'text-gray-500'}`}>
          {agent.current_task || '空闲'}
        </div>
      </div>
      <ArrowRight className={`w-4 h-4 shrink-0 ${isOff ? 'text-gray-700' : 'text-gray-500'}`} />
    </Link>
  )
}

export default function DashboardPage() {
  const { data: healthData } = useSWR(`${API_BASE}/health`, fetcher, { refreshInterval: 5000 })
  const { data: agentsData } = useSWR(`${API_BASE}/api/org-chart`, fetcher, { refreshInterval: 10000 })
  const { data: approvalsData } = useSWR(`${API_BASE}/api/approvals/pending`, fetcher, { refreshInterval: 10000 })
  const { data: eventsData } = useSWR(`${API_BASE}/api/events/recent?limit=8`, fetcher, { refreshInterval: 3000 })
  const { data: agentSystemStatus } = useSWR(`${API_BASE}/api/system/agent-status`, fetcher, { refreshInterval: 3000 })
  
  const isBackendConnected = !!healthData
  const isAgentRunning = agentSystemStatus?.is_running || false
  
  // 部门数据
  const departments = [
    { name: '董事会办公室', nameEn: 'Board Office', agentCount: 2, activeCount: 2, icon: Building2, color: 'bg-purple-500', href: '/org#board' },
    { name: '研究部', nameEn: 'Research Guild', agentCount: 6, activeCount: 5, icon: FlaskConical, color: 'bg-blue-500', href: '/org#research' },
    { name: '风控部', nameEn: 'Risk Guild', agentCount: 3, activeCount: 3, icon: Shield, color: 'bg-orange-500', href: '/org#risk' },
    { name: '交易部', nameEn: 'Trading Guild', agentCount: 4, activeCount: 4, icon: TrendingUp, color: 'bg-green-500', href: '/org#trading' },
    { name: '情报部', nameEn: 'Intelligence Guild', agentCount: 5, activeCount: 4, icon: Brain, color: 'bg-cyan-500', href: '/org#intelligence' },
    { name: '治理部', nameEn: 'Governance', agentCount: 3, activeCount: 3, icon: Target, color: 'bg-pink-500', href: '/org#governance' },
  ]
  
  const pendingApprovals = approvalsData?.approvals || [
    { id: '1', title: 'BTC 动量策略执行计划', type: '交易', urgency: 'high', from: '交易主管', owner: 'CRO' },
    { id: '2', title: '新增情绪分析工具请求', type: '工具', urgency: 'normal', from: 'Alpha A 组长', owner: 'CTO*' },
    { id: '3', title: '风控规则调整提案', type: '治理', urgency: 'normal', from: 'CRO', owner: '投票中' },
  ]
  
  const defaultAgents = [
    { id: 'cio', name: 'CIO', current_task: '审核策略提案' },
    { id: 'head_of_research', name: '研究总监', current_task: '主持策略评审' },
    { id: 'cro', name: 'CRO', current_task: '风险评估' },
    { id: 'head_trader', name: '交易主管', current_task: '执行监控' },
    { id: 'alpha_a_lead', name: 'Alpha A 组长', current_task: '策略研究' },
  ]
  
  const activeAgents = defaultAgents.map(a => ({
    ...a,
    status: isAgentRunning ? 'active' : 'off',
    current_task: isAgentRunning ? a.current_task : '未上班',
  }))
  
  const recentEvents = eventsData?.events || [
    { time: '17:38', agent: 'Alpha A 组长', action: '提交策略回测报告', type: 'research' },
    { time: '17:35', agent: 'CRO', action: '完成风险评估', type: 'risk' },
    { time: '17:32', agent: '交易主管', action: '确认执行计划', type: 'trade' },
    { time: '17:28', agent: '情报总监', action: '发布市场预警', type: 'intelligence' },
  ]
  
  return (
    <div className="space-y-6 animate-slide-in">
      {/* Backend Status Banner */}
      {!isBackendConnected && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-yellow-200 font-medium">后端未连接</p>
            <p className="text-xs text-yellow-400 truncate">
              请启动: <code className="bg-terminal-muted px-1 rounded">python -m uvicorn dashboard.api.main:app --port 8000</code>
            </p>
          </div>
        </div>
      )}
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">控制中心</h1>
          <p className="page-subtitle">AI Quant Company · 董事长仪表盘</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary btn-sm">
            <FileText className="w-4 h-4 mr-2" />
            生成周报
          </button>
          <button className="btn btn-primary btn-sm">
            <Zap className="w-4 h-4 mr-2" />
            启动研究周期
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="活跃 Agent"
          value={isAgentRunning ? "34" : "0"}
          change={isAgentRunning ? "运行中" : "未启动"}
          changeType={isAgentRunning ? "positive" : "neutral"}
          icon={Users}
        />
        <StatCard
          title="研究周期"
          value="5"
          change="3 进行中"
          changeType="neutral"
          icon={FlaskConical}
        />
        <StatCard
          title="待审批"
          value={pendingApprovals.length}
          change={`${pendingApprovals.filter((a: any) => a.urgency === 'high').length} 紧急`}
          changeType="negative"
          icon={CheckSquare}
        />
        <StatCard
          title="本周收益"
          value="+2.4"
          suffix="%"
          change="+$1,240"
          changeType="positive"
          icon={DollarSign}
        />
        <StatCard
          title="风险指数"
          value="32"
          change="低风险"
          changeType="positive"
          icon={Activity}
        />
      </div>

      {/* 部门概览 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">公司组织</h2>
          <Link href="/org" className="text-xs text-accent-primary hover:underline">
            查看组织架构 →
          </Link>
        </div>
        <div className="grid grid-cols-6 gap-4">
          {departments.map((dept) => (
            <DepartmentCard key={dept.nameEn} {...dept} />
          ))}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* 待审批 */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-accent-warning" />
            <h2 className="text-lg font-semibold text-gray-100">待您审批</h2>
            <span className="badge badge-warning text-xs ml-auto">{pendingApprovals.length}</span>
          </div>
          <div className="space-y-3">
            {pendingApprovals.slice(0, 4).map((item: any) => (
              <ApprovalItem key={item.id} item={item} />
            ))}
          </div>
          <Link href="/approvals" className="block text-center text-sm text-accent-primary hover:underline mt-4">
            查看全部待审批 →
          </Link>
        </div>

        {/* 活跃 Agent */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-100">当前活跃</h2>
            <span className="flex items-center gap-1 text-xs text-accent-success">
              <span className="status-dot active"></span>
              {activeAgents.length} 在线
            </span>
          </div>
          <div className="space-y-2">
            {activeAgents.map((agent: any) => (
              <AgentActivityCard key={agent.id} agent={agent} />
            ))}
          </div>
          <Link href="/org" className="block text-center text-sm text-accent-primary hover:underline mt-4">
            查看全部 Agent →
          </Link>
        </div>

        {/* 实时动态 */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-100">实时动态</h2>
            <span className="flex items-center gap-1 text-xs text-accent-success">
              <span className="status-dot active"></span>
              Live
            </span>
          </div>
          <div className="space-y-3">
            {recentEvents.map((event: any, idx: number) => (
              <div key={idx} className="flex items-start gap-3 text-sm">
                <span className="text-xs text-gray-500 font-mono w-10 shrink-0">{event.time}</span>
                <div className="flex-1 min-w-0">
                  <span className="text-gray-300">{event.agent}</span>
                  <span className="text-gray-500 mx-1">·</span>
                  <span className={`${
                    event.type === 'research' ? 'text-purple-400' :
                    event.type === 'risk' ? 'text-orange-400' :
                    event.type === 'trade' ? 'text-green-400' :
                    event.type === 'intelligence' ? 'text-cyan-400' :
                    'text-gray-400'
                  }`}>{event.action}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 快捷入口 */}
      <div className="grid grid-cols-4 gap-4">
        <Link href="/chat/cio" className="card-hover flex items-center gap-3 p-4">
          <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0">
            <MessageSquare className="w-5 h-5 text-purple-400" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-gray-200">与 CIO 对话</div>
            <div className="text-xs text-gray-500 truncate">投资策略讨论</div>
          </div>
        </Link>
        <Link href="/trading" className="card-hover flex items-center gap-3 p-4">
          <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center shrink-0">
            <TrendingUp className="w-5 h-5 text-green-400" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-gray-200">交易台</div>
            <div className="text-xs text-gray-500 truncate">行情与执行</div>
          </div>
        </Link>
        <Link href="/reports" className="card-hover flex items-center gap-3 p-4">
          <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5 text-blue-400" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-gray-200">报告中心</div>
            <div className="text-xs text-gray-500 truncate">查看所有报告</div>
          </div>
        </Link>
        <Link href="/meetings" className="card-hover flex items-center gap-3 p-4">
          <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center shrink-0">
            <Clock className="w-5 h-5 text-orange-400" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-gray-200">会议室</div>
            <div className="text-xs text-gray-500 truncate">对话与议题</div>
          </div>
        </Link>
      </div>
    </div>
  )
}
