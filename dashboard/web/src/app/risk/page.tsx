'use client'

import { useState, useEffect } from 'react'
import {
  Shield,
  Plus,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Users,
  Vote,
  Activity,
  TrendingDown,
  Percent,
  Scale,
} from 'lucide-react'

interface RiskRule {
  id: string
  name: string
  description: string
  rule_type: string
  status: string
  parameters: Record<string, any>
  proposer_id: string
  proposer_name: string
  approval_rate: number
  votes_count: number
  required_voters: string[]
  created_at: string
  effective_from: string | null
}

interface ComplianceCheck {
  compliant: boolean
  violations: Array<{ rule_id: string; rule_name: string; message: string; severity: string }>
  warnings: Array<{ rule_id: string; rule_name: string; message: string }>
  rules_checked: number
}

const ruleTypeConfig: Record<string, { label: string; icon: any; color: string }> = {
  position_limit: { label: '仓位限制', icon: Percent, color: 'text-blue-400' },
  risk_limit: { label: '风险限制', icon: Shield, color: 'text-orange-400' },
  trading_limit: { label: '交易限制', icon: Activity, color: 'text-purple-400' },
  exposure_limit: { label: '敞口限制', icon: TrendingDown, color: 'text-yellow-400' },
  loss_limit: { label: '亏损限制', icon: AlertTriangle, color: 'text-red-400' },
  concentration_limit: { label: '集中度限制', icon: Scale, color: 'text-green-400' },
  liquidity_rule: { label: '流动性规则', icon: Activity, color: 'text-cyan-400' },
  strategy_allocation: { label: '策略配置', icon: Shield, color: 'text-pink-400' },
}

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  draft: { label: '草稿', color: 'text-gray-400', bg: 'bg-gray-500/20' },
  proposed: { label: '已提议', color: 'text-blue-400', bg: 'bg-blue-500/20' },
  voting: { label: '投票中', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  approved: { label: '已批准', color: 'text-green-400', bg: 'bg-green-500/20' },
  rejected: { label: '已拒绝', color: 'text-red-400', bg: 'bg-red-500/20' },
  active: { label: '生效中', color: 'text-accent-primary', bg: 'bg-accent-primary/20' },
  suspended: { label: '已暂停', color: 'text-orange-400', bg: 'bg-orange-500/20' },
}

function RuleCard({ rule, onVote }: { rule: RiskRule; onVote: (id: string, vote: string) => void }) {
  const typeConfig = ruleTypeConfig[rule.rule_type] || ruleTypeConfig.risk_limit
  const status = statusConfig[rule.status] || statusConfig.draft
  const Icon = typeConfig.icon

  return (
    <div className="card-hover p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${status.bg}`}>
            <Icon className={`w-5 h-5 ${typeConfig.color}`} />
          </div>
          <div>
            <h3 className="text-base font-medium text-gray-100">{rule.name}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{rule.description}</p>
          </div>
        </div>
        <span className={`badge text-[10px] ${status.bg} ${status.color}`}>
          {status.label}
        </span>
      </div>

      {/* Parameters */}
      <div className="mb-3 p-2 bg-terminal-muted/30 rounded-lg">
        <div className="text-xs text-gray-500 mb-1">规则参数</div>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(rule.parameters).slice(0, 4).map(([key, value]) => (
            <div key={key} className="flex justify-between">
              <span className="text-xs text-gray-400">{key}:</span>
              <span className="text-xs text-gray-200 font-mono">
                {typeof value === 'number' ? value.toLocaleString() : String(value)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Voting Progress (for voting status) */}
      {rule.status === 'voting' && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-500">投票进度</span>
            <span className="text-gray-400">{rule.approval_rate.toFixed(0)}% 同意</span>
          </div>
          <div className="h-1.5 bg-terminal-muted rounded-full overflow-hidden">
            <div
              className={`h-full ${rule.approval_rate >= 60 ? 'bg-accent-success' : 'bg-yellow-500'}`}
              style={{ width: `${rule.approval_rate}%` }}
            />
          </div>
          <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
            <Users className="w-3 h-3" />
            {rule.votes_count} 票 / 需要: {rule.required_voters.join(', ')}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-terminal-border/50">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Clock className="w-3 h-3" />
          <span>{new Date(rule.created_at).toLocaleDateString('zh-CN')}</span>
          <span>by {rule.proposer_name}</span>
        </div>
        <div className="flex items-center gap-2">
          {rule.status === 'voting' && (
            <>
              <button
                onClick={() => onVote(rule.id, 'approve')}
                className="btn btn-sm py-1 px-2 text-xs bg-green-500/20 text-green-400 hover:bg-green-500/30"
              >
                <CheckCircle className="w-3 h-3 mr-1" />
                同意
              </button>
              <button
                onClick={() => onVote(rule.id, 'reject')}
                className="btn btn-sm py-1 px-2 text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30"
              >
                <XCircle className="w-3 h-3 mr-1" />
                反对
              </button>
            </>
          )}
          {rule.status === 'approved' && (
            <button className="btn btn-primary btn-sm py-1 px-2 text-xs">
              激活
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function RiskPage() {
  const [rules, setRules] = useState<RiskRule[]>([])
  const [activeRules, setActiveRules] = useState<RiskRule[]>([])
  const [compliance, setCompliance] = useState<ComplianceCheck | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [rulesRes, activeRes] = await Promise.all([
        fetch('http://localhost:8000/api/governance/rules'),
        fetch('http://localhost:8000/api/governance/rules/active'),
      ])
      
      const rulesData = await rulesRes.json()
      const activeData = await activeRes.json()
      
      setRules(rulesData.rules || [])
      setActiveRules(activeData.rules || [])

      // Mock compliance check
      setCompliance({
        compliant: true,
        violations: [],
        warnings: [
          { rule_id: '1', rule_name: '总杠杆限制', message: '当前杠杆 2.3x 接近 3x 限制' },
        ],
        rules_checked: activeData.count || 4,
      })
    } catch (err) {
      console.error('Failed to fetch rules:', err)
      // Mock data
      setRules([
        {
          id: '1',
          name: '单一资产仓位上限',
          description: '任何单一资产的仓位不得超过总资产的 30%',
          rule_type: 'concentration_limit',
          status: 'active',
          parameters: { max_single_asset_pct: 30, applies_to: 'all' },
          proposer_id: 'system',
          proposer_name: '系统默认',
          approval_rate: 100,
          votes_count: 3,
          required_voters: ['cro', 'pm', 'cio'],
          created_at: '2026-01-01T00:00:00Z',
          effective_from: '2026-01-01T00:00:00Z',
        },
        {
          id: '2',
          name: '调整日内亏损限制',
          description: '提议将日内亏损限制从 5% 降低到 3%',
          rule_type: 'loss_limit',
          status: 'voting',
          parameters: { max_daily_loss_pct: 3, action: 'force_close' },
          proposer_id: 'cro',
          proposer_name: '首席风险官',
          approval_rate: 67,
          votes_count: 2,
          required_voters: ['cro', 'cio', 'chairman'],
          created_at: '2026-01-13T10:00:00Z',
          effective_from: null,
        },
      ])
      setActiveRules([])
      setCompliance({
        compliant: true,
        violations: [],
        warnings: [{ rule_id: '1', rule_name: '杠杆限制', message: '接近限额' }],
        rules_checked: 4,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleVote = async (ruleId: string, vote: string) => {
    try {
      await fetch(`http://localhost:8000/api/governance/rules/${ruleId}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voter_id: 'chairman',
          voter_name: '董事长',
          department: 'board',
          vote: vote,
          reason: vote === 'approve' ? '同意该规则调整' : '不同意该规则调整',
        }),
      })
      fetchData()
    } catch (err) {
      console.error('Failed to vote:', err)
    }
  }

  const filteredRules = filter === 'all'
    ? rules
    : filter === 'active'
    ? rules.filter(r => r.status === 'active')
    : rules.filter(r => r.status === 'voting')

  const stats = {
    total: rules.length,
    active: rules.filter(r => r.status === 'active').length,
    voting: rules.filter(r => r.status === 'voting').length,
    compliant: compliance?.compliant ?? true,
  }

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">风控治理</h1>
          <p className="page-subtitle">风险规则管理与合规监控</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-primary btn-sm">
            <Plus className="w-4 h-4 mr-2" />
            提议新规则
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="text-2xl font-bold text-gray-100">{stats.total}</div>
          <div className="text-sm text-gray-500">总规则数</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-accent-primary">{stats.active}</div>
          <div className="text-sm text-gray-500">生效中</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-yellow-400">{stats.voting}</div>
          <div className="text-sm text-gray-500">投票中</div>
        </div>
        <div className="card">
          <div className="flex items-center gap-2">
            {stats.compliant ? (
              <>
                <CheckCircle className="w-6 h-6 text-accent-success" />
                <div>
                  <div className="text-lg font-bold text-accent-success">合规</div>
                  <div className="text-xs text-gray-500">
                    {compliance?.warnings.length || 0} 警告
                  </div>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="w-6 h-6 text-accent-danger" />
                <div>
                  <div className="text-lg font-bold text-accent-danger">违规</div>
                  <div className="text-xs text-gray-500">
                    {compliance?.violations.length || 0} 违规项
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Compliance Status */}
      {compliance && compliance.warnings.length > 0 && (
        <div className="card border-yellow-500/30">
          <h3 className="text-base font-semibold text-gray-100 flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
            合规警告
          </h3>
          <div className="space-y-2">
            {compliance.warnings.map((w, i) => (
              <div key={i} className="flex items-center gap-3 p-2 bg-yellow-500/10 rounded-lg">
                <span className="text-xs text-yellow-400 font-medium">{w.rule_name}</span>
                <span className="text-xs text-gray-400">{w.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-terminal-border">
        {[
          { key: 'all', label: '全部' },
          { key: 'active', label: '生效中' },
          { key: 'voting', label: '投票中' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`pb-3 px-1 text-sm border-b-2 transition-colors ${
              filter === tab.key
                ? 'border-accent-primary text-accent-primary'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Rules Grid */}
      {loading ? (
        <div className="text-center text-gray-500 py-10">加载中...</div>
      ) : filteredRules.length === 0 ? (
        <div className="text-center text-gray-500 py-10">暂无规则</div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {filteredRules.map(rule => (
            <RuleCard key={rule.id} rule={rule} onVote={handleVote} />
          ))}
        </div>
      )}
    </div>
  )
}
