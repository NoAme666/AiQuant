'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import useSWR, { mutate } from 'swr'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle,
  Play,
  Pause,
  RefreshCw,
  Shield,
  BarChart3,
  Target,
  Zap,
  ArrowUp,
  ArrowDown,
  Circle,
  Square,
} from 'lucide-react'
import PriceChart from '@/components/PriceChart'
import { MarketTickerStatic } from '@/components/MarketTicker'
import * as api from '@/lib/api-v2'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface Signal {
  id: string
  type: 'buy' | 'sell'
  symbol: string
  price: number
  target_price: number
  stop_loss: number
  take_profit: number
  quantity: number
  confidence: number
  strategy: string
  timestamp: string
  status: 'pending' | 'executed' | 'cancelled' | 'expired'
  pnl?: number
  pnl_pct?: number
  win_probability: number
  risk_reward: number
  position_size_pct: number
}

interface Position {
  symbol: string
  side: 'long' | 'short'
  quantity: number
  entry_price: number
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  stop_loss: number
  take_profit: number
}

interface TradingPlan {
  id: string
  name: string
  state: string
  strategy_type: string
  signals: Signal[]
  realized_pnl: number
  win_rate: number
  total_trades: number
  sharpe: number
}

// 默认空数据
const defaultSignals: Signal[] = []
const defaultPositions: Position[] = []
const defaultPlans: TradingPlan[] = []

// 仓位可视化组件 - 显示止损止盈框
function PositionVisualization({ position }: { position: Position }) {
  const { entry_price, current_price, stop_loss, take_profit, side } = position
  const isLong = side === 'long'
  
  // 计算价格范围
  const priceRange = take_profit - stop_loss
  const entryPct = ((entry_price - stop_loss) / priceRange) * 100
  const currentPct = ((current_price - stop_loss) / priceRange) * 100
  
  // 距离止损/止盈的百分比
  const distanceToSL = isLong 
    ? ((current_price - stop_loss) / (entry_price - stop_loss) - 1) * 100
    : ((stop_loss - current_price) / (stop_loss - entry_price) - 1) * 100
  const distanceToTP = isLong
    ? ((take_profit - current_price) / (take_profit - entry_price) - 1) * 100
    : ((current_price - take_profit) / (entry_price - take_profit) - 1) * 100

  return (
    <div className="bg-terminal-muted/30 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`badge ${isLong ? 'badge-success' : 'badge-danger'} text-[10px]`}>
            {isLong ? 'LONG' : 'SHORT'}
          </span>
          <span className="text-sm font-medium text-gray-200">{position.symbol}</span>
        </div>
        <span className={`text-sm font-mono ${position.unrealized_pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
          {position.unrealized_pnl >= 0 ? '+' : ''}${position.unrealized_pnl.toFixed(2)}
        </span>
      </div>
      
      {/* 仓位图 */}
      <div className="relative h-8 bg-terminal-bg rounded overflow-hidden mb-2">
        {/* 止损区域 (红色) */}
        <div 
          className="absolute left-0 top-0 bottom-0 bg-accent-danger/30"
          style={{ width: `${Math.max(entryPct - 5, 0)}%` }}
        />
        {/* 止盈区域 (绿色) */}
        <div 
          className="absolute right-0 top-0 bottom-0 bg-accent-success/30"
          style={{ width: `${Math.max(100 - entryPct - 5, 0)}%` }}
        />
        {/* 入场价位线 */}
        <div 
          className="absolute top-0 bottom-0 w-0.5 bg-gray-400"
          style={{ left: `${entryPct}%` }}
        />
        {/* 当前价位指示器 */}
        <div 
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-white bg-accent-primary"
          style={{ left: `${Math.min(Math.max(currentPct, 2), 98)}%`, transform: 'translate(-50%, -50%)' }}
        />
      </div>
      
      {/* 价格标签 */}
      <div className="flex items-center justify-between text-[10px]">
        <div className="text-accent-danger">
          SL: ${stop_loss.toLocaleString()}
        </div>
        <div className="text-gray-400">
          入场: ${entry_price.toLocaleString()}
        </div>
        <div className="text-accent-success">
          TP: ${take_profit.toLocaleString()}
        </div>
      </div>
      
      {/* 当前状态 */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-terminal-border/50">
        <div className="text-xs text-gray-500">
          当前: <span className="text-gray-200 font-mono">${current_price.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="text-accent-danger">距SL: {distanceToSL.toFixed(1)}%</span>
          <span className="text-accent-success">距TP: {distanceToTP.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  )
}

// 信号卡片组件
function SignalCard({ signal, onExecute, onCancel }: { 
  signal: Signal
  onExecute: (id: string) => void
  onCancel: (id: string) => void
}) {
  const isBuy = signal.type === 'buy'
  const isPending = signal.status === 'pending'
  
  return (
    <div className={`card-hover p-3 ${isPending ? 'border-l-2 border-accent-warning' : ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`w-6 h-6 rounded flex items-center justify-center ${
            isBuy ? 'bg-accent-success/20' : 'bg-accent-danger/20'
          }`}>
            {isBuy ? (
              <ArrowUp className="w-4 h-4 text-accent-success" />
            ) : (
              <ArrowDown className="w-4 h-4 text-accent-danger" />
            )}
          </span>
          <div>
            <div className="flex items-center gap-1">
              <span className="text-sm font-medium text-gray-200">{signal.symbol}</span>
              <span className={`badge ${isBuy ? 'badge-success' : 'badge-danger'} text-[8px]`}>
                {isBuy ? 'BUY' : 'SELL'}
              </span>
            </div>
            <span className="text-[10px] text-gray-500">{signal.strategy}</span>
          </div>
        </div>
        <div className="text-right">
          <span className={`badge ${
            signal.status === 'pending' ? 'badge-warning' :
            signal.status === 'executed' ? 'badge-success' :
            'badge-neutral'
          } text-[10px]`}>
            {signal.status === 'pending' ? '待执行' :
             signal.status === 'executed' ? '已执行' :
             signal.status === 'cancelled' ? '已取消' : '已过期'}
          </span>
          <div className="text-[10px] text-gray-500 mt-0.5">{signal.timestamp}</div>
        </div>
      </div>
      
      {/* 价格信息 */}
      <div className="grid grid-cols-4 gap-2 mb-2 py-2 border-y border-terminal-border/50">
        <div className="text-center">
          <div className="text-sm font-mono text-gray-200">${signal.price.toLocaleString()}</div>
          <div className="text-[10px] text-gray-500">入场价</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-mono text-accent-danger">${signal.stop_loss.toLocaleString()}</div>
          <div className="text-[10px] text-gray-500">止损</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-mono text-accent-success">${signal.take_profit.toLocaleString()}</div>
          <div className="text-[10px] text-gray-500">止盈</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-mono text-gray-200">{signal.quantity}</div>
          <div className="text-[10px] text-gray-500">数量</div>
        </div>
      </div>
      
      {/* 指标 */}
      <div className="grid grid-cols-4 gap-2 mb-3">
        <div className="text-center bg-terminal-muted/30 rounded p-1.5">
          <div className={`text-sm font-bold ${signal.win_probability >= 0.6 ? 'text-accent-success' : signal.win_probability >= 0.5 ? 'text-yellow-400' : 'text-accent-danger'}`}>
            {(signal.win_probability * 100).toFixed(0)}%
          </div>
          <div className="text-[10px] text-gray-500">胜率</div>
        </div>
        <div className="text-center bg-terminal-muted/30 rounded p-1.5">
          <div className={`text-sm font-bold ${signal.risk_reward >= 2 ? 'text-accent-success' : 'text-yellow-400'}`}>
            {signal.risk_reward.toFixed(1)}
          </div>
          <div className="text-[10px] text-gray-500">盈亏比</div>
        </div>
        <div className="text-center bg-terminal-muted/30 rounded p-1.5">
          <div className={`text-sm font-bold ${signal.confidence >= 0.7 ? 'text-accent-success' : 'text-yellow-400'}`}>
            {(signal.confidence * 100).toFixed(0)}%
          </div>
          <div className="text-[10px] text-gray-500">置信度</div>
        </div>
        <div className="text-center bg-terminal-muted/30 rounded p-1.5">
          <div className="text-sm font-bold text-gray-200">
            {(signal.position_size_pct * 100).toFixed(0)}%
          </div>
          <div className="text-[10px] text-gray-500">仓位</div>
        </div>
      </div>
      
      {/* 已执行的盈亏 */}
      {signal.status === 'executed' && signal.pnl !== undefined && (
        <div className={`mb-3 p-2 rounded ${signal.pnl >= 0 ? 'bg-accent-success/10' : 'bg-accent-danger/10'}`}>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">执行盈亏</span>
            <span className={`text-sm font-bold ${signal.pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
              {signal.pnl >= 0 ? '+' : ''}${signal.pnl.toFixed(2)} ({(signal.pnl_pct! * 100).toFixed(2)}%)
            </span>
          </div>
        </div>
      )}
      
      {/* 操作按钮 */}
      {isPending && (
        <div className="flex items-center gap-2">
          <button 
            onClick={() => onCancel(signal.id)}
            className="btn btn-ghost btn-sm flex-1 text-gray-400 hover:text-accent-danger"
          >
            <XCircle className="w-4 h-4 mr-1" />
            忽略
          </button>
          <button 
            onClick={() => onExecute(signal.id)}
            className="btn btn-primary btn-sm flex-1"
          >
            <Play className="w-4 h-4 mr-1" />
            执行
          </button>
        </div>
      )}
    </div>
  )
}

// 交易计划卡片
function TradingPlanCard({ plan }: { plan: TradingPlan }) {
  const stateColors: Record<string, { badge: string; label: string }> = {
    'DRAFT': { badge: 'badge-neutral', label: '草稿' },
    'SIMULATION': { badge: 'badge-info', label: '模拟中' },
    'PENDING_CHAIRMAN': { badge: 'badge-warning', label: '待审批' },
    'APPROVED': { badge: 'badge-success', label: '已批准' },
    'MONITORING': { badge: 'badge-success', label: '执行中' },
    'CLOSED': { badge: 'badge-neutral', label: '已关闭' },
  }
  const state = stateColors[plan.state] || stateColors['DRAFT']
  const pendingSignals = plan.signals.filter(s => s.status === 'pending').length

  return (
    <div className="card-hover p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <span className="text-xs text-gray-500 font-mono">{plan.id}</span>
          <h3 className="text-sm font-medium text-gray-100 mt-0.5">{plan.name}</h3>
          <span className="text-[10px] text-gray-500">{plan.strategy_type}</span>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`badge ${state.badge} text-[10px]`}>{state.label}</span>
          {pendingSignals > 0 && (
            <span className="badge badge-warning text-[10px]">{pendingSignals} 待执行</span>
          )}
        </div>
      </div>
      
      {/* 核心指标 */}
      <div className="grid grid-cols-4 gap-2 mb-3 py-2 border-y border-terminal-border/50">
        <div className="text-center">
          <div className={`text-sm font-bold ${plan.realized_pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
            {plan.realized_pnl >= 0 ? '+' : ''}${plan.realized_pnl}
          </div>
          <div className="text-[10px] text-gray-500">盈亏</div>
        </div>
        <div className="text-center">
          <div className={`text-sm font-bold ${plan.win_rate >= 0.55 ? 'text-accent-success' : 'text-yellow-400'}`}>
            {(plan.win_rate * 100).toFixed(0)}%
          </div>
          <div className="text-[10px] text-gray-500">胜率</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-bold text-gray-200">{plan.total_trades}</div>
          <div className="text-[10px] text-gray-500">交易</div>
        </div>
        <div className="text-center">
          <div className={`text-sm font-bold ${plan.sharpe >= 1.5 ? 'text-accent-success' : 'text-yellow-400'}`}>
            {plan.sharpe.toFixed(2)}
          </div>
          <div className="text-[10px] text-gray-500">Sharpe</div>
        </div>
      </div>
      
      {plan.state === 'PENDING_CHAIRMAN' && (
        <button className="btn btn-primary btn-sm w-full">
          审批
        </button>
      )}
    </div>
  )
}

export default function TradingPage() {
  // 更快的刷新间隔
  const { data: balanceData, mutate: mutateBalance } = useSWR(`${API_BASE}/api/account/balance`, fetcher, { refreshInterval: 3000 })
  const { data: tickerData } = useSWR(`${API_BASE}/api/market/tickers`, fetcher, { refreshInterval: 1000 })
  
  // 真实数据 API
  const { data: signalsData, mutate: mutateSignals } = useSWR(`${API_BASE}/api/v2/signals`, fetcher, { refreshInterval: 3000 })
  const { data: positionsData } = useSWR(`${API_BASE}/api/v2/positions`, fetcher, { refreshInterval: 5000 })
  const { data: plansData } = useSWR(`${API_BASE}/api/v2/trading-plans`, fetcher, { refreshInterval: 5000 })
  
  const signals: Signal[] = signalsData?.signals || defaultSignals
  const positions: Position[] = positionsData?.positions || defaultPositions
  const plans: TradingPlan[] = plansData?.plans || defaultPlans
  
  // 从真实行情获取价格
  const btcTicker = tickerData?.tickers?.find((t: any) => t.symbol === 'BTC/USDT')
  const ethTicker = tickerData?.tickers?.find((t: any) => t.symbol === 'ETH/USDT')
  const btcPrice = btcTicker?.last || 95200
  const ethPrice = ethTicker?.last || 3520
  const btcChange = btcTicker?.percentage || 2.3
  const ethChange = ethTicker?.percentage || 1.8
  
  // 执行信号
  const handleExecuteSignal = async (id: string) => {
    try {
      const pnl = Math.random() * 200 - 50  // 模拟盈亏
      await api.executeSignal(id, pnl)
      mutateSignals()
      alert(`✅ 信号 ${id} 已提交执行！`)
    } catch (e) {
      alert('执行失败')
    }
  }
  
  // 取消信号
  const handleCancelSignal = async (id: string) => {
    try {
      await api.cancelSignal(id)
      mutateSignals()
    } catch (e) {
      alert('取消失败')
    }
  }

  const totalValue = positions.reduce((sum, p) => sum + p.current_price * p.quantity, 0)
  const totalPnl = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0)
  const pendingSignalsCount = signals.filter(s => s.status === 'pending').length

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">交易台</h1>
          <p className="page-subtitle">实时信号 · 仓位监控 · 策略执行</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => mutateBalance()} className="btn btn-secondary btn-sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新
          </button>
          <button className="btn btn-primary btn-sm">
            <Play className="w-4 h-4 mr-2" />
            新建计划
          </button>
        </div>
      </div>

      {/* Market Chart & Ticker */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <PriceChart defaultSymbol="BTC/USDT" height={280} />
        </div>
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-100 mb-4">市场行情</h2>
          <MarketTickerStatic />
        </div>
      </div>

      {/* Stats Overview - 更快刷新 */}
      <div className="grid grid-cols-5 gap-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">BTC/USDT</span>
            {btcChange >= 0 ? (
              <TrendingUp className="w-4 h-4 text-accent-success" />
            ) : (
              <TrendingDown className="w-4 h-4 text-accent-danger" />
            )}
          </div>
          <div className="text-2xl font-bold text-gray-100 number-highlight mt-1">
            ${btcPrice.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          <div className={`text-xs mt-1 ${btcChange >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
            {btcChange >= 0 ? '+' : ''}{btcChange.toFixed(2)}% 24h
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">ETH/USDT</span>
            {ethChange >= 0 ? (
              <TrendingUp className="w-4 h-4 text-accent-success" />
            ) : (
              <TrendingDown className="w-4 h-4 text-accent-danger" />
            )}
          </div>
          <div className="text-2xl font-bold text-gray-100 number-highlight mt-1">
            ${ethPrice.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
          <div className={`text-xs mt-1 ${ethChange >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
            {ethChange >= 0 ? '+' : ''}{ethChange.toFixed(2)}% 24h
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">账户余额</span>
            <DollarSign className="w-4 h-4 text-accent-primary" />
          </div>
          <div className="text-2xl font-bold text-gray-100 number-highlight mt-1">
            ${balanceData?.total_usd?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '---'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {balanceData?.exchange || 'OKX'}
          </div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">未实现盈亏</span>
            <Activity className="w-4 h-4 text-accent-success" />
          </div>
          <div className={`text-2xl font-bold number-highlight mt-1 ${totalPnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
            {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(0)}
          </div>
        </div>
        <div className="card border border-accent-warning/30">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">待执行信号</span>
            <AlertTriangle className="w-4 h-4 text-accent-warning" />
          </div>
          <div className="text-2xl font-bold text-accent-warning number-highlight mt-1">
            {pendingSignalsCount}
          </div>
          <div className="text-xs text-gray-500 mt-1">等待您审批</div>
        </div>
      </div>

      {/* Main Content - 3 columns */}
      <div className="grid grid-cols-3 gap-6">
        {/* 左列 - 实时信号 */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
              <Zap className="w-5 h-5 text-accent-warning" />
              实时信号
            </h2>
            <span className="badge badge-warning text-xs">{pendingSignalsCount} 待执行</span>
          </div>
          
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {signals.map((signal) => (
              <SignalCard 
                key={signal.id} 
                signal={signal}
                onExecute={handleExecuteSignal}
                onCancel={handleCancelSignal}
              />
            ))}
          </div>
        </div>

        {/* 中列 - 仓位与止损止盈 */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
              <Target className="w-5 h-5 text-accent-primary" />
              仓位控制
            </h2>
            <span className="text-xs text-gray-500">{positions.length} 持仓</span>
          </div>
          
          <div className="space-y-3">
            {positions.map((position) => (
              <PositionVisualization key={position.symbol} position={position} />
            ))}
          </div>
          
          {/* 风险摘要 */}
          <div className="card">
            <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4 text-orange-400" />
              风险摘要
            </h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">总敞口</span>
                <span className="text-gray-200">${totalValue.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">最大回撤限制</span>
                <span className="text-gray-200">-15%</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">当前风险值 VaR</span>
                <span className="text-accent-warning">$2,450</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">杠杆率</span>
                <span className="text-accent-success">1.0x</span>
              </div>
            </div>
          </div>
        </div>

        {/* 右列 - 交易计划 */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              交易计划
            </h2>
            <span className="text-xs text-gray-500">{plans.length} 计划</span>
          </div>
          
          <div className="space-y-3">
            {plans.map((plan) => (
              <TradingPlanCard key={plan.id} plan={plan} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
