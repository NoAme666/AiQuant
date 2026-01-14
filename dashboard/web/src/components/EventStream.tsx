'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Info,
  Bell,
  Zap,
  ArrowRight,
  RefreshCw,
  Wifi,
  WifiOff
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE = API_BASE.replace('http', 'ws')

interface MarketEvent {
  type: string
  data: {
    symbol: string
    last: number
    change_24h: number
    timestamp: string
  }
}

interface SystemEvent {
  id: string
  type: string
  actor?: string
  action: string
  target?: string
  level: 'info' | 'success' | 'warning' | 'danger'
  timestamp: string
  details?: Record<string, unknown>
}

const eventIcons: Record<string, React.ElementType> = {
  ticker: Activity,
  alert: AlertTriangle,
  success: CheckCircle,
  info: Info,
  action: Zap,
}

const levelColors: Record<string, string> = {
  info: 'text-accent-primary bg-accent-primary/10',
  success: 'text-accent-success bg-accent-success/10',
  warning: 'text-accent-warning bg-accent-warning/10',
  danger: 'text-accent-danger bg-accent-danger/10',
}

function EventItem({ event }: { event: SystemEvent }) {
  const Icon = eventIcons[event.type] || Info
  const color = levelColors[event.level] || levelColors.info
  
  const timeAgo = getTimeAgo(new Date(event.timestamp))
  
  return (
    <div className="flex items-start gap-3 p-3 border-b border-terminal-border last:border-0 hover:bg-terminal-muted/30 transition-colors">
      <div className={`p-1.5 rounded ${color}`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          {event.actor && (
            <>
              <span className="font-medium text-gray-100 text-sm">{event.actor}</span>
              <ArrowRight className="w-3 h-3 text-gray-500" />
            </>
          )}
          <span className="text-sm text-gray-300">{event.action}</span>
          {event.target && (
            <span className="text-sm text-accent-primary">{event.target}</span>
          )}
        </div>
        <div className="text-xs text-gray-500">{timeAgo}</div>
      </div>
    </div>
  )
}

function TickerEvent({ data }: { data: MarketEvent['data'] }) {
  const isUp = (data.change_24h || 0) >= 0
  
  return (
    <div className="flex items-center justify-between p-2 bg-terminal-muted/30 rounded text-sm">
      <div className="flex items-center gap-2">
        <Activity className="w-3.5 h-3.5 text-accent-primary" />
        <span className="font-mono font-medium">{data.symbol}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="font-mono">${data.last?.toLocaleString()}</span>
        <span className={`font-mono ${isUp ? 'text-accent-success' : 'text-accent-danger'}`}>
          {isUp ? '+' : ''}{data.change_24h?.toFixed(2)}%
        </span>
      </div>
    </div>
  )
}

function getTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000)
  
  if (seconds < 60) return '刚刚'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`
  return `${Math.floor(seconds / 86400)} 天前`
}

interface EventStreamProps {
  maxEvents?: number
  showMarketTicker?: boolean
}

export default function EventStream({ 
  maxEvents = 20, 
  showMarketTicker = true 
}: EventStreamProps) {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<SystemEvent[]>([])
  const [latestTicker, setLatestTicker] = useState<MarketEvent['data'] | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  // 模拟事件（用于演示）
  useEffect(() => {
    const mockEvents: SystemEvent[] = [
      {
        id: '1',
        type: 'action',
        actor: 'Alpha A Lead',
        action: '提交策略到',
        target: 'ROBUSTNESS_GATE',
        level: 'info',
        timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
      },
      {
        id: '2',
        type: 'success',
        actor: 'CRO',
        action: '批准了会议申请',
        target: '策略评审会议',
        level: 'success',
        timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
      },
      {
        id: '3',
        type: 'info',
        actor: 'Data Auditor',
        action: '完成数据审核',
        target: 'BTC 动量策略',
        level: 'info',
        timestamp: new Date(Date.now() - 60 * 60000).toISOString(),
      },
      {
        id: '4',
        type: 'alert',
        actor: 'Skeptic',
        action: '要求补充实验',
        target: 'ETH 均值回归',
        level: 'warning',
        timestamp: new Date(Date.now() - 2 * 60 * 60000).toISOString(),
      },
      {
        id: '5',
        type: 'success',
        actor: 'Backtest Lead',
        action: '完成回测',
        target: 'SOL 趋势策略',
        level: 'success',
        timestamp: new Date(Date.now() - 3 * 60 * 60000).toISOString(),
      },
    ]
    setEvents(mockEvents)
  }, [])
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    
    try {
      const ws = new WebSocket(`${WS_BASE}/api/market/stream`)
      
      ws.onopen = () => {
        setConnected(true)
        // 订阅默认币种
        ws.send(JSON.stringify({
          action: 'subscribe',
          symbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
        }))
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as MarketEvent
          if (data.type === 'ticker' && data.data) {
            setLatestTicker(data.data)
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
      
      ws.onclose = () => {
        setConnected(false)
        // 5秒后重连
        reconnectTimeoutRef.current = setTimeout(connect, 5000)
      }
      
      ws.onerror = () => {
        setConnected(false)
      }
      
      wsRef.current = ws
    } catch (e) {
      console.error('WebSocket connection error:', e)
      setConnected(false)
    }
  }, [])
  
  useEffect(() => {
    connect()
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])
  
  return (
    <div className="bg-terminal-card border border-terminal-border rounded-lg overflow-hidden h-full flex flex-col">
      {/* 标题栏 */}
      <div className="flex items-center justify-between p-3 border-b border-terminal-border">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-accent-primary" />
          <span className="font-medium text-gray-100">实时事件</span>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="flex items-center gap-1 text-xs text-accent-success">
              <Wifi className="w-3 h-3" />
              已连接
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <WifiOff className="w-3 h-3" />
              未连接
            </span>
          )}
          <button
            onClick={connect}
            className="p-1 hover:bg-terminal-muted rounded transition-colors"
            title="刷新连接"
          >
            <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
          </button>
        </div>
      </div>
      
      {/* 实时行情 */}
      {showMarketTicker && latestTicker && (
        <div className="p-3 border-b border-terminal-border">
          <TickerEvent data={latestTicker} />
        </div>
      )}
      
      {/* 事件列表 */}
      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 text-sm">
            暂无事件
          </div>
        ) : (
          <div>
            {events.slice(0, maxEvents).map(event => (
              <EventItem key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// 紧凑版事件流
export function EventStreamCompact({ maxEvents = 5 }: { maxEvents?: number }) {
  const [events] = useState<SystemEvent[]>([
    {
      id: '1',
      type: 'action',
      actor: 'Alpha A Lead',
      action: '提交策略',
      level: 'info',
      timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    },
    {
      id: '2',
      type: 'success',
      actor: 'CRO',
      action: '批准会议',
      level: 'success',
      timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
    },
    {
      id: '3',
      type: 'alert',
      actor: 'Risk',
      action: '风险警告',
      level: 'warning',
      timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
    },
  ])
  
  return (
    <div className="space-y-2">
      {events.slice(0, maxEvents).map(event => {
        const Icon = eventIcons[event.type] || Info
        const color = levelColors[event.level]
        
        return (
          <div key={event.id} className="flex items-center gap-2 text-sm">
            <div className={`p-1 rounded ${color}`}>
              <Icon className="w-3 h-3" />
            </div>
            <span className="text-gray-100">{event.actor}</span>
            <span className="text-gray-500">{event.action}</span>
            <span className="text-xs text-gray-600 ml-auto">
              {getTimeAgo(new Date(event.timestamp))}
            </span>
          </div>
        )
      })}
    </div>
  )
}
