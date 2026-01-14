'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  Users,
  Building2,
  User,
  MessageSquare,
  TrendingUp,
  Shield,
  FlaskConical,
  Database,
  TestTube,
  Brain,
  Star,
  DollarSign,
} from 'lucide-react'

interface Agent {
  id: string
  name: string
  name_en: string
  role: string
  status: 'active' | 'frozen' | 'inactive'
  reputation: number
  budget: number
  tasks_completed: number
  current_task?: string
}

interface Department {
  id: string
  name: string
  name_en: string
  icon: React.ElementType
  color: string
  lead?: string
  agents: Agent[]
}

const departments: Department[] = [
  {
    id: 'board_office',
    name: '董事会办公室',
    name_en: 'Board Office',
    icon: Building2,
    color: 'text-purple-400',
    lead: 'chief_of_staff',
    agents: [
      { id: 'chief_of_staff', name: '办公室主任', name_en: 'Chief of Staff', role: 'Lead', status: 'active', reputation: 0.92, budget: 5000, tasks_completed: 156, current_task: '审核会议申请' },
      { id: 'audit_compliance', name: '合规审计', name_en: 'Audit & Compliance', role: 'Auditor', status: 'active', reputation: 0.88, budget: 3000, tasks_completed: 89 },
    ],
  },
  {
    id: 'investment_committee',
    name: '投资委员会',
    name_en: 'Investment Committee',
    icon: TrendingUp,
    color: 'text-green-400',
    agents: [
      { id: 'cio', name: '首席投资官', name_en: 'CIO', role: 'Lead', status: 'active', reputation: 0.95, budget: 10000, tasks_completed: 234, current_task: '策略评审' },
      { id: 'pm', name: '组合经理', name_en: 'Portfolio Manager', role: 'Manager', status: 'active', reputation: 0.90, budget: 8000, tasks_completed: 178 },
    ],
  },
  {
    id: 'research_guild',
    name: '研究部',
    name_en: 'Research Guild',
    icon: FlaskConical,
    color: 'text-blue-400',
    lead: 'head_of_research',
    agents: [
      { id: 'head_of_research', name: '研究总监', name_en: 'Head of Research', role: 'Lead', status: 'active', reputation: 0.93, budget: 15000, tasks_completed: 312, current_task: '组织策略赛马' },
      { id: 'alpha_a_lead', name: 'Alpha A 组长', name_en: 'Alpha A Lead', role: 'Team Lead', status: 'active', reputation: 0.87, budget: 5000, tasks_completed: 145, current_task: '因子研究' },
      { id: 'alpha_a_researcher_1', name: 'Alpha A 研究员1', name_en: 'Researcher 1', role: 'Researcher', status: 'active', reputation: 0.82, budget: 3000, tasks_completed: 98 },
      { id: 'alpha_a_researcher_2', name: 'Alpha A 研究员2', name_en: 'Researcher 2', role: 'Researcher', status: 'active', reputation: 0.79, budget: 3000, tasks_completed: 87 },
      { id: 'alpha_b_lead', name: 'Alpha B 组长', name_en: 'Alpha B Lead', role: 'Team Lead', status: 'active', reputation: 0.85, budget: 5000, tasks_completed: 134 },
      { id: 'alpha_b_researcher_1', name: 'Alpha B 研究员1', name_en: 'Researcher 1', role: 'Researcher', status: 'active', reputation: 0.80, budget: 3000, tasks_completed: 76 },
    ],
  },
  {
    id: 'risk_guild',
    name: '风控部',
    name_en: 'Risk & Skeptic Guild',
    icon: Shield,
    color: 'text-orange-400',
    agents: [
      { id: 'cro', name: '首席风险官', name_en: 'CRO', role: 'Lead', status: 'active', reputation: 0.96, budget: 8000, tasks_completed: 267, current_task: '风险评估' },
      { id: 'skeptic', name: '质疑者', name_en: 'Skeptic', role: 'Reviewer', status: 'frozen', reputation: 0.91, budget: 4000, tasks_completed: 189 },
      { id: 'black_swan', name: '黑天鹅分析师', name_en: 'Black Swan Analyst', role: 'Analyst', status: 'active', reputation: 0.84, budget: 3000, tasks_completed: 112 },
    ],
  },
  {
    id: 'trading_guild',
    name: '交易部',
    name_en: 'Trading Guild',
    icon: TrendingUp,
    color: 'text-cyan-400',
    agents: [
      { id: 'head_trader', name: '交易主管', name_en: 'Head Trader', role: 'Lead', status: 'active', reputation: 0.89, budget: 6000, tasks_completed: 198, current_task: '监控执行' },
      { id: 'execution_trader_alpha', name: '执行交易员 Alpha', name_en: 'Trader Alpha', role: 'Trader', status: 'active', reputation: 0.83, budget: 3000, tasks_completed: 156 },
      { id: 'execution_trader_beta', name: '执行交易员 Beta', name_en: 'Trader Beta', role: 'Trader', status: 'active', reputation: 0.81, budget: 3000, tasks_completed: 143 },
    ],
  },
  {
    id: 'meta_governance',
    name: '治理部',
    name_en: 'Meta-Governance',
    icon: Brain,
    color: 'text-pink-400',
    agents: [
      { id: 'cgo', name: '首席治理官', name_en: 'CGO', role: 'Lead', status: 'active', reputation: 0.98, budget: 5000, tasks_completed: 89, current_task: '合规审查' },
      { id: 'cpo', name: '首席人才官', name_en: 'CPO', role: 'Lead', status: 'active', reputation: 0.87, budget: 4000, tasks_completed: 67 },
      { id: 'cto_capability', name: '能力建设官', name_en: 'CTO*', role: 'Lead', status: 'active', reputation: 0.85, budget: 4000, tasks_completed: 54 },
    ],
  },
]

function AgentCard({ agent, departmentColor }: { agent: Agent; departmentColor: string }) {
  return (
    <Link
      href={`/chat/${agent.id}`}
      className="card-hover p-4 flex flex-col gap-3"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-terminal-muted flex items-center justify-center">
            <User className={`w-5 h-5 ${departmentColor}`} />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-200">{agent.name}</div>
            <div className="text-xs text-gray-500">{agent.name_en}</div>
          </div>
        </div>
        <span className={`status-dot ${agent.status}`}></span>
      </div>

      {agent.current_task && (
        <div className="text-xs text-gray-400 bg-terminal-muted/50 px-2 py-1 rounded">
          {agent.current_task}
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="flex items-center justify-center gap-1">
            <Star className="w-3 h-3 text-yellow-400" />
            <span className="text-sm font-medium text-gray-200">{(agent.reputation * 100).toFixed(0)}%</span>
          </div>
          <div className="text-[10px] text-gray-500">声誉</div>
        </div>
        <div>
          <div className="flex items-center justify-center gap-1">
            <DollarSign className="w-3 h-3 text-accent-primary" />
            <span className="text-sm font-medium text-gray-200">{agent.budget}</span>
          </div>
          <div className="text-[10px] text-gray-500">预算</div>
        </div>
        <div>
          <div className="text-sm font-medium text-gray-200">{agent.tasks_completed}</div>
          <div className="text-[10px] text-gray-500">任务</div>
        </div>
      </div>

      <button className="btn btn-ghost btn-sm w-full mt-auto">
        <MessageSquare className="w-4 h-4 mr-2" />
        对话
      </button>
    </Link>
  )
}

function DepartmentSection({ department }: { department: Department }) {
  const [expanded, setExpanded] = useState(true)
  const Icon = department.icon

  return (
    <div className="card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between mb-4"
      >
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg bg-terminal-muted flex items-center justify-center`}>
            <Icon className={`w-5 h-5 ${department.color}`} />
          </div>
          <div className="text-left">
            <div className="text-lg font-semibold text-gray-100">{department.name}</div>
            <div className="text-xs text-gray-500">{department.name_en} · {department.agents.length} Agents</div>
          </div>
        </div>
        <span className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {expanded && (
        <div className="grid grid-cols-3 gap-4">
          {department.agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} departmentColor={department.color} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function OrgPage() {
  const totalAgents = departments.reduce((sum, d) => sum + d.agents.length, 0)
  const activeAgents = departments.reduce(
    (sum, d) => sum + d.agents.filter((a) => a.status === 'active').length,
    0
  )

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">组织架构</h1>
          <p className="page-subtitle">AI Quant Company 人员与部门管理</p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="status-dot active"></span>
            <span className="text-gray-400">{activeAgents} 活跃</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="status-dot frozen"></span>
            <span className="text-gray-400">{totalAgents - activeAgents} 暂停</span>
          </div>
          <span className="text-gray-500">|</span>
          <span className="text-gray-300 font-medium">共 {totalAgents} 名 Agent</span>
        </div>
      </div>

      {/* Department Sections */}
      <div className="space-y-6">
        {departments.map((department) => (
          <DepartmentSection key={department.id} department={department} />
        ))}
      </div>
    </div>
  )
}
