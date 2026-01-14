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
} from 'lucide-react'
import useSWR from 'swr'

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

// Agent Status Component
function AgentStatusList() {
  const agents = [
    { id: 'cio', name: 'CIO', status: 'active', task: '审核策略报告' },
    { id: 'head_of_research', name: '研究总监', status: 'active', task: '分析市场数据' },
    { id: 'cro', name: 'CRO', status: 'active', task: '风险评估' },
    { id: 'head_trader', name: '交易主管', status: 'active', task: '监控持仓' },
    { id: 'alpha_a_lead', name: 'Alpha A 组长', status: 'active', task: '因子研究' },
    { id: 'skeptic', name: '质疑者', status: 'frozen', task: '- 暂停 -' },
  ]

  return (
    <div className="space-y-2">
      {agents.map((agent) => (
        <Link
          key={agent.id}
          href={`/chat/${agent.id}`}
          className="flex items-center gap-3 p-3 bg-terminal-muted/30 rounded-lg hover:bg-terminal-muted/50 transition-colors"
        >
          <span className={`status-dot ${agent.status}`}></span>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-200">{agent.name}</div>
            <div className="text-xs text-gray-500 truncate">{agent.task}</div>
          </div>
          <ArrowRight className="w-4 h-4 text-gray-500" />
        </Link>
      ))}
    </div>
  )
}

// Recent Activity Component
function RecentActivity() {
  const activities = [
    { time: '14:32', agent: 'Alpha A 组长', action: '提交策略研究报告', type: 'research' },
    { time: '14:28', agent: 'CRO', action: '审核通过 BTC/USDT 交易计划', type: 'approval' },
    { time: '14:15', agent: '执行交易员', action: '完成订单执行', type: 'trade' },
    { time: '13:50', agent: 'CGO', action: '发布合规检查报告', type: 'compliance' },
    { time: '13:30', agent: '研究总监', action: '发起研究周期 #RC-2026-001', type: 'research' },
  ]

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'research': return 'text-purple-400'
      case 'approval': return 'text-accent-success'
      case 'trade': return 'text-accent-primary'
      case 'compliance': return 'text-orange-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="space-y-3">
      {activities.map((activity, idx) => (
        <div key={idx} className="flex items-start gap-3 text-sm">
          <span className="text-xs text-gray-500 font-mono w-12">{activity.time}</span>
          <div>
            <span className="text-gray-300">{activity.agent}</span>
            <span className="text-gray-500 mx-1">·</span>
            <span className={getTypeColor(activity.type)}>{activity.action}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

// Pending Approvals Component
function PendingApprovals() {
  const approvals = [
    { id: '1', title: 'BTC/USDT 交易计划', type: 'trading', urgency: 'high', from: '交易主管' },
    { id: '2', title: '新增研究员招聘提案', type: 'hiring', urgency: 'normal', from: 'CPO' },
    { id: '3', title: '策略 MeanRev_v2 上线', type: 'strategy', urgency: 'normal', from: 'CIO' },
  ]

  return (
    <div className="space-y-3">
      {approvals.map((item) => (
        <div
          key={item.id}
          className="p-3 bg-terminal-muted/30 rounded-lg border-l-2 border-accent-warning hover:bg-terminal-muted/50 transition-colors cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-200">{item.title}</span>
            {item.urgency === 'high' && (
              <span className="badge badge-danger text-[10px]">紧急</span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            <span>来自 {item.from}</span>
            <span>·</span>
            <span className="text-accent-warning">{item.type}</span>
          </div>
        </div>
      ))}
      <Link href="/approvals" className="block text-center text-sm text-accent-primary hover:underline">
        查看全部待审批 →
      </Link>
    </div>
  )
}

// Research Cycles Component
function ResearchCycles() {
  const cycles = [
    { id: 'RC-001', name: 'BTC 动量策略', stage: 'RISK_REVIEW', progress: 70 },
    { id: 'RC-002', name: 'ETH 均值回归', stage: 'BACKTEST', progress: 45 },
    { id: 'RC-003', name: '跨市场套利', stage: 'DATA_GATE', progress: 20 },
  ]

  const getStageColor = (stage: string) => {
    const colors: Record<string, string> = {
      'DATA_GATE': 'bg-blue-500',
      'BACKTEST': 'bg-purple-500',
      'RISK_REVIEW': 'bg-orange-500',
      'IC_REVIEW': 'bg-yellow-500',
      'BOARD': 'bg-accent-primary',
    }
    return colors[stage] || 'bg-gray-500'
  }

  return (
    <div className="space-y-4">
      {cycles.map((cycle) => (
        <div key={cycle.id} className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm text-gray-200">{cycle.name}</span>
              <span className="text-xs text-gray-500 ml-2">{cycle.id}</span>
            </div>
            <span className="badge badge-neutral text-[10px]">{cycle.stage}</span>
          </div>
          <div className="h-1.5 bg-terminal-muted rounded-full overflow-hidden">
            <div
              className={`h-full ${getStageColor(cycle.stage)} transition-all`}
              style={{ width: `${cycle.progress}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  return (
    <div className="space-y-6 animate-slide-in">
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
          value="18"
          change="2 新增本周"
          changeType="positive"
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
          value="3"
          change="1 紧急"
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

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left Column - Agent Status */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-100">Agent 状态</h2>
            <Link href="/org" className="text-xs text-accent-primary hover:underline">
              查看全部
            </Link>
          </div>
          <AgentStatusList />
        </div>

        {/* Middle Column - Activity & Research */}
        <div className="space-y-6">
          {/* Pending Approvals */}
          <div className="card border-l-2 border-accent-warning">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-accent-warning" />
              <h2 className="text-lg font-semibold text-gray-100">待您审批</h2>
            </div>
            <PendingApprovals />
          </div>

          {/* Research Progress */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-100">研究进度</h2>
              <Link href="/research" className="text-xs text-accent-primary hover:underline">
                研究中心
              </Link>
            </div>
            <ResearchCycles />
          </div>
        </div>

        {/* Right Column - Activity Feed */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-100">实时动态</h2>
            <span className="flex items-center gap-1 text-xs text-accent-success">
              <span className="status-dot active"></span>
              Live
            </span>
          </div>
          <RecentActivity />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-4 gap-4">
        <Link href="/chat/cio" className="card-hover flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <Users className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-200">与 CIO 对话</div>
            <div className="text-xs text-gray-500">投资策略讨论</div>
          </div>
        </Link>
        <Link href="/trading" className="card-hover flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-primary/20 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-accent-primary" />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-200">交易台</div>
            <div className="text-xs text-gray-500">持仓与执行</div>
          </div>
        </Link>
        <Link href="/reports" className="card-hover flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <FileText className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-200">报告中心</div>
            <div className="text-xs text-gray-500">查看所有报告</div>
          </div>
        </Link>
        <Link href="/meetings" className="card-hover flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
            <Clock className="w-5 h-5 text-orange-400" />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-200">会议室</div>
            <div className="text-xs text-gray-500">查看会议记录</div>
          </div>
        </Link>
      </div>
    </div>
  )
}
