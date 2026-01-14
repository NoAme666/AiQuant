'use client'

import { useState } from 'react'
import Link from 'next/link'
import useSWR from 'swr'
import {
  Building2,
  Users,
  FlaskConical,
  TrendingUp,
  Shield,
  Brain,
  Settings,
  MessageSquare,
  ArrowRight,
  Clock,
  CheckCircle,
  Circle,
  Briefcase,
  Target,
  Coffee,
  AlertTriangle,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface Agent {
  id: string
  name: string
  name_en: string
  role: string
  current_task: string | null
}

interface Department {
  id: string
  name: string
  name_en: string
  icon: React.ElementType
  color: string
  bgColor: string
  description: string
  agents: Agent[]
}

// 部门和员工数据
const departmentsData: Department[] = [
  {
    id: 'board_office',
    name: '董事会办公室',
    name_en: 'Board Office',
    icon: Building2,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    description: '公司最高决策层',
    agents: [
      { id: 'chairman', name: '董事长', name_en: 'Chairman', role: 'C-Level', current_task: '审批策略提案' },
      { id: 'chief_of_staff', name: '办公室主任', name_en: 'Chief of Staff', role: 'Lead', current_task: '协调各部门会议' },
    ],
  },
  {
    id: 'investment_office',
    name: '投资办公室',
    name_en: 'Investment Office',
    icon: Briefcase,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    description: '投资决策与执行',
    agents: [
      { id: 'cio', name: 'CIO 首席投资官', name_en: 'Chief Investment Officer', role: 'C-Level', current_task: '评审 Alpha 策略' },
      { id: 'pm', name: '投资组合经理', name_en: 'Portfolio Manager', role: 'Lead', current_task: '组合再平衡分析' },
    ],
  },
  {
    id: 'research_guild',
    name: '研究部',
    name_en: 'Research Guild',
    icon: FlaskConical,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/20',
    description: '策略研究与开发',
    agents: [
      { id: 'head_of_research', name: '研究总监', name_en: 'Head of Research', role: 'Lead', current_task: '主持策略评审会' },
      { id: 'alpha_a_lead', name: 'Alpha A 组长', name_en: 'Alpha A Lead', role: 'Lead', current_task: 'BTC 动量策略研究' },
      { id: 'alpha_a_researcher_1', name: 'Alpha A 研究员', name_en: 'Researcher 1', role: 'Member', current_task: '回测参数优化' },
      { id: 'alpha_b_lead', name: 'Alpha B 组长', name_en: 'Alpha B Lead', role: 'Lead', current_task: 'ETH 均值回归' },
      { id: 'alpha_b_researcher_1', name: 'Alpha B 研究员', name_en: 'Researcher 2', role: 'Member', current_task: null },
      { id: 'quant_dev', name: '量化开发', name_en: 'Quant Dev', role: 'Member', current_task: '工具开发' },
    ],
  },
  {
    id: 'risk_guild',
    name: '风控部',
    name_en: 'Risk Guild',
    icon: Shield,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    description: '风险评估与合规',
    agents: [
      { id: 'cro', name: 'CRO 首席风险官', name_en: 'Chief Risk Officer', role: 'C-Level', current_task: '风险敞口评估' },
      { id: 'skeptic', name: '质疑者', name_en: 'Skeptic', role: 'Member', current_task: '策略漏洞分析' },
      { id: 'black_swan', name: '黑天鹅猎手', name_en: 'Black Swan Hunter', role: 'Member', current_task: null },
    ],
  },
  {
    id: 'trading_guild',
    name: '交易部',
    name_en: 'Trading Guild',
    icon: TrendingUp,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    description: '交易执行与监控',
    agents: [
      { id: 'head_trader', name: '交易主管', name_en: 'Head Trader', role: 'Lead', current_task: '监控执行队列' },
      { id: 'execution_trader_1', name: '执行交易员 A', name_en: 'Exec Trader A', role: 'Member', current_task: 'BTC 订单执行' },
      { id: 'execution_trader_2', name: '执行交易员 B', name_en: 'Exec Trader B', role: 'Member', current_task: 'ETH 订单执行' },
      { id: 'algo_trader', name: '算法交易', name_en: 'Algo Trader', role: 'Member', current_task: null },
    ],
  },
  {
    id: 'intelligence_guild',
    name: '情报部',
    name_en: 'Intelligence Guild',
    icon: Brain,
    color: 'text-pink-400',
    bgColor: 'bg-pink-500/20',
    description: '市场情报与分析',
    agents: [
      { id: 'head_of_intelligence', name: '情报总监', name_en: 'Head of Intelligence', role: 'Lead', current_task: '市场情绪报告' },
      { id: 'news_analyst', name: '新闻分析师', name_en: 'News Analyst', role: 'Member', current_task: '新闻抓取与摘要' },
      { id: 'sentiment_analyst', name: '情绪分析师', name_en: 'Sentiment Analyst', role: 'Member', current_task: '恐惧贪婪指数' },
      { id: 'social_monitor', name: '社交监控', name_en: 'Social Monitor', role: 'Member', current_task: 'Twitter 热点' },
      { id: 'onchain_analyst', name: '链上分析', name_en: 'On-chain Analyst', role: 'Member', current_task: null },
    ],
  },
]

function AgentCard({ agent, deptColor, isSystemRunning }: { agent: Agent; deptColor: string; isSystemRunning: boolean }) {
  // 根据系统是否运行决定状态
  const status = isSystemRunning ? (agent.current_task ? 'active' : 'idle') : 'off'
  
  const statusConfig = {
    active: { label: '工作中', dotColor: 'bg-accent-success', textColor: 'text-gray-200' },
    idle: { label: '空闲', dotColor: 'bg-gray-400', textColor: 'text-gray-400' },
    off: { label: '未上班', dotColor: 'bg-gray-600', textColor: 'text-gray-500' },
  }
  const config = statusConfig[status]
  
  const displayTask = isSystemRunning 
    ? (agent.current_task || '等待任务分配')
    : '系统未启动'

  return (
    <Link
      href={`/chat/${agent.id}`}
      className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
        isSystemRunning 
          ? 'bg-terminal-muted/30 hover:bg-terminal-muted/50' 
          : 'bg-terminal-muted/10 opacity-60'
      } group`}
    >
      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold ${
        isSystemRunning ? deptColor.replace('text-', 'bg-').replace('400', '500/20') : 'bg-gray-800'
      } ${isSystemRunning ? deptColor : 'text-gray-500'}`}>
        {agent.name.slice(0, 1)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${config.textColor}`}>{agent.name}</span>
          {agent.role === 'C-Level' && (
            <span className="badge badge-primary text-[8px]">C</span>
          )}
          {agent.role === 'Lead' && (
            <span className="badge badge-neutral text-[8px]">Lead</span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`}></span>
          <span className={`text-xs truncate ${isSystemRunning ? 'text-gray-500' : 'text-gray-600'}`}>
            {displayTask}
          </span>
        </div>
      </div>
      <ArrowRight className={`w-4 h-4 transition-colors ${
        isSystemRunning ? 'text-gray-600 group-hover:text-accent-primary' : 'text-gray-700'
      }`} />
    </Link>
  )
}

function DepartmentSection({ dept, isSystemRunning }: { dept: Department; isSystemRunning: boolean }) {
  const Icon = dept.icon
  const activeCount = isSystemRunning 
    ? dept.agents.filter(a => a.current_task).length 
    : 0

  return (
    <div id={dept.id} className="card scroll-mt-20">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-lg ${isSystemRunning ? dept.bgColor : 'bg-gray-800/50'} flex items-center justify-center`}>
            <Icon className={`w-6 h-6 ${isSystemRunning ? dept.color : 'text-gray-500'}`} />
          </div>
          <div>
            <h2 className={`text-lg font-semibold ${isSystemRunning ? 'text-gray-100' : 'text-gray-400'}`}>{dept.name}</h2>
            <p className="text-xs text-gray-500">{dept.name_en} · {dept.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isSystemRunning ? (
            <>
              <span className={`text-xs ${dept.color}`}>{activeCount} 活跃</span>
              <span className="text-xs text-gray-500">/ {dept.agents.length} 人</span>
            </>
          ) : (
            <span className="text-xs text-gray-600 flex items-center gap-1">
              <Coffee className="w-3 h-3" />
              下班中
            </span>
          )}
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        {dept.agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} deptColor={dept.color} isSystemRunning={isSystemRunning} />
        ))}
      </div>
    </div>
  )
}

export default function OrganizationPage() {
  // 检查系统是否真正运行
  const { data: agentSystemStatus } = useSWR(`${API_BASE}/api/system/agent-status`, fetcher, { refreshInterval: 3000 })
  
  const isSystemRunning = agentSystemStatus?.is_running || false
  
  const totalAgents = departmentsData.reduce((sum, d) => sum + d.agents.length, 0)
  const activeAgents = isSystemRunning
    ? departmentsData.reduce((sum, d) => sum + d.agents.filter(a => a.current_task).length, 0)
    : 0

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">组织架构</h1>
          <p className="page-subtitle">AI Quant Company · 虚拟办公室</p>
        </div>
        <div className="flex items-center gap-4">
          {isSystemRunning ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="status-dot active"></span>
              <span className="text-accent-success">{activeAgents} 活跃</span>
              <span className="text-gray-600">/</span>
              <span className="text-gray-500">{totalAgents} 总人数</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
              <Coffee className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-yellow-300">全员下班中</span>
            </div>
          )}
        </div>
      </div>

      {/* 系统未启动提示 */}
      {!isSystemRunning && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-yellow-200 font-medium">Agent 系统未启动</p>
            <p className="text-xs text-yellow-400">请前往「系统状态」页面点击「上班」按钮启动 Agent 系统</p>
          </div>
          <Link href="/system" className="btn btn-warning btn-sm">
            前往启动
          </Link>
        </div>
      )}

      {/* Quick Nav */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {departmentsData.map((dept) => {
          const Icon = dept.icon
          return (
            <a
              key={dept.id}
              href={`#${dept.id}`}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-opacity shrink-0 ${
                isSystemRunning ? dept.bgColor : 'bg-gray-800/50'
              } ${isSystemRunning ? 'hover:opacity-80' : 'opacity-50'}`}
            >
              <Icon className={`w-4 h-4 ${isSystemRunning ? dept.color : 'text-gray-500'}`} />
              <span className={`text-sm ${isSystemRunning ? dept.color : 'text-gray-500'}`}>{dept.name}</span>
            </a>
          )
        })}
      </div>

      {/* Office Layout - 2 column grid */}
      <div className="grid grid-cols-2 gap-6">
        {departmentsData.map((dept) => (
          <DepartmentSection key={dept.id} dept={dept} isSystemRunning={isSystemRunning} />
        ))}
      </div>

      {/* Legend */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-400 mb-3">图例说明</h3>
        <div className="flex items-center gap-6 text-xs text-gray-500">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent-success"></span>
            工作中
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-gray-400"></span>
            空闲
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-gray-600"></span>
            未上班
          </div>
          <div className="flex items-center gap-1.5">
            <span className="badge badge-primary text-[8px]">C</span>
            C-Level
          </div>
          <div className="flex items-center gap-1.5">
            <span className="badge badge-neutral text-[8px]">Lead</span>
            部门负责人
          </div>
        </div>
      </div>
    </div>
  )
}
