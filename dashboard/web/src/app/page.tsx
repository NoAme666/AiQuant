'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  Building2, 
  GitBranch, 
  FlaskConical, 
  FileText, 
  Users, 
  MessageSquare,
  Activity,
  Wallet,
  Star,
  AlertTriangle
} from 'lucide-react'

// 统计卡片组件
function StatCard({ 
  title, 
  value, 
  icon: Icon, 
  trend, 
  color = 'primary' 
}: { 
  title: string
  value: string | number
  icon: React.ElementType
  trend?: { value: number; label: string }
  color?: 'primary' | 'success' | 'warning' | 'danger'
}) {
  const colorClasses = {
    primary: 'text-accent-primary',
    success: 'text-accent-success',
    warning: 'text-accent-warning',
    danger: 'text-accent-danger',
  }

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400">{title}</p>
          <p className={`text-3xl font-bold mt-1 ${colorClasses[color]}`}>{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trend.value >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
              {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg bg-terminal-muted ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}

// 快捷入口卡片
function QuickAccessCard({ 
  title, 
  description, 
  href, 
  icon: Icon 
}: { 
  title: string
  description: string
  href: string
  icon: React.ElementType
}) {
  return (
    <Link href={href} className="card-hover group">
      <div className="flex items-center gap-4">
        <div className="p-3 rounded-lg bg-terminal-muted group-hover:bg-accent-primary/20 transition-colors">
          <Icon className="w-6 h-6 text-accent-primary" />
        </div>
        <div>
          <h3 className="font-medium text-gray-100">{title}</h3>
          <p className="text-sm text-gray-400">{description}</p>
        </div>
      </div>
    </Link>
  )
}

// 活动流项目
function ActivityItem({ 
  actor, 
  action, 
  target, 
  time 
}: { 
  actor: string
  action: string
  target: string
  time: string
}) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-terminal-border last:border-0">
      <div className="w-8 h-8 rounded-full bg-terminal-muted flex items-center justify-center text-xs font-medium text-accent-primary">
        {actor.slice(0, 2).toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm">
          <span className="font-medium text-gray-100">{actor}</span>
          <span className="text-gray-400"> {action} </span>
          <span className="text-accent-primary">{target}</span>
        </p>
        <p className="text-xs text-gray-500 mt-0.5">{time}</p>
      </div>
    </div>
  )
}

// 待处理事项
function PendingItem({ 
  title, 
  type, 
  priority 
}: { 
  title: string
  type: string
  priority: 'high' | 'medium' | 'low'
}) {
  const priorityColors = {
    high: 'badge-danger',
    medium: 'badge-warning',
    low: 'badge-info',
  }

  return (
    <div className="flex items-center justify-between py-2 border-b border-terminal-border last:border-0">
      <div className="flex items-center gap-3">
        <AlertTriangle className={`w-4 h-4 ${
          priority === 'high' ? 'text-accent-danger' : 
          priority === 'medium' ? 'text-accent-warning' : 
          'text-gray-400'
        }`} />
        <span className="text-sm">{title}</span>
      </div>
      <span className={priorityColors[priority]}>{type}</span>
    </div>
  )
}

export default function LobbyPage() {
  const [stats, setStats] = useState({
    activeCycles: 0,
    pendingApprovals: 0,
    totalExperiments: 0,
    totalAgents: 0,
    budgetUtilization: 0,
    avgReputation: 0,
  })

  useEffect(() => {
    // 模拟数据加载
    setStats({
      activeCycles: 3,
      pendingApprovals: 5,
      totalExperiments: 127,
      totalAgents: 18,
      budgetUtilization: 0.65,
      avgReputation: 0.72,
    })
  }, [])

  return (
    <div className="min-h-screen p-6">
      {/* 顶部导航 */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">AI Quant Company</h1>
          <p className="text-gray-400">董事长办公室 Dashboard</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2 text-sm text-gray-400">
            <span className="status-dot active"></span>
            系统运行中
          </span>
          <button className="btn-secondary">
            <MessageSquare className="w-4 h-4 mr-2 inline" />
            消息
          </button>
        </div>
      </header>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard 
          title="活跃研究周期" 
          value={stats.activeCycles} 
          icon={GitBranch}
          color="primary"
        />
        <StatCard 
          title="待审批事项" 
          value={stats.pendingApprovals} 
          icon={AlertTriangle}
          color="warning"
        />
        <StatCard 
          title="总实验数" 
          value={stats.totalExperiments} 
          icon={FlaskConical}
          color="success"
        />
        <StatCard 
          title="预算使用率" 
          value={`${(stats.budgetUtilization * 100).toFixed(0)}%`} 
          icon={Wallet}
          trend={{ value: 5, label: '本周' }}
          color="primary"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：快捷入口 */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold text-gray-100 mb-4">快捷入口</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <QuickAccessCard 
              title="组织架构" 
              description="查看各部门与 Agent 状态" 
              href="/org-chart"
              icon={Building2}
            />
            <QuickAccessCard 
              title="研究流水线" 
              description="跟踪策略研究进度" 
              href="/pipeline"
              icon={GitBranch}
            />
            <QuickAccessCard 
              title="实验库" 
              description="查看所有回测实验" 
              href="/experiments"
              icon={FlaskConical}
            />
            <QuickAccessCard 
              title="报告中心" 
              description="董事会报告与研究报告" 
              href="/reports"
              icon={FileText}
            />
            <QuickAccessCard 
              title="会议中心" 
              description="会议申请与审批" 
              href="/meetings"
              icon={Users}
            />
            <QuickAccessCard 
              title="风险监控" 
              description="实时风险指标与告警" 
              href="/risk"
              icon={Activity}
            />
          </div>

          {/* 最近活动 */}
          <div className="card mt-6">
            <h3 className="font-medium text-gray-100 mb-4">最近活动</h3>
            <div className="space-y-1">
              <ActivityItem 
                actor="Alpha A Lead"
                action="提交了策略到"
                target="ROBUSTNESS_GATE"
                time="5 分钟前"
              />
              <ActivityItem 
                actor="CRO"
                action="批准了会议申请"
                target="策略评审会议"
                time="15 分钟前"
              />
              <ActivityItem 
                actor="Data Auditor"
                action="完成数据审核"
                target="BTC 动量策略"
                time="1 小时前"
              />
              <ActivityItem 
                actor="Skeptic"
                action="要求补充实验"
                target="ETH 均值回归"
                time="2 小时前"
              />
            </div>
          </div>
        </div>

        {/* 右侧：待处理事项 & 声誉排行 */}
        <div className="space-y-6">
          {/* 待处理事项 */}
          <div className="card">
            <h3 className="font-medium text-gray-100 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-accent-warning" />
              待处理事项
            </h3>
            <div className="space-y-1">
              <PendingItem 
                title="BTC 策略待董事会决策"
                type="决策"
                priority="high"
              />
              <PendingItem 
                title="Alpha B 会议待审批"
                type="会议"
                priority="medium"
              />
              <PendingItem 
                title="风控报告待阅读"
                type="报告"
                priority="low"
              />
            </div>
            <Link href="/approvals" className="block text-center text-sm text-accent-primary mt-4 hover:underline">
              查看全部 →
            </Link>
          </div>

          {/* 声誉排行 */}
          <div className="card">
            <h3 className="font-medium text-gray-100 mb-4 flex items-center gap-2">
              <Star className="w-4 h-4 text-accent-primary" />
              声誉排行
            </h3>
            <div className="space-y-3">
              {[
                { name: 'Alpha A Lead', score: 0.85, trend: 'up' },
                { name: 'CRO', score: 0.82, trend: 'stable' },
                { name: 'Data Auditor', score: 0.78, trend: 'up' },
                { name: 'Backtest Lead', score: 0.75, trend: 'down' },
              ].map((agent, i) => (
                <div key={agent.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-terminal-muted flex items-center justify-center text-xs font-bold text-accent-primary">
                      {i + 1}
                    </span>
                    <span className="text-sm">{agent.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{(agent.score * 100).toFixed(0)}%</span>
                    <span className={`text-xs ${
                      agent.trend === 'up' ? 'text-accent-success' : 
                      agent.trend === 'down' ? 'text-accent-danger' : 
                      'text-gray-400'
                    }`}>
                      {agent.trend === 'up' ? '↑' : agent.trend === 'down' ? '↓' : '—'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <Link href="/reputation" className="block text-center text-sm text-accent-primary mt-4 hover:underline">
              查看详情 →
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
