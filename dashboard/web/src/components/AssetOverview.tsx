'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown,
  PieChart,
  RefreshCw,
  AlertCircle,
  DollarSign,
  Lock,
  Unlock
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const fetcher = (url: string) => fetch(url).then(res => res.json())

interface Balance {
  asset: string
  free: number
  locked: number
  total: number
  usd_value: number
}

interface AccountData {
  exchange: string
  total_usd: number
  balances: Balance[]
  timestamp: string
  error?: string
}

interface Position {
  symbol: string
  side: string
  contracts: number
  entry_price: number
  mark_price: number
  unrealized_pnl: number
  leverage: number
}

interface PositionData {
  exchange: string
  positions: Position[]
  timestamp: string
  error?: string
}

function formatUSD(value: number): string {
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
  if (value >= 1e3) return `$${(value / 1e3).toFixed(2)}K`
  return `$${value.toFixed(2)}`
}

function formatAmount(value: number): string {
  if (value >= 1e6) return `${(value / 1e6).toFixed(4)}M`
  if (value >= 1e3) return `${(value / 1e3).toFixed(4)}K`
  if (value >= 1) return value.toFixed(4)
  return value.toFixed(8)
}

// 资产饼图的颜色
const COLORS = [
  '#00d9ff', // accent-primary
  '#22c55e', // green
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#6366f1', // indigo
]

function AssetPieChart({ balances }: { balances: Balance[] }) {
  const total = balances.reduce((sum, b) => sum + b.usd_value, 0)
  const topAssets = balances.slice(0, 6)
  
  let currentAngle = 0
  const segments = topAssets.map((asset, i) => {
    const percentage = (asset.usd_value / total) * 100
    const angle = (percentage / 100) * 360
    const startAngle = currentAngle
    currentAngle += angle
    
    return {
      asset: asset.asset,
      percentage,
      startAngle,
      endAngle: currentAngle,
      color: COLORS[i % COLORS.length],
    }
  })
  
  return (
    <div className="flex items-center gap-6">
      {/* 简化的条形图替代饼图 */}
      <div className="flex-1 space-y-2">
        {segments.map(seg => (
          <div key={seg.asset} className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded-sm" 
              style={{ backgroundColor: seg.color }}
            />
            <span className="text-sm text-gray-300 w-12">{seg.asset}</span>
            <div className="flex-1 h-2 bg-terminal-muted rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-500"
                style={{ 
                  width: `${seg.percentage}%`,
                  backgroundColor: seg.color,
                }}
              />
            </div>
            <span className="text-xs text-gray-500 w-12 text-right">
              {seg.percentage.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function BalanceRow({ balance }: { balance: Balance }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-terminal-border last:border-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-terminal-muted flex items-center justify-center text-xs font-bold text-accent-primary">
          {balance.asset.slice(0, 2)}
        </div>
        <div>
          <div className="font-medium text-gray-100">{balance.asset}</div>
          <div className="text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Unlock className="w-3 h-3" />
              {formatAmount(balance.free)}
              {balance.locked > 0 && (
                <>
                  <Lock className="w-3 h-3 ml-2" />
                  {formatAmount(balance.locked)}
                </>
              )}
            </span>
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className="font-mono font-medium text-gray-100">
          {formatUSD(balance.usd_value)}
        </div>
        <div className="text-xs text-gray-500">
          {formatAmount(balance.total)} {balance.asset}
        </div>
      </div>
    </div>
  )
}

function PositionRow({ position }: { position: Position }) {
  const pnlPositive = position.unrealized_pnl >= 0
  const pnlPercent = ((position.mark_price - position.entry_price) / position.entry_price) * 100
  
  return (
    <div className="flex items-center justify-between py-2 border-b border-terminal-border last:border-0">
      <div className="flex items-center gap-3">
        <div className={`px-2 py-0.5 text-xs font-medium rounded ${
          position.side === 'long' 
            ? 'bg-accent-success/20 text-accent-success' 
            : 'bg-accent-danger/20 text-accent-danger'
        }`}>
          {position.side === 'long' ? 'LONG' : 'SHORT'}
        </div>
        <div>
          <div className="font-medium text-gray-100">{position.symbol}</div>
          <div className="text-xs text-gray-500">
            {position.contracts} 张 · {position.leverage}x
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className={`font-mono font-medium ${pnlPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
          {pnlPositive ? '+' : ''}{formatUSD(position.unrealized_pnl)}
        </div>
        <div className={`text-xs ${pnlPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
          {pnlPositive ? '+' : ''}{pnlPercent.toFixed(2)}%
        </div>
      </div>
    </div>
  )
}

export default function AssetOverview() {
  const [activeTab, setActiveTab] = useState<'balance' | 'positions'>('balance')
  
  const { data: balanceData, error: balanceError, isLoading: balanceLoading, mutate: refreshBalance } = useSWR<AccountData>(
    `${API_BASE}/api/account/balance`,
    fetcher,
    { refreshInterval: 60000 }
  )
  
  const { data: positionData, error: positionError, isLoading: positionLoading } = useSWR<PositionData>(
    `${API_BASE}/api/account/positions`,
    fetcher,
    { refreshInterval: 30000 }
  )
  
  const isLoading = balanceLoading || positionLoading
  const hasError = balanceError || positionError || balanceData?.error
  
  return (
    <div className="bg-terminal-card border border-terminal-border rounded-lg overflow-hidden">
      {/* 头部 */}
      <div className="p-4 border-b border-terminal-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Wallet className="w-5 h-5 text-accent-primary" />
            <span className="font-medium text-gray-100">账户资产</span>
            {balanceData?.exchange && (
              <span className="text-xs text-gray-500 bg-terminal-muted px-2 py-0.5 rounded">
                {balanceData.exchange.toUpperCase()}
              </span>
            )}
          </div>
          <button
            onClick={() => refreshBalance()}
            className="p-1.5 hover:bg-terminal-muted rounded transition-colors"
            title="刷新"
          >
            <RefreshCw className={`w-4 h-4 text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        
        {/* 总资产 */}
        {balanceData && !hasError && (
          <div className="flex items-end gap-2">
            <DollarSign className="w-6 h-6 text-accent-primary" />
            <span className="text-3xl font-bold font-mono text-gray-100">
              {balanceData.total_usd?.toLocaleString('en-US', { maximumFractionDigits: 2 })}
            </span>
            <span className="text-gray-500 mb-1">USD</span>
          </div>
        )}
        
        {hasError && (
          <div className="flex items-center gap-2 text-accent-warning">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">
              {balanceData?.error || '加载失败，请检查 API 密钥配置'}
            </span>
          </div>
        )}
      </div>
      
      {/* 资产分布 */}
      {balanceData?.balances && balanceData.balances.length > 0 && (
        <div className="p-4 border-b border-terminal-border">
          <div className="text-sm text-gray-400 mb-3">资产分布</div>
          <AssetPieChart balances={balanceData.balances} />
        </div>
      )}
      
      {/* Tab 切换 */}
      <div className="flex border-b border-terminal-border">
        <button
          onClick={() => setActiveTab('balance')}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'balance'
              ? 'text-accent-primary border-b-2 border-accent-primary'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          余额 ({balanceData?.balances?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('positions')}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'positions'
              ? 'text-accent-primary border-b-2 border-accent-primary'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          持仓 ({positionData?.positions?.length || 0})
        </button>
      </div>
      
      {/* 内容区域 */}
      <div className="max-h-80 overflow-y-auto">
        {activeTab === 'balance' ? (
          <div className="p-3">
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="animate-pulse bg-terminal-muted rounded h-14" />
                ))}
              </div>
            ) : balanceData?.balances?.length ? (
              balanceData.balances.map(balance => (
                <BalanceRow key={balance.asset} balance={balance} />
              ))
            ) : (
              <div className="text-center text-gray-500 py-8">暂无余额数据</div>
            )}
          </div>
        ) : (
          <div className="p-3">
            {positionLoading ? (
              <div className="space-y-3">
                {[1, 2].map(i => (
                  <div key={i} className="animate-pulse bg-terminal-muted rounded h-14" />
                ))}
              </div>
            ) : positionData?.positions?.length ? (
              positionData.positions.map((pos, idx) => (
                <PositionRow key={`${pos.symbol}-${idx}`} position={pos} />
              ))
            ) : (
              <div className="text-center text-gray-500 py-8">暂无持仓</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// 简化版资产卡片
export function AssetCard() {
  const { data } = useSWR<AccountData>(
    `${API_BASE}/api/account/balance`,
    fetcher,
    { refreshInterval: 60000 }
  )
  
  if (!data || data.error) {
    return (
      <div className="bg-terminal-card border border-terminal-border rounded-lg p-4">
        <div className="flex items-center gap-2 text-gray-400">
          <Wallet className="w-5 h-5" />
          <span>账户未连接</span>
        </div>
      </div>
    )
  }
  
  const topBalances = data.balances?.slice(0, 3) || []
  
  return (
    <div className="bg-terminal-card border border-terminal-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Wallet className="w-5 h-5 text-accent-primary" />
          <span className="font-medium text-gray-100">总资产</span>
        </div>
        <span className="text-xs text-gray-500">{data.exchange?.toUpperCase()}</span>
      </div>
      
      <div className="text-2xl font-bold font-mono text-gray-100 mb-3">
        ${data.total_usd?.toLocaleString()}
      </div>
      
      <div className="space-y-1">
        {topBalances.map(b => (
          <div key={b.asset} className="flex items-center justify-between text-sm">
            <span className="text-gray-400">{b.asset}</span>
            <span className="font-mono text-gray-300">{formatUSD(b.usd_value)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
