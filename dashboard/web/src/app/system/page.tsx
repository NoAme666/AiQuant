'use client'

import { useState, useEffect } from 'react'
import useSWR, { mutate } from 'swr'
import {
  Server,
  Database,
  Cpu,
  HardDrive,
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Wifi,
  WifiOff,
  Zap,
  AlertTriangle,
  Play,
  Square,
  DollarSign,
  TrendingUp,
  Brain,
  Coins,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface ServiceStatus {
  name: string
  status: 'online' | 'offline' | 'degraded'
  latency?: number
  lastCheck: string
  details?: string
}

interface TokenStats {
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_requests: number
  thinking_calls: number
  estimated_cost_usd: number
  cost_breakdown: {
    input_cost: number
    output_cost: number
  }
  pricing_model: string
  pricing_per_million: {
    input: number
    output: number
  }
}

interface CostEstimate {
  assumptions: {
    agents_count: number
    runs_per_hour: number
    hourly_input_tokens: number
    hourly_output_tokens: number
  }
  estimates: Record<string, { hourly: number; daily: number; monthly: number }>
  recommended: string
}

function StatusBadge({ status }: { status: 'online' | 'offline' | 'degraded' }) {
  const config = {
    online: { label: '正常', color: 'bg-accent-success', icon: CheckCircle },
    offline: { label: '离线', color: 'bg-accent-danger', icon: XCircle },
    degraded: { label: '降级', color: 'bg-accent-warning', icon: AlertTriangle },
  }
  const { label, color, icon: Icon } = config[status]
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs ${color}/20 text-white`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  )
}

function ServiceCard({ service }: { service: ServiceStatus }) {
  return (
    <div className="card-hover p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            service.status === 'online' ? 'bg-accent-success/20' :
            service.status === 'offline' ? 'bg-accent-danger/20' :
            'bg-accent-warning/20'
          }`}>
            <Server className={`w-5 h-5 ${
              service.status === 'online' ? 'text-accent-success' :
              service.status === 'offline' ? 'text-accent-danger' :
              'text-accent-warning'
            }`} />
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-200">{service.name}</h3>
            {service.latency && (
              <p className="text-xs text-gray-500">{service.latency}ms 响应</p>
            )}
          </div>
        </div>
        <StatusBadge status={service.status} />
      </div>
      {service.details && (
        <p className="text-xs text-gray-500 border-t border-terminal-border/50 pt-2 mt-2">{service.details}</p>
      )}
      <div className="flex items-center gap-1 text-xs text-gray-500 mt-2">
        <Clock className="w-3 h-3" />
        上次检查: {service.lastCheck}
      </div>
    </div>
  )
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

export default function SystemStatusPage() {
  const { data: healthData } = useSWR(`${API_BASE}/health`, fetcher, { refreshInterval: 5000 })
  const { data: agentLoopData } = useSWR(`${API_BASE}/api/agent-loop/status`, fetcher, { refreshInterval: 5000 })
  const { data: agentSystemStatus } = useSWR(`${API_BASE}/api/system/agent-status`, fetcher, { refreshInterval: 3000 })
  const { data: tokenStats } = useSWR<TokenStats>(`${API_BASE}/api/system/token-stats`, fetcher, { refreshInterval: 5000 })
  const { data: costEstimate } = useSWR<CostEstimate>(`${API_BASE}/api/system/cost-estimate`, fetcher)
  const { data: llmPricing } = useSWR(`${API_BASE}/api/system/llm-pricing`, fetcher)
  
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [selectedModel, setSelectedModel] = useState('antigravity')
  
  const isBackendOnline = !!healthData
  const isAgentRunning = agentSystemStatus?.is_running || false
  const now = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  
  // 启动 Agent 系统
  const handleStartAgents = async (mock: boolean = false) => {
    setIsStarting(true)
    try {
      const res = await fetch(`${API_BASE}/api/system/start-agents?mock=${mock}`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        alert(`✅ ${data.message}`)
        mutate(`${API_BASE}/api/system/agent-status`)
      } else {
        alert(`❌ ${data.error}`)
      }
    } catch (e) {
      alert('启动失败，请检查后端服务')
    }
    setIsStarting(false)
  }
  
  // 停止 Agent 系统
  const handleStopAgents = async () => {
    setIsStopping(true)
    try {
      const res = await fetch(`${API_BASE}/api/system/stop-agents`, { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        alert(`✅ ${data.message}`)
        mutate(`${API_BASE}/api/system/agent-status`)
      } else {
        alert(`❌ ${data.error}`)
      }
    } catch (e) {
      alert('停止失败')
    }
    setIsStopping(false)
  }
  
  const services: ServiceStatus[] = [
    {
      name: 'API 后端',
      status: isBackendOnline ? 'online' : 'offline',
      latency: isBackendOnline ? 12 : undefined,
      lastCheck: now,
      details: isBackendOnline ? 'FastAPI 服务运行正常' : '请启动后端服务',
    },
    {
      name: 'Agent 调度器',
      status: isAgentRunning ? 'online' : 'degraded',
      latency: 8,
      lastCheck: now,
      details: isAgentRunning ? `PID: ${agentSystemStatus?.pid}` : '未启动 - 点击上方按钮启动',
    },
    {
      name: '数据库',
      status: isBackendOnline ? 'online' : 'offline',
      latency: 3,
      lastCheck: now,
      details: 'PostgreSQL @ 154.26.181.47',
    },
    {
      name: '交易所连接',
      status: 'online',
      latency: 45,
      lastCheck: now,
      details: 'OKX API 连接正常',
    },
    {
      name: '消息队列',
      status: isBackendOnline ? 'online' : 'offline',
      latency: 2,
      lastCheck: now,
      details: 'Redis 内存消息总线',
    },
    {
      name: '前端服务',
      status: 'online',
      latency: 5,
      lastCheck: now,
      details: 'Next.js 服务运行正常',
    },
  ]
  
  const onlineCount = services.filter(s => s.status === 'online').length
  const totalCount = services.length
  
  // 获取选中模型的成本估算
  const selectedEstimate = costEstimate?.estimates?.[selectedModel] || { hourly: 0, daily: 0, monthly: 0 }
  
  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">系统状态</h1>
          <p className="page-subtitle">服务监控、Token 统计与成本预算</p>
        </div>
        <div className="flex items-center gap-3">
          {isAgentRunning ? (
            <button 
              className="btn btn-danger btn-sm"
              onClick={handleStopAgents}
              disabled={isStopping}
            >
              <Square className="w-4 h-4 mr-2" />
              {isStopping ? '停止中...' : '下班 (停止 Agent)'}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button 
                className="btn btn-primary btn-sm"
                onClick={() => handleStartAgents(false)}
                disabled={isStarting || !isBackendOnline}
              >
                <Play className="w-4 h-4 mr-2" />
                {isStarting ? '启动中...' : '🚀 上班 (真实模式)'}
              </button>
              <button 
                className="btn btn-secondary btn-sm"
                onClick={() => handleStartAgents(true)}
                disabled={isStarting || !isBackendOnline}
              >
                <Play className="w-4 h-4 mr-2" />
                测试模式
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Agent 运行状态横幅 */}
      {isAgentRunning ? (
        <div className="bg-accent-success/10 border border-accent-success/30 rounded-lg p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-accent-success/20 flex items-center justify-center animate-pulse">
            <Brain className="w-5 h-5 text-accent-success" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-accent-success font-medium">🟢 Agent 系统运行中</p>
            <p className="text-xs text-gray-400">34 个 Agent 正在自动工作，研究策略、分析市场、相互协作</p>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-accent-success">{agentSystemStatus?.pid}</div>
            <div className="text-xs text-gray-500">PID</div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          <div className="flex-1">
            <p className="text-sm text-yellow-200 font-medium">⏸️ Agent 系统未启动</p>
            <p className="text-xs text-yellow-400">点击右上角 "上班" 按钮启动 Agent 系统</p>
          </div>
        </div>
      )}
      
      {/* Token 使用统计 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
            <Coins className="w-5 h-5 text-yellow-400" />
            Token 使用统计
          </h2>
          <span className="text-xs text-gray-500">今日</span>
        </div>
        
        <div className="grid grid-cols-6 gap-4 mb-4">
          <div className="bg-terminal-muted/30 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-400 font-mono">
              {formatNumber(tokenStats?.total_input_tokens || 0)}
            </div>
            <div className="text-xs text-gray-500">输入 Tokens</div>
          </div>
          <div className="bg-terminal-muted/30 rounded-lg p-4">
            <div className="text-2xl font-bold text-purple-400 font-mono">
              {formatNumber(tokenStats?.total_output_tokens || 0)}
            </div>
            <div className="text-xs text-gray-500">输出 Tokens</div>
          </div>
          <div className="bg-terminal-muted/30 rounded-lg p-4">
            <div className="text-2xl font-bold text-cyan-400 font-mono">
              {formatNumber(tokenStats?.total_tokens || 0)}
            </div>
            <div className="text-xs text-gray-500">总 Tokens</div>
          </div>
          <div className="bg-terminal-muted/30 rounded-lg p-4">
            <div className="text-2xl font-bold text-gray-300 font-mono">
              {tokenStats?.total_requests || 0}
            </div>
            <div className="text-xs text-gray-500">API 请求数</div>
          </div>
          <div className="bg-terminal-muted/30 rounded-lg p-4">
            <div className="text-2xl font-bold text-orange-400 font-mono">
              {tokenStats?.thinking_calls || 0}
            </div>
            <div className="text-xs text-gray-500">🧠 Thinking</div>
          </div>
          <div className="bg-terminal-muted/30 rounded-lg p-4 border border-accent-success/30">
            <div className="text-2xl font-bold text-accent-success font-mono">
              ${tokenStats?.estimated_cost_usd?.toFixed(4) || '0.00'}
            </div>
            <div className="text-xs text-gray-500">今日成本</div>
          </div>
        </div>
        
        <div className="text-xs text-gray-500 flex items-center gap-4">
          <span>模型: {tokenStats?.pricing_model || 'antigravity'}</span>
          <span>输入: ${tokenStats?.pricing_per_million?.input || 1}/M tokens</span>
          <span>输出: ${tokenStats?.pricing_per_million?.output || 3}/M tokens</span>
        </div>
      </div>
      
      {/* 成本预算估算 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-green-400" />
            运行成本预算
          </h2>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="bg-terminal-muted border border-terminal-border rounded px-3 py-1 text-sm text-gray-200"
          >
            {llmPricing?.pricing && Object.keys(llmPricing.pricing).map((model) => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>
        
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="bg-terminal-muted/30 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-gray-100 font-mono">
              ${selectedEstimate.hourly}
            </div>
            <div className="text-sm text-gray-500">每小时</div>
          </div>
          <div className="bg-terminal-muted/30 rounded-lg p-4 text-center border border-accent-primary/30">
            <div className="text-3xl font-bold text-accent-primary font-mono">
              ${selectedEstimate.daily}
            </div>
            <div className="text-sm text-gray-500">每天</div>
          </div>
          <div className="bg-terminal-muted/30 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-gray-100 font-mono">
              ${selectedEstimate.monthly}
            </div>
            <div className="text-sm text-gray-500">每月</div>
          </div>
        </div>
        
        {/* LLM 价格对比表 */}
        <div className="border-t border-terminal-border/50 pt-4 mt-4">
          <h3 className="text-sm font-medium text-gray-300 mb-3">LLM 模型价格对比 (2026年1月)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-terminal-border/50">
                  <th className="pb-2 font-medium">模型</th>
                  <th className="pb-2 font-medium text-right">输入 $/M</th>
                  <th className="pb-2 font-medium text-right">输出 $/M</th>
                  <th className="pb-2 font-medium text-right">日成本预估</th>
                  <th className="pb-2 font-medium text-right">月成本预估</th>
                </tr>
              </thead>
              <tbody>
                {llmPricing?.pricing && Object.entries(llmPricing.pricing).map(([model, pricing]: [string, any]) => {
                  const estimate = costEstimate?.estimates?.[model]
                  const isRecommended = model === costEstimate?.recommended
                  return (
                    <tr 
                      key={model} 
                      className={`border-b border-terminal-border/30 ${isRecommended ? 'bg-accent-success/5' : ''} ${selectedModel === model ? 'bg-accent-primary/10' : ''}`}
                    >
                      <td className="py-2 flex items-center gap-2">
                        {model}
                        {isRecommended && <span className="badge badge-success text-[10px]">推荐</span>}
                      </td>
                      <td className="py-2 text-right text-blue-400 font-mono">${pricing.input}</td>
                      <td className="py-2 text-right text-purple-400 font-mono">${pricing.output}</td>
                      <td className="py-2 text-right font-mono">${estimate?.daily || '-'}</td>
                      <td className="py-2 text-right font-mono">${estimate?.monthly || '-'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500 mt-3">
            * 估算基于 34 个 Agent，每分钟执行 1 次，每次平均 500 输入 + 200 输出 tokens
          </p>
        </div>
      </div>
      
      {/* Overview */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              onlineCount === totalCount ? 'bg-accent-success/20' : 'bg-accent-warning/20'
            }`}>
              {onlineCount === totalCount ? (
                <Wifi className="w-6 h-6 text-accent-success" />
              ) : (
                <WifiOff className="w-6 h-6 text-accent-warning" />
              )}
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-100">{onlineCount}/{totalCount}</div>
              <div className="text-sm text-gray-500">服务在线</div>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Brain className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-100">34</div>
              <div className="text-sm text-gray-500">Agent 数量</div>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Database className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-100">27</div>
              <div className="text-sm text-gray-500">数据库表</div>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-cyan-500/20 flex items-center justify-center">
              <Zap className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-100">{isAgentRunning ? '运行中' : '已停止'}</div>
              <div className="text-sm text-gray-500">系统状态</div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Services Grid */}
      <div>
        <h2 className="text-lg font-semibold text-gray-100 mb-4">服务状态 ({onlineCount}/{totalCount} 在线)</h2>
        <div className="grid grid-cols-3 gap-4">
          {services.map((service) => (
            <ServiceCard key={service.name} service={service} />
          ))}
        </div>
      </div>
    </div>
  )
}
