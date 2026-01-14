'use client'

import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface TickerData {
  symbol: string
  last: number
  change_24h: number
  volume_24h: number
  high_24h: number
  low_24h: number
}

const fetcher = (url: string) => fetch(url).then(res => res.json())

function formatPrice(price: number): string {
  if (price >= 10000) return price.toLocaleString('en-US', { maximumFractionDigits: 0 })
  if (price >= 100) return price.toLocaleString('en-US', { maximumFractionDigits: 2 })
  if (price >= 1) return price.toLocaleString('en-US', { maximumFractionDigits: 4 })
  return price.toLocaleString('en-US', { maximumFractionDigits: 6 })
}

function formatVolume(vol: number): string {
  if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`
  if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`
  if (vol >= 1e3) return `${(vol / 1e3).toFixed(1)}K`
  return vol.toFixed(0)
}

function TickerItem({ ticker }: { ticker: TickerData }) {
  const change = ticker.change_24h || 0
  const isUp = change > 0
  const isDown = change < 0
  
  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-terminal-card rounded-lg border border-terminal-border hover:border-accent-primary/50 transition-colors min-w-[200px]">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono font-semibold text-gray-100">
            {ticker.symbol.replace('/USDT', '')}
          </span>
          <span className="text-xs text-gray-500">/USDT</span>
        </div>
        <div className="font-mono text-lg font-bold text-gray-100">
          ${formatPrice(ticker.last)}
        </div>
      </div>
      <div className={`flex items-center gap-1 px-2 py-1 rounded ${
        isUp ? 'bg-accent-success/20 text-accent-success' :
        isDown ? 'bg-accent-danger/20 text-accent-danger' :
        'bg-gray-500/20 text-gray-400'
      }`}>
        {isUp && <TrendingUp className="w-3 h-3" />}
        {isDown && <TrendingDown className="w-3 h-3" />}
        {!isUp && !isDown && <Minus className="w-3 h-3" />}
        <span className="font-mono text-sm font-semibold">
          {change >= 0 ? '+' : ''}{change.toFixed(2)}%
        </span>
      </div>
    </div>
  )
}

export default function MarketTicker() {
  const { data, error, isLoading } = useSWR(
    `${API_BASE}/api/market/tickers`,
    fetcher,
    { refreshInterval: 10000 }  // 每10秒刷新
  )
  
  const [scrollPosition, setScrollPosition] = useState(0)
  
  useEffect(() => {
    const interval = setInterval(() => {
      setScrollPosition(prev => prev + 1)
    }, 50)
    return () => clearInterval(interval)
  }, [])
  
  if (isLoading) {
    return (
      <div className="flex items-center gap-4 overflow-hidden py-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="animate-pulse bg-terminal-muted rounded-lg h-16 w-48" />
        ))}
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="text-accent-danger text-sm py-2">
        行情加载失败
      </div>
    )
  }
  
  const tickers: TickerData[] = data?.tickers || []
  
  // 复制 tickers 以实现无缝滚动
  const duplicatedTickers = [...tickers, ...tickers]
  
  return (
    <div className="relative overflow-hidden">
      <div 
        className="flex items-center gap-4 py-2"
        style={{
          transform: `translateX(-${scrollPosition % (tickers.length * 220)}px)`,
          transition: 'transform 0.05s linear',
        }}
      >
        {duplicatedTickers.map((ticker, idx) => (
          <TickerItem key={`${ticker.symbol}-${idx}`} ticker={ticker} />
        ))}
      </div>
      
      {/* 左右渐变遮罩 */}
      <div className="absolute top-0 left-0 w-20 h-full bg-gradient-to-r from-terminal-bg to-transparent pointer-events-none" />
      <div className="absolute top-0 right-0 w-20 h-full bg-gradient-to-l from-terminal-bg to-transparent pointer-events-none" />
    </div>
  )
}

// 静态行情列表（非滚动）
export function MarketTickerStatic() {
  const { data, error, isLoading } = useSWR(
    `${API_BASE}/api/market/tickers`,
    fetcher,
    { refreshInterval: 10000 }
  )
  
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="animate-pulse bg-terminal-muted rounded-lg h-20" />
        ))}
      </div>
    )
  }
  
  if (error) {
    return <div className="text-accent-danger text-sm">行情加载失败</div>
  }
  
  const tickers: TickerData[] = (data?.tickers || []).slice(0, 12)
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
      {tickers.map(ticker => (
        <div 
          key={ticker.symbol}
          className="bg-terminal-card border border-terminal-border rounded-lg p-3 hover:border-accent-primary/50 transition-colors"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono font-semibold text-sm text-gray-100">
              {ticker.symbol.replace('/USDT', '')}
            </span>
            <span className={`text-xs font-mono ${
              (ticker.change_24h || 0) >= 0 ? 'text-accent-success' : 'text-accent-danger'
            }`}>
              {(ticker.change_24h || 0) >= 0 ? '+' : ''}{(ticker.change_24h || 0).toFixed(2)}%
            </span>
          </div>
          <div className="font-mono text-lg font-bold text-gray-100">
            ${formatPrice(ticker.last)}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Vol: {formatVolume(ticker.volume_24h || 0)}
          </div>
        </div>
      ))}
    </div>
  )
}
