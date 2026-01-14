'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import useSWR from 'swr'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  ArrowLeft,
  Download,
  Play,
  RefreshCw,
  Clock,
  Target,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Lightbulb,
  MessageSquare,
  User,
  Calendar,
  Activity,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface BacktestResult {
  id: string
  strategy_name: string
  strategy_type: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  start_date: string
  end_date: string
  run_time: string
  metrics: {
    total_return: number
    annual_return: number
    sharpe_ratio: number
    sortino_ratio: number
    max_drawdown: number
    win_rate: number
    profit_factor: number
    calmar_ratio: number
    total_trades: number
    avg_trade_duration: string
  }
  monthly_returns: { month: string; return: number }[]
  drawdown_periods: { start: string; end: string; drawdown: number; recovery_days: number }[]
  team_evaluation: {
    overall_score: number
    verdict: string
    strengths: string[]
    weaknesses: string[]
    improvements: string[]
    evaluators: { agent_id: string; agent_name: string; score: number; comment: string }[]
  }
}

// Mock data
const backtestResult: BacktestResult = {
  id: 'RC-2026-001',
  strategy_name: 'BTC 动量突破策略',
  strategy_type: 'Momentum',
  status: 'completed',
  progress: 100,
  start_date: '2024-01-01',
  end_date: '2025-12-31',
  run_time: '12 分钟',
  metrics: {
    total_return: 0.485,
    annual_return: 0.242,
    sharpe_ratio: 1.85,
    sortino_ratio: 2.34,
    max_drawdown: -0.12,
    win_rate: 0.58,
    profit_factor: 1.82,
    calmar_ratio: 1.42,
    total_trades: 156,
    avg_trade_duration: '4.2 天',
  },
  monthly_returns: [
    { month: '2024-01', return: 0.05 },
    { month: '2024-02', return: 0.08 },
    { month: '2024-03', return: -0.02 },
    { month: '2024-04', return: 0.04 },
    { month: '2024-05', return: 0.06 },
    { month: '2024-06', return: -0.03 },
    { month: '2024-07', return: 0.07 },
    { month: '2024-08', return: 0.03 },
    { month: '2024-09', return: -0.01 },
    { month: '2024-10', return: 0.05 },
    { month: '2024-11', return: 0.09 },
    { month: '2024-12', return: 0.04 },
  ],
  drawdown_periods: [
    { start: '2024-03-10', end: '2024-03-25', drawdown: -0.08, recovery_days: 12 },
    { start: '2024-06-15', end: '2024-07-10', drawdown: -0.12, recovery_days: 18 },
    { start: '2024-09-01', end: '2024-09-08', drawdown: -0.05, recovery_days: 5 },
  ],
  team_evaluation: {
    overall_score: 82,
    verdict: '推荐',
    strengths: [
      '策略逻辑清晰，基于成熟的动量因子',
      '风险调整收益良好，Sharpe 1.85',
      '最大回撤可控，-12% 在可接受范围',
    ],
    weaknesses: [
      '在极端市场波动时表现一般',
      '换手率较高，可能产生较多滑点',
      '对参数敏感度较高',
    ],
    improvements: [
      '增加成交量过滤条件，减少虚假突破',
      '优化止损逻辑，考虑使用跟踪止损',
      '测试在不同市场环境下的稳定性',
      '考虑融入宏观经济因子作为过滤',
    ],
    evaluators: [
      { agent_id: 'head_of_research', agent_name: '研究总监', score: 85, comment: '策略思路清晰，建议进入下一阶段' },
      { agent_id: 'cro', agent_name: 'CRO', score: 78, comment: '风险指标达标，但需要加强极端情景测试' },
      { agent_id: 'skeptic', agent_name: '质疑者', score: 72, comment: '对参数敏感度有担忧，建议增加鲁棒性测试' },
      { agent_id: 'pm', agent_name: '投资组合经理', score: 88, comment: '与现有组合相关性低，适合配置' },
    ],
  },
}

function MetricCard({
  label,
  value,
  format = 'number',
  positive_is_good = true,
}: {
  label: string
  value: number | string
  format?: 'number' | 'percent' | 'ratio'
  positive_is_good?: boolean
}) {
  let displayValue: string
  let isPositive = true

  if (typeof value === 'number') {
    if (format === 'percent') {
      displayValue = `${(value * 100).toFixed(2)}%`
      isPositive = positive_is_good ? value >= 0 : value <= 0
    } else if (format === 'ratio') {
      displayValue = value.toFixed(2)
      isPositive = positive_is_good ? value >= 1 : value <= 1
    } else {
      displayValue = value.toFixed(2)
      isPositive = positive_is_good ? value >= 0 : value <= 0
    }
  } else {
    displayValue = value
  }

  return (
    <div className="bg-terminal-muted/30 rounded-lg p-3 text-center">
      <div className={`text-xl font-bold ${
        typeof value === 'number'
          ? isPositive ? 'text-accent-success' : 'text-accent-danger'
          : 'text-gray-200'
      }`}>
        {displayValue}
      </div>
      <div className="text-[10px] text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function MonthlyReturnBar({ month, value }: { month: string; value: number }) {
  const isPositive = value >= 0
  const height = Math.abs(value) * 500 // Scale factor

  return (
    <div className="flex flex-col items-center">
      <div className="h-20 flex items-end">
        <div
          className={`w-6 rounded-t ${isPositive ? 'bg-accent-success' : 'bg-accent-danger'}`}
          style={{ height: `${Math.max(height, 4)}px` }}
        />
      </div>
      <div className="text-[10px] text-gray-500 mt-1">{month.split('-')[1]}月</div>
      <div className={`text-[10px] ${isPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
        {isPositive ? '+' : ''}{(value * 100).toFixed(1)}%
      </div>
    </div>
  )
}

function EvaluatorCard({ evaluator }: { evaluator: BacktestResult['team_evaluation']['evaluators'][0] }) {
  return (
    <div className="p-3 bg-terminal-muted/30 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <Link href={`/chat/${evaluator.agent_id}`} className="text-sm font-medium text-accent-primary hover:underline">
          {evaluator.agent_name}
        </Link>
        <span className={`text-lg font-bold ${
          evaluator.score >= 80 ? 'text-accent-success' :
          evaluator.score >= 60 ? 'text-yellow-400' :
          'text-accent-danger'
        }`}>
          {evaluator.score}
        </span>
      </div>
      <p className="text-xs text-gray-400">{evaluator.comment}</p>
    </div>
  )
}

export default function BacktestDetailPage() {
  const params = useParams()
  const id = params.id
  
  // 从 API 获取真实回测数据
  const { data: result } = useSWR<BacktestResult>(
    id ? `${API_BASE}/api/v2/backtests/${id}` : null,
    fetcher,
    { refreshInterval: 5000 }
  )
  
  // 如果 API 返回 404 或数据不存在，使用默认数据
  const backtestData: BacktestResult = result || backtestResult

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/research" className="btn btn-ghost btn-sm p-2">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-mono">{backtestData.id}</span>
              <span className={`badge ${
                backtestData.status === 'completed' ? 'badge-success' :
                backtestData.status === 'running' ? 'badge-info' :
                'badge-danger'
              } text-[10px]`}>
                {backtestData.status === 'completed' ? '已完成' : backtestData.status === 'running' ? '运行中' : '失败'}
              </span>
            </div>
            <h1 className="page-title">{backtestData.strategy_name}</h1>
            <p className="page-subtitle">{backtestData.strategy_type} · 回测结果详情</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary btn-sm">
            <Download className="w-4 h-4 mr-2" />
            导出报告
          </button>
          <button className="btn btn-primary btn-sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            重新回测
          </button>
        </div>
      </div>

      {/* Backtest Info */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6 text-sm text-gray-400">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              回测区间: {backtestData.start_date} ~ {backtestData.end_date}
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              运行时间: {backtestData.run_time}
            </div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              交易次数: {backtestData.metrics.total_trades}
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div>
        <h2 className="text-lg font-semibold text-gray-100 mb-4">核心指标</h2>
        <div className="grid grid-cols-5 gap-4">
          <MetricCard label="总收益" value={backtestData.metrics.total_return} format="percent" />
          <MetricCard label="年化收益" value={backtestData.metrics.annual_return} format="percent" />
          <MetricCard label="Sharpe" value={backtestData.metrics.sharpe_ratio} format="ratio" />
          <MetricCard label="最大回撤" value={backtestData.metrics.max_drawdown} format="percent" positive_is_good={false} />
          <MetricCard label="胜率" value={backtestData.metrics.win_rate} format="percent" />
        </div>
        <div className="grid grid-cols-5 gap-4 mt-4">
          <MetricCard label="Sortino" value={backtestData.metrics.sortino_ratio} format="ratio" />
          <MetricCard label="盈亏比" value={backtestData.metrics.profit_factor} format="ratio" />
          <MetricCard label="Calmar" value={backtestData.metrics.calmar_ratio} format="ratio" />
          <MetricCard label="交易次数" value={backtestData.metrics.total_trades} />
          <MetricCard label="平均持仓" value={backtestData.metrics.avg_trade_duration} />
        </div>
      </div>

      {/* Monthly Returns */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">月度收益</h2>
        <div className="flex items-end justify-between gap-2 overflow-x-auto pb-2">
          {backtestData.monthly_returns.map((m) => (
            <MonthlyReturnBar key={m.month} month={m.month} value={m.return} />
          ))}
        </div>
      </div>

      {/* Drawdown Periods */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-100 mb-4">回撤分析</h2>
        <table className="table w-full">
          <thead>
            <tr className="text-xs text-gray-500">
              <th className="text-left">开始日期</th>
              <th className="text-left">恢复日期</th>
              <th className="text-right">最大回撤</th>
              <th className="text-right">恢复天数</th>
            </tr>
          </thead>
          <tbody>
            {backtestData.drawdown_periods.map((period, idx) => (
              <tr key={idx} className="border-b border-terminal-border/50">
                <td className="py-2 text-sm text-gray-300">{period.start}</td>
                <td className="py-2 text-sm text-gray-300">{period.end}</td>
                <td className="py-2 text-sm text-accent-danger text-right">{(period.drawdown * 100).toFixed(2)}%</td>
                <td className="py-2 text-sm text-gray-400 text-right">{period.recovery_days} 天</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Team Evaluation */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">团队评价</h2>
          <div className="flex items-center gap-3">
            <span className={`text-3xl font-bold ${
              backtestData.team_evaluation.overall_score >= 80 ? 'text-accent-success' :
              backtestData.team_evaluation.overall_score >= 60 ? 'text-yellow-400' :
              'text-accent-danger'
            }`}>
              {backtestData.team_evaluation.overall_score}
            </span>
            <span className={`badge ${
              backtestData.team_evaluation.verdict === '强烈推荐' ? 'badge-success' :
              backtestData.team_evaluation.verdict === '推荐' ? 'badge-info' :
              backtestData.team_evaluation.verdict === '继续研究' ? 'badge-warning' :
              'badge-danger'
            }`}>
              {backtestData.team_evaluation.verdict}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 mb-6">
          {/* Strengths */}
          <div>
            <h3 className="text-sm font-medium text-accent-success flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4" />
              优势
            </h3>
            <ul className="space-y-1">
              {backtestData.team_evaluation.strengths.map((s, i) => (
                <li key={i} className="text-xs text-gray-400 flex items-start gap-2">
                  <span className="text-accent-success mt-1">•</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>

          {/* Weaknesses */}
          <div>
            <h3 className="text-sm font-medium text-accent-danger flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4" />
              不足
            </h3>
            <ul className="space-y-1">
              {backtestData.team_evaluation.weaknesses.map((w, i) => (
                <li key={i} className="text-xs text-gray-400 flex items-start gap-2">
                  <span className="text-accent-danger mt-1">•</span>
                  {w}
                </li>
              ))}
            </ul>
          </div>

          {/* Improvements */}
          <div>
            <h3 className="text-sm font-medium text-yellow-400 flex items-center gap-2 mb-2">
              <Lightbulb className="w-4 h-4" />
              改进建议
            </h3>
            <ul className="space-y-1">
              {backtestData.team_evaluation.improvements.map((imp, i) => (
                <li key={i} className="text-xs text-gray-400 flex items-start gap-2">
                  <span className="text-yellow-400 mt-1">•</span>
                  {imp}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Evaluators */}
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">评审意见</h3>
          <div className="grid grid-cols-2 gap-3">
            {backtestData.team_evaluation.evaluators.map((e) => (
              <EvaluatorCard key={e.agent_id} evaluator={e} />
            ))}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3">
        <Link href="/research" className="btn btn-secondary btn-sm">
          返回研究中心
        </Link>
        <button className="btn btn-primary btn-sm">
          提交进入下一阶段
        </button>
      </div>
    </div>
  )
}
