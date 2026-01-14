'use client'

import { useState, useEffect } from 'react'
import useSWR from 'swr'
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Clock,
  AlertTriangle,
  Calendar,
  BarChart3,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface Asset {
  asset: string
  free: number
  locked: number
  total: number
  usd_value: number
}

interface PnlData {
  exchange: string
  total_value_usd: number
  today: { pnl: number; pnl_pct: number }
  week: { pnl: number; pnl_pct: number }
  month: { pnl: number; pnl_pct: number }
  total: { pnl: number; pnl_pct: number; initial_value: number }
  history: Array<{ date: string; value: number; daily_pnl: number; daily_pnl_pct: number }>
}

function AssetRow({ asset, totalValue }: { asset: Asset; totalValue: number }) {
  const allocation = totalValue > 0 ? (asset.usd_value / totalValue * 100) : 0
  
  return (
    <tr className="border-b border-terminal-border/50 hover:bg-terminal-muted/30">
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-accent-primary/20 flex items-center justify-center text-xs font-bold text-accent-primary">
            {asset.asset.slice(0, 2)}
          </div>
          <div>
            <div className="text-sm font-medium text-gray-200">{asset.asset}</div>
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-right">
        <div className="text-sm font-mono text-gray-200">{asset.total.toFixed(6)}</div>
        {asset.locked > 0 && (
          <div className="text-xs text-gray-500">🔒 {asset.locked.toFixed(4)}</div>
        )}
      </td>
      <td className="py-3 px-4 text-right">
        <div className="text-sm font-mono text-gray-200">${asset.usd_value.toLocaleString()}</div>
      </td>
      <td className="py-3 px-4 text-right">
        <div className="text-sm text-gray-400">{allocation.toFixed(1)}%</div>
        <div className="w-full bg-terminal-muted/50 rounded-full h-1 mt-1">
          <div 
            className="bg-accent-primary h-1 rounded-full" 
            style={{ width: `${Math.min(allocation, 100)}%` }}
          ></div>
        </div>
      </td>
    </tr>
  )
}

function PnlCard({ label, pnl, pnl_pct, icon: Icon }: { 
  label: string
  pnl: number
  pnl_pct: number
  icon: React.ElementType
}) {
  const isPositive = pnl >= 0
  
  return (
    <div className="card">
      <div className="flex items-center gap-3">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
          isPositive ? 'bg-accent-success/20' : 'bg-accent-danger/20'
        }`}>
          <Icon className={`w-6 h-6 ${isPositive ? 'text-accent-success' : 'text-accent-danger'}`} />
        </div>
        <div>
          <div className={`text-xl font-bold font-mono ${
            isPositive ? 'text-accent-success' : 'text-accent-danger'
          }`}>
            {isPositive ? '+' : ''}${pnl.toLocaleString()}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">{label}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${
              isPositive ? 'bg-accent-success/20 text-accent-success' : 'bg-accent-danger/20 text-accent-danger'
            }`}>
              {isPositive ? '+' : ''}{pnl_pct.toFixed(2)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AssetsPage() {
  const { data: balanceData, mutate: mutateBalance } = useSWR(`${API_BASE}/api/account/balance`, fetcher, { refreshInterval: 30000 })
  const { data: pnlData, mutate: mutatePnl } = useSWR<PnlData>(`${API_BASE}/api/account/pnl`, fetcher, { refreshInterval: 60000 })
  const [isRecording, setIsRecording] = useState(false)
  
  const assets: Asset[] = balanceData?.balances || []
  const totalValue = balanceData?.total_usd || pnlData?.total_value_usd || 0
  const exchange = balanceData?.exchange || pnlData?.exchange || 'unknown'
  
  const handleRecordSnapshot = async () => {
    setIsRecording(true)
    try {
      await fetch(`${API_BASE}/api/account/snapshot`, { method: 'POST' })
      mutateBalance()
      mutatePnl()
    } catch (e) {
      console.error('记录快照失败', e)
    }
    setIsRecording(false)
  }
  
  const handleRefresh = () => {
    mutateBalance()
    mutatePnl()
  }
  
  const isDataLoaded = balanceData && !balanceData.error
  
  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">资产总览</h1>
          <p className="page-subtitle">
            {isDataLoaded ? (
              <>实时数据来自 <span className="text-accent-primary font-medium uppercase">{exchange}</span></>
            ) : (
              '连接交易所中...'
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            className="btn btn-secondary btn-sm"
            onClick={handleRecordSnapshot}
            disabled={isRecording}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            {isRecording ? '记录中...' : '记录快照'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新数据
          </button>
        </div>
      </div>
      
      {/* Connection Warning */}
      {!isDataLoaded && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
          <div className="flex-1">
            <p className="text-sm text-yellow-200 font-medium">⚠️ 无法连接交易所</p>
            <p className="text-xs text-yellow-400">
              {balanceData?.error || '请检查 OKX API 配置是否正确'}
            </p>
          </div>
        </div>
      )}
      
      {/* Overview Card */}
      <div className="card bg-gradient-to-r from-terminal-bg to-terminal-muted/30">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-400 mb-1">账户总资产</div>
            <div className="text-4xl font-bold text-gray-100 number-highlight font-mono">
              ${totalValue.toLocaleString()}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {assets.length} 种资产 · {exchange.toUpperCase()}
            </div>
          </div>
          <div className="w-24 h-24 rounded-full bg-accent-primary/10 flex items-center justify-center">
            <Wallet className="w-12 h-12 text-accent-primary" />
          </div>
        </div>
      </div>
      
      {/* PnL Cards */}
      <div className="grid grid-cols-4 gap-4">
        <PnlCard 
          label="今日盈亏" 
          pnl={pnlData?.today?.pnl || 0} 
          pnl_pct={pnlData?.today?.pnl_pct || 0}
          icon={Clock}
        />
        <PnlCard 
          label="本周盈亏" 
          pnl={pnlData?.week?.pnl || 0} 
          pnl_pct={pnlData?.week?.pnl_pct || 0}
          icon={Calendar}
        />
        <PnlCard 
          label="本月盈亏" 
          pnl={pnlData?.month?.pnl || 0} 
          pnl_pct={pnlData?.month?.pnl_pct || 0}
          icon={BarChart3}
        />
        <PnlCard 
          label="累计盈亏" 
          pnl={pnlData?.total?.pnl || 0} 
          pnl_pct={pnlData?.total?.pnl_pct || 0}
          icon={TrendingUp}
        />
      </div>
      
      {/* Assets Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">资产明细</h2>
          <span className="text-xs text-gray-500">
            初始投入: ${pnlData?.total?.initial_value?.toLocaleString() || '-'}
          </span>
        </div>
        
        {assets.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-terminal-border text-left text-xs text-gray-500">
                  <th className="py-2 px-4 font-medium">资产</th>
                  <th className="py-2 px-4 font-medium text-right">数量</th>
                  <th className="py-2 px-4 font-medium text-right">价值 (USD)</th>
                  <th className="py-2 px-4 font-medium text-right">占比</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <AssetRow key={asset.asset} asset={asset} totalValue={totalValue} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Wallet className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">暂无资产数据</p>
            <p className="text-xs text-gray-600 mt-1">请检查交易所连接状态</p>
          </div>
        )}
      </div>
      
      {/* PnL History Chart Placeholder */}
      {pnlData?.history && pnlData.history.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-100 mb-4">盈亏走势 (近30天)</h2>
          <div className="grid grid-cols-7 gap-2">
            {pnlData.history.slice(-7).map((item, idx) => {
              const isPositive = item.daily_pnl >= 0
              return (
                <div key={idx} className="text-center">
                  <div className={`text-xs font-mono ${isPositive ? 'text-accent-success' : 'text-accent-danger'}`}>
                    {isPositive ? '+' : ''}{item.daily_pnl_pct.toFixed(2)}%
                  </div>
                  <div className={`h-16 rounded mt-1 ${isPositive ? 'bg-accent-success/20' : 'bg-accent-danger/20'}`}
                    style={{
                      height: `${Math.min(Math.abs(item.daily_pnl_pct) * 10 + 20, 80)}px`,
                    }}
                  ></div>
                  <div className="text-[10px] text-gray-500 mt-1">
                    {new Date(item.date).getDate()}日
                  </div>
                </div>
              )
            })}
          </div>
          <div className="mt-4 pt-4 border-t border-terminal-border/50 flex items-center justify-between text-sm">
            <span className="text-gray-500">共 {pnlData.history.length} 条记录</span>
            <span className="text-gray-400">
              区间收益: 
              <span className={`ml-2 font-mono ${pnlData.total.pnl >= 0 ? 'text-accent-success' : 'text-accent-danger'}`}>
                {pnlData.total.pnl >= 0 ? '+' : ''}{pnlData.total.pnl_pct.toFixed(2)}%
              </span>
            </span>
          </div>
        </div>
      )}
      
      {/* Last Update */}
      <div className="flex items-center justify-center gap-2 text-xs text-gray-500" suppressHydrationWarning>
        <Clock className="w-3 h-3" />
        数据更新时间: <span suppressHydrationWarning>{new Date().toLocaleTimeString('zh-CN')}</span>
      </div>
    </div>
  )
}
