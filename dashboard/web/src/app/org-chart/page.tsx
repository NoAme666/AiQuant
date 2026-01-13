'use client'

import { useState } from 'react'
import Link from 'next/link'
import { 
  ArrowLeft, 
  Building2, 
  User, 
  MessageSquare,
  Wallet,
  Star,
  ChevronRight
} from 'lucide-react'

// 部门数据
const departments = [
  {
    id: 'board_office',
    name: '董事会办公室',
    nameEn: 'Board Office',
    color: 'text-purple-400',
    bgColor: 'bg-purple-400/10',
    agents: [
      { id: 'chief_of_staff', name: '办公室主任', nameEn: 'Chief of Staff', isLead: true, status: 'active', budget: 180, reputation: 0.85 },
      { id: 'audit_compliance', name: '合规审计', nameEn: 'Audit & Compliance', isLead: false, status: 'active', budget: 150, reputation: 0.78 },
    ]
  },
  {
    id: 'investment_committee',
    name: '投资委员会',
    nameEn: 'Investment Committee',
    color: 'text-blue-400',
    bgColor: 'bg-blue-400/10',
    agents: [
      { id: 'cio', name: '首席投资官', nameEn: 'CIO', isLead: true, status: 'active', budget: 180, reputation: 0.82 },
      { id: 'pm', name: '组合经理', nameEn: 'Portfolio Manager', isLead: true, status: 'active', budget: 160, reputation: 0.75 },
    ]
  },
  {
    id: 'research_guild',
    name: '研究部',
    nameEn: 'Research Guild',
    color: 'text-accent-primary',
    bgColor: 'bg-accent-primary/10',
    agents: [
      { id: 'head_of_research', name: '研究总监', nameEn: 'Head of Research', isLead: true, status: 'active', budget: 150, reputation: 0.88, currentTask: '评审中' },
      { id: 'alpha_a_lead', name: 'Alpha A 组长', nameEn: 'Alpha A Lead', isLead: true, status: 'active', budget: 800, reputation: 0.72, currentTask: '回测中' },
      { id: 'alpha_a_r1', name: 'Alpha A 研究员1', nameEn: 'Researcher 1', isLead: false, status: 'active', budget: 0, reputation: 0.68 },
      { id: 'alpha_a_r2', name: 'Alpha A 研究员2', nameEn: 'Researcher 2', isLead: false, status: 'active', budget: 0, reputation: 0.71 },
      { id: 'alpha_b_lead', name: 'Alpha B 组长', nameEn: 'Alpha B Lead', isLead: true, status: 'active', budget: 650, reputation: 0.69 },
      { id: 'alpha_b_r1', name: 'Alpha B 研究员1', nameEn: 'Researcher 1', isLead: false, status: 'active', budget: 0, reputation: 0.65 },
      { id: 'alpha_b_r2', name: 'Alpha B 研究员2', nameEn: 'Researcher 2', isLead: false, status: 'frozen', budget: 0, reputation: 0.45 },
    ]
  },
  {
    id: 'data_guild',
    name: '数据部',
    nameEn: 'Data Guild',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-400/10',
    agents: [
      { id: 'data_engineering_lead', name: '数据工程主管', nameEn: 'Data Engineering Lead', isLead: true, status: 'active', budget: 600, reputation: 0.80 },
      { id: 'data_engineer', name: '数据工程师', nameEn: 'Data Engineer', isLead: false, status: 'active', budget: 0, reputation: 0.72 },
      { id: 'data_quality_auditor', name: '数据质量审计', nameEn: 'Data Quality Auditor', isLead: true, status: 'active', budget: 180, reputation: 0.85, hasVeto: true },
    ]
  },
  {
    id: 'backtest_guild',
    name: '回测部',
    nameEn: 'Backtest Guild',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-400/10',
    agents: [
      { id: 'backtest_lead', name: '回测主管', nameEn: 'Backtest Lead', isLead: true, status: 'active', budget: 1200, reputation: 0.78, currentTask: '实验运行中' },
      { id: 'tcost_modeler', name: '交易成本建模', nameEn: 'TCost Modeler', isLead: false, status: 'active', budget: 250, reputation: 0.76 },
      { id: 'robustness_lab', name: '鲁棒性实验室', nameEn: 'Robustness Lab', isLead: false, status: 'active', budget: 400, reputation: 0.74 },
    ]
  },
  {
    id: 'risk_guild',
    name: '风控部',
    nameEn: 'Risk & Skeptic Guild',
    color: 'text-orange-400',
    bgColor: 'bg-orange-400/10',
    agents: [
      { id: 'cro', name: '首席风险官', nameEn: 'CRO', isLead: true, status: 'active', budget: 250, reputation: 0.90, hasVeto: true },
      { id: 'skeptic', name: '质疑者', nameEn: 'Skeptic', isLead: true, status: 'active', budget: 180, reputation: 0.82, currentTask: '审查策略' },
      { id: 'black_swan', name: '黑天鹅分析师', nameEn: 'Black Swan', isLead: false, status: 'active', budget: 150, reputation: 0.75 },
    ]
  },
]

// Agent 卡片组件
function AgentCard({ agent, onClick }: { agent: any; onClick: () => void }) {
  return (
    <div 
      onClick={onClick}
      className="card-hover flex items-center gap-4 group"
    >
      <div className="relative">
        <div className="w-12 h-12 rounded-full bg-terminal-muted flex items-center justify-center">
          <User className="w-6 h-6 text-gray-400" />
        </div>
        <span className={`absolute -bottom-1 -right-1 status-dot ${agent.status}`}></span>
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-medium text-gray-100 truncate">{agent.name}</h4>
          {agent.isLead && (
            <span className="badge-info text-xs">Lead</span>
          )}
          {agent.hasVeto && (
            <span className="badge-danger text-xs">否决权</span>
          )}
        </div>
        <p className="text-sm text-gray-400 truncate">{agent.nameEn}</p>
        {agent.currentTask && (
          <p className="text-xs text-accent-primary mt-1">{agent.currentTask}</p>
        )}
      </div>
      
      <div className="text-right">
        <div className="flex items-center gap-1 text-sm">
          <Star className="w-3 h-3 text-accent-primary" />
          <span className="text-gray-300">{(agent.reputation * 100).toFixed(0)}%</span>
        </div>
        {agent.budget > 0 && (
          <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
            <Wallet className="w-3 h-3" />
            <span>{agent.budget}</span>
          </div>
        )}
      </div>
      
      <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-accent-primary transition-colors" />
    </div>
  )
}

export default function OrgChartPage() {
  const [selectedAgent, setSelectedAgent] = useState<any>(null)

  return (
    <div className="min-h-screen p-6">
      {/* 顶部导航 */}
      <header className="flex items-center gap-4 mb-8">
        <Link href="/" className="p-2 rounded-lg hover:bg-terminal-muted transition-colors">
          <ArrowLeft className="w-5 h-5 text-gray-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2">
            <Building2 className="w-6 h-6 text-accent-primary" />
            组织架构
          </h1>
          <p className="text-gray-400">查看各部门与 Agent 状态</p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {departments.map(dept => (
          <div key={dept.id} className="card">
            <div className={`flex items-center gap-3 mb-4 pb-3 border-b border-terminal-border`}>
              <div className={`w-10 h-10 rounded-lg ${dept.bgColor} flex items-center justify-center`}>
                <Building2 className={`w-5 h-5 ${dept.color}`} />
              </div>
              <div>
                <h3 className={`font-semibold ${dept.color}`}>{dept.name}</h3>
                <p className="text-xs text-gray-500">{dept.nameEn}</p>
              </div>
              <span className="ml-auto badge-info">{dept.agents.length} 人</span>
            </div>
            
            <div className="space-y-2">
              {dept.agents.map(agent => (
                <AgentCard 
                  key={agent.id}
                  agent={agent}
                  onClick={() => setSelectedAgent(agent)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Agent 详情弹窗 */}
      {selectedAgent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setSelectedAgent(null)}>
          <div className="card w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-4 mb-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-full bg-terminal-muted flex items-center justify-center">
                  <User className="w-8 h-8 text-gray-400" />
                </div>
                <span className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full ${selectedAgent.status === 'active' ? 'bg-accent-success' : 'bg-accent-warning'}`}></span>
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-100">{selectedAgent.name}</h2>
                <p className="text-gray-400">{selectedAgent.nameEn}</p>
              </div>
            </div>
            
            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">状态</span>
                <span className={selectedAgent.status === 'active' ? 'text-accent-success' : 'text-accent-warning'}>
                  {selectedAgent.status === 'active' ? '活跃' : '冻结'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">声誉分数</span>
                <span className="text-gray-100">{(selectedAgent.reputation * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">预算剩余</span>
                <span className="text-gray-100">{selectedAgent.budget} 点</span>
              </div>
              {selectedAgent.currentTask && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">当前任务</span>
                  <span className="text-accent-primary">{selectedAgent.currentTask}</span>
                </div>
              )}
            </div>
            
            <div className="flex gap-3">
              <Link 
                href={`/chat/${selectedAgent.id}`}
                className="btn-primary flex-1 text-center"
              >
                <MessageSquare className="w-4 h-4 mr-2 inline" />
                发起对话
              </Link>
              <button 
                onClick={() => setSelectedAgent(null)}
                className="btn-secondary flex-1"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
