'use client'

import { useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { 
  User, 
  Activity, 
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock,
  ChevronRight,
  Building2,
  FlaskConical,
  Shield,
  Brain,
  Users
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const fetcher = (url: string) => fetch(url).then(res => res.json())

interface Agent {
  id: string
  name: string
  name_en: string
  department: string
  is_lead: boolean
  status: string
  budget_remaining: number
  reputation_score: number
  current_task?: string
}

interface Department {
  id: string
  name: string
  name_en: string
  agents: Agent[]
}

const departmentIcons: Record<string, React.ElementType> = {
  board_office: Building2,
  research_guild: FlaskConical,
  risk_oversight: Shield,
  data_engineering: Brain,
  backtest_infra: Activity,
  meta_governance: Users,
}

const statusColors: Record<string, { bg: string; text: string; dot: string }> = {
  active: { bg: 'bg-accent-success/10', text: 'text-accent-success', dot: 'bg-accent-success' },
  busy: { bg: 'bg-accent-warning/10', text: 'text-accent-warning', dot: 'bg-accent-warning' },
  idle: { bg: 'bg-gray-500/10', text: 'text-gray-400', dot: 'bg-gray-400' },
  frozen: { bg: 'bg-accent-danger/10', text: 'text-accent-danger', dot: 'bg-accent-danger' },
}

function AgentCard({ agent, compact = false }: { agent: Agent; compact?: boolean }) {
  const status = statusColors[agent.status] || statusColors.idle
  const reputationPercent = Math.round(agent.reputation_score * 100)
  
  if (compact) {
    return (
      <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-terminal-muted/50 transition-colors">
        <div className="relative">
          <div className="w-8 h-8 rounded-full bg-terminal-muted flex items-center justify-center text-xs font-bold text-accent-primary">
            {agent.name.slice(0, 2)}
          </div>
          <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full ${status.dot} ring-2 ring-terminal-bg`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-100 truncate">{agent.name}</div>
          {agent.current_task && (
            <div className="text-xs text-gray-500 truncate">{agent.current_task}</div>
          )}
        </div>
        <div className="text-xs font-mono text-gray-400">{reputationPercent}%</div>
      </div>
    )
  }
  
  return (
    <Link
      href={`/chat/${agent.id}`}
      className="block p-4 bg-terminal-card border border-terminal-border rounded-lg hover:border-accent-primary/50 transition-colors group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-terminal-muted flex items-center justify-center text-sm font-bold text-accent-primary">
              {agent.name.slice(0, 2)}
            </div>
            <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full ${status.dot} ring-2 ring-terminal-card`} />
          </div>
          <div>
            <div className="font-medium text-gray-100 group-hover:text-accent-primary transition-colors">
              {agent.name}
            </div>
            <div className="text-xs text-gray-500">{agent.name_en}</div>
          </div>
        </div>
        {agent.is_lead && (
          <span className="px-2 py-0.5 text-xs font-medium bg-accent-primary/20 text-accent-primary rounded">
            Lead
          </span>
        )}
      </div>
      
      {/* 状态和任务 */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`px-2 py-0.5 text-xs font-medium rounded ${status.bg} ${status.text}`}>
          {agent.status === 'active' ? '活跃' : agent.status === 'busy' ? '忙碌' : agent.status === 'frozen' ? '冻结' : '空闲'}
        </span>
        {agent.current_task && (
          <span className="text-xs text-gray-500 truncate">{agent.current_task}</span>
        )}
      </div>
      
      {/* 指标 */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1 text-gray-400">
          <Zap className="w-3.5 h-3.5" />
          <span className="font-mono">{agent.budget_remaining}</span>
          <span className="text-xs">CP</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-16 h-1.5 bg-terminal-muted rounded-full overflow-hidden">
            <div 
              className="h-full bg-accent-primary rounded-full transition-all"
              style={{ width: `${reputationPercent}%` }}
            />
          </div>
          <span className="font-mono text-xs text-gray-400">{reputationPercent}%</span>
        </div>
      </div>
    </Link>
  )
}

function DepartmentSection({ department }: { department: Department }) {
  const [expanded, setExpanded] = useState(true)
  const Icon = departmentIcons[department.id] || Building2
  
  const activeCount = department.agents.filter(a => a.status === 'active').length
  
  return (
    <div className="border border-terminal-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-terminal-muted/30 hover:bg-terminal-muted/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon className="w-5 h-5 text-accent-primary" />
          <div className="text-left">
            <div className="font-medium text-gray-100">{department.name}</div>
            <div className="text-xs text-gray-500">{department.name_en}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            {activeCount}/{department.agents.length} 活跃
          </span>
          <ChevronRight className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        </div>
      </button>
      
      {expanded && (
        <div className="p-3 space-y-2">
          {department.agents.map(agent => (
            <AgentCard key={agent.id} agent={agent} compact />
          ))}
        </div>
      )}
    </div>
  )
}

export default function AgentStatusPanel() {
  const { data, error, isLoading } = useSWR<Department[]>(
    `${API_BASE}/api/org-chart`,
    fetcher,
    { refreshInterval: 30000 }
  )
  
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse bg-terminal-muted rounded-lg h-32" />
        ))}
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex items-center gap-2 text-accent-danger p-4">
        <AlertTriangle className="w-4 h-4" />
        <span>加载组织架构失败</span>
      </div>
    )
  }
  
  const departments = data || []
  const totalAgents = departments.reduce((sum, d) => sum + d.agents.length, 0)
  const activeAgents = departments.reduce(
    (sum, d) => sum + d.agents.filter(a => a.status === 'active').length,
    0
  )
  
  return (
    <div className="space-y-4">
      {/* 总览 */}
      <div className="flex items-center justify-between p-3 bg-terminal-card border border-terminal-border rounded-lg">
        <div className="flex items-center gap-3">
          <Users className="w-5 h-5 text-accent-primary" />
          <span className="font-medium text-gray-100">Agent 状态</span>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-accent-success" />
            <span className="text-gray-400">{activeAgents} 活跃</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-gray-400" />
            <span className="text-gray-400">{totalAgents - activeAgents} 其他</span>
          </div>
        </div>
      </div>
      
      {/* 部门列表 */}
      <div className="space-y-3">
        {departments.map(dept => (
          <DepartmentSection key={dept.id} department={dept} />
        ))}
      </div>
    </div>
  )
}

// 紧凑版 Agent 列表（用于侧边栏）
export function AgentListCompact() {
  const { data, isLoading } = useSWR<Department[]>(
    `${API_BASE}/api/org-chart`,
    fetcher,
    { refreshInterval: 30000 }
  )
  
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="animate-pulse bg-terminal-muted rounded h-10" />
        ))}
      </div>
    )
  }
  
  const agents = data?.flatMap(d => d.agents) || []
  
  return (
    <div className="space-y-1">
      {agents.slice(0, 8).map(agent => (
        <AgentCard key={agent.id} agent={agent} compact />
      ))}
      {agents.length > 8 && (
        <Link
          href="/org-chart"
          className="block text-center text-sm text-accent-primary hover:underline py-2"
        >
          查看全部 {agents.length} 个 Agent →
        </Link>
      )}
    </div>
  )
}
