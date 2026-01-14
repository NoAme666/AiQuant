'use client'

import { useState, useEffect } from 'react'
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
} from 'lucide-react'

interface Position {
  symbol: string
  side: 'long' | 'short'
  quantity: number
  entry_price: number
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  stop_loss?: number
  take_profit?: number
}

interface TradingPlan {
  id: string
  name: string
  state: string
  created_at: string
  target_portfolio: Record<string, number>
  realized_pnl: number
}

interface Order {
  id: string
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  price: number
  status: string
  created_at: string
}

// Mock data
const positions: Position[] = [
  { symbol: 'BTC/USDT', side: 'long', quantity: 0.5, entry_price: 94500, current_price: 95200, unrealized_pnl: 350, unrealized_pnl_pct: 0.0074 },
  { symbol: 'ETH/USDT', side: 'long', quantity: 5, entry_price: 3450, current_price: 3520, unrealized_pnl: 350, unrealized_pnl_pct: 0.0203 },
]

const tradingPlans: TradingPlan[] = [
  { id: 'TP-001', name: 'BTC 动量策略执行', state: 'MONITORING', created_at: '2026-01-14', target_portfolio: { 'BTC/USDT': 0.3, 'ETH/USDT': 0.2 }, realized_pnl: 1240 },
  { id: 'TP-002', name: 'ETH 均值回归建仓', state: 'PENDING_CHAIRMAN', created_at: '2026-01-14', target_portfolio: { 'ETH/USDT': 0.4 }, realized_pnl: 0 },
]

const recentOrders: Order[] = [
  { id: 'O-001', symbol: 'BTC/USDT', side: 'buy', quantity: 0.2, price: 94800, status: 'filled', created_at: '14:32:15' },
  { id: 'O-002', symbol: 'ETH/USDT', side: 'buy', quantity: 2, price: 3480, status: 'filled', created_at: '14:28:03' },
  { id: 'O-003', symbol: 'BTC/USDT', side: 'buy', quantity: 0.3, price: 94300, status: 'filled', created_at: '13:45:22' },
]

function PositionRow({ position }: { position: Position }) {
  const isProfit = position.unrealized_pnl >= 0

  return (
    <tr>
      <td>
        <div className="flex items-center gap-2">
          <span className={`badge ${position.side === 'long' ? 'badge-success' : 'badge-danger'} text-[10px]`}>
            {position.side.toUpperCase()}
          </span>
          <span className="font-medium">{position.symbol}</span>
        </div>
      </td>
      <td className="number-highlight">{position.quantity}</td>
      <td className="number-highlight">${position.entry_price.toLocaleString()}</td>
      <td className="number-highlight">${position.current_price.toLocaleString()}</td>
      <td className={isProfit ? 'text-accent-success' : 'text-accent-danger'}>
        <div className="number-highlight">
          {isProfit ? '+' : ''}{position.unrealized_pnl.toFixed(2)}
          <span className="text-xs ml-1">
            ({isProfit ? '+' : ''}{(position.unrealized_pnl_pct * 100).toFixed(2)}%)
          </span>
        </div>
      </td>
      <td>
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost btn-sm p-1.5">
            <TrendingUp className="w-4 h-4" />
          </button>
          <button className="btn btn-ghost btn-sm p-1.5 text-accent-danger">
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  )
}

function TradingPlanCard({ plan }: { plan: TradingPlan }) {
  const stateColors: Record<string, string> = {
    'DRAFT': 'badge-neutral',
    'PENDING_CHAIRMAN': 'badge-warning',
    'APPROVED': 'badge-success',
    'MONITORING': 'badge-info',
    'CLOSED': 'badge-neutral',
  }

  return (
    <div className="card-hover p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <span className="text-xs text-gray-500 font-mono">{plan.id}</span>
          <h3 className="text-sm font-medium text-gray-100 mt-0.5">{plan.name}</h3>
        </div>
        <span className={`badge ${stateColors[plan.state] || 'badge-neutral'} text-[10px]`}>
          {plan.state}
        </span>
      </div>
      
      <div className="space-y-2 mb-3">
        {Object.entries(plan.target_portfolio).map(([symbol, weight]) => (
          <div key={symbol} className="flex items-center justify-between text-xs">
            <span className="text-gray-400">{symbol}</span>
            <span className="text-gray-200">{(weight * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-terminal-border/50">
        <span className="text-xs text-gray-500">{plan.created_at}</span>
        {plan.realized_pnl !== 0 && (
          <span className={`text-sm ${plan.realized_pnl > 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
            {plan.realized_pnl > 0 ? '+' : ''}${plan.realized_pnl}
          </span>
        )}
      </div>
    </div>
  )
}

export default function TradingPage() {
  const [btcPrice, setBtcPrice] = useState(95200)
  const [ethPrice, setEthPrice] = useState(3520)

  // Simulate price updates
  useEffect(() => {
    const interval = setInterval(() => {
      setBtcPrice((p) => p + (Math.random() - 0.5) * 100)
      setEthPrice((p) => p + (Math.random() - 0.5) * 10)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const totalValue = positions.reduce((sum, p) => sum + p.current_price * p.quantity, 0)
  const totalPnl = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0)

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">交易台</h1>
          <p className="page-subtitle">持仓监控与交易执行</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-secondary btn-sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新
          </button>
          <button className="btn btn-primary btn-sm">
            <Play className="w-4 h-4 mr-2" />
            新建交易计划
          </button>
        </div>
      </div>

      {/* Market Overview */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">BTC/USDT</span>
            <TrendingUp className="w-4 h-4 text-accent-success" />
          </div>
          <div className="text-2xl font-bold text-gray-100 number-highlight mt-1">
            ${btcPrice.toFixed(0)}
          </div>
          <div className="text-xs text-accent-success mt-1">+2.3% 24h</div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">ETH/USDT</span>
            <TrendingUp className="w-4 h-4 text-accent-success" />
          </div>
          <div className="text-2xl font-bold text-gray-100 number-highlight mt-1">
            ${ethPrice.toFixed(0)}
          </div>
          <div className="text-xs text-accent-success mt-1">+1.8% 24h</div>
        </div>
        <div className="card">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">持仓价值</span>
            <DollarSign className="w-4 h-4 text-accent-primary" />
          </div>
          <div className="text-2xl font-bold text-gray-100 number-highlight mt-1">
            ${totalValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
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
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Positions */}
        <div className="col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-100">当前持仓</h2>
            <span className="text-xs text-gray-500">{positions.length} 个持仓</span>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>交易对</th>
                <th>数量</th>
                <th>入场价</th>
                <th>当前价</th>
                <th>盈亏</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <PositionRow key={position.symbol} position={position} />
              ))}
            </tbody>
          </table>
        </div>

        {/* Trading Plans */}
        <div className="space-y-4">
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">交易计划</h2>
            <div className="space-y-3">
              {tradingPlans.map((plan) => (
                <TradingPlanCard key={plan.id} plan={plan} />
              ))}
            </div>
          </div>

          {/* Recent Orders */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-100 mb-4">最近订单</h2>
            <div className="space-y-2">
              {recentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between py-2 border-b border-terminal-border/50 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={`badge ${order.side === 'buy' ? 'badge-success' : 'badge-danger'} text-[10px]`}>
                      {order.side.toUpperCase()}
                    </span>
                    <span className="text-sm text-gray-200">{order.symbol}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-gray-200">{order.quantity} @ ${order.price}</div>
                    <div className="text-xs text-gray-500">{order.created_at}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
