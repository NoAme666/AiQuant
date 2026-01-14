'use client'

import { useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const fetcher = (url: string) => fetch(url).then(res => res.json())

interface OHLCVData {
  timestamp: number
  datetime: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

const TIMEFRAMES = [
  { label: '1m', value: '1m' },
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1H', value: '1h' },
  { label: '4H', value: '4h' },
  { label: '1D', value: '1d' },
]

const SYMBOLS = [
  'BTC/USDT',
  'ETH/USDT',
  'SOL/USDT',
  'BNB/USDT',
  'XRP/USDT',
  'DOGE/USDT',
]

interface PriceChartProps {
  defaultSymbol?: string
  defaultTimeframe?: string
  height?: number
  showControls?: boolean
}

export default function PriceChart({
  defaultSymbol = 'BTC/USDT',
  defaultTimeframe = '1h',
  height = 400,
  showControls = true,
}: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  
  const [symbol, setSymbol] = useState(defaultSymbol)
  const [timeframe, setTimeframe] = useState(defaultTimeframe)
  
  const { data, error, isLoading } = useSWR(
    `${API_BASE}/api/market/ohlcv/${symbol.replace('/', '-')}?timeframe=${timeframe}&limit=200`,
    fetcher,
    { refreshInterval: 30000 }
  )
  
  // 初始化图表
  useEffect(() => {
    if (!chartContainerRef.current) return
    
    // 清理旧图表
    if (chartRef.current) {
      chartRef.current.remove()
    }
    
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: 'rgba(75, 85, 99, 0.3)' },
        horzLines: { color: 'rgba(75, 85, 99, 0.3)' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#00d9ff',
          width: 1,
          style: 2,
          labelBackgroundColor: '#00d9ff',
        },
        horzLine: {
          color: '#00d9ff',
          width: 1,
          style: 2,
          labelBackgroundColor: '#00d9ff',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(75, 85, 99, 0.5)',
      },
      timeScale: {
        borderColor: 'rgba(75, 85, 99, 0.5)',
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: height,
    })
    
    // K 线系列 - v4 API
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })
    
    // 成交量系列 - v4 API
    const volumeSeries = chart.addHistogramSeries({
      color: '#00d9ff',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    })
    
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })
    
    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    volumeSeriesRef.current = volumeSeries
    
    // 响应式
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }
    
    window.addEventListener('resize', handleResize)
    
    return () => {
      window.removeEventListener('resize', handleResize)
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [height])
  
  // 更新数据
  useEffect(() => {
    if (!data?.data || !candleSeriesRef.current || !volumeSeriesRef.current) return
    
    const ohlcvData: OHLCVData[] = data.data
    
    const candleData: CandlestickData[] = ohlcvData.map(d => ({
      time: Math.floor(d.timestamp / 1000) as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }))
    
    const volumeData = ohlcvData.map(d => ({
      time: Math.floor(d.timestamp / 1000) as Time,
      value: d.volume,
      color: d.close >= d.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
    }))
    
    candleSeriesRef.current.setData(candleData)
    volumeSeriesRef.current.setData(volumeData)
    
    // 自动缩放
    chartRef.current?.timeScale().fitContent()
  }, [data])
  
  return (
    <div className="bg-terminal-card border border-terminal-border rounded-lg overflow-hidden">
      {/* 控制栏 */}
      {showControls && (
        <div className="flex items-center justify-between p-3 border-b border-terminal-border">
          <div className="flex items-center gap-2">
            {/* 交易对选择 */}
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="bg-terminal-muted border border-terminal-border rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-accent-primary"
            >
              {SYMBOLS.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            
            {/* 周期选择 */}
            <div className="flex items-center gap-1 bg-terminal-muted rounded p-0.5">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf.value}
                  onClick={() => setTimeframe(tf.value)}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
                    timeframe === tf.value
                      ? 'bg-accent-primary text-terminal-bg'
                      : 'text-gray-400 hover:text-gray-100'
                  }`}
                >
                  {tf.label}
                </button>
              ))}
            </div>
          </div>
          
          {/* 当前价格 */}
          {data?.data && data.data.length > 0 && (
            <div className="text-right">
              <div className="font-mono text-lg font-bold text-gray-100">
                ${data.data[data.data.length - 1]?.close?.toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">
                {symbol}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* 图表区域 */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-terminal-bg/80 z-10">
            <div className="flex items-center gap-2 text-gray-400">
              <div className="animate-spin w-5 h-5 border-2 border-accent-primary border-t-transparent rounded-full" />
              <span>加载中...</span>
            </div>
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-terminal-bg/80 z-10">
            <div className="text-accent-danger">图表加载失败</div>
          </div>
        )}
        
        <div ref={chartContainerRef} style={{ height: `${height}px` }} />
      </div>
    </div>
  )
}

// 迷你图表（用于卡片展示）
export function MiniChart({
  symbol = 'BTC/USDT',
  timeframe = '1h',
  height = 120,
}: {
  symbol?: string
  timeframe?: string
  height?: number
}) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  
  const { data } = useSWR(
    `${API_BASE}/api/market/ohlcv/${symbol.replace('/', '-')}?timeframe=${timeframe}&limit=50`,
    fetcher,
    { refreshInterval: 60000 }
  )
  
  useEffect(() => {
    if (!chartContainerRef.current) return
    
    if (chartRef.current) {
      chartRef.current.remove()
    }
    
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'transparent',
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      crosshair: { mode: 0 },
      handleScroll: false,
      handleScale: false,
      width: chartContainerRef.current.clientWidth,
      height: height,
    })
    
    const lineSeries = chart.addAreaSeries({
      lineColor: '#00d9ff',
      topColor: 'rgba(0, 217, 255, 0.3)',
      bottomColor: 'rgba(0, 217, 255, 0.0)',
      lineWidth: 2,
    })
    
    chartRef.current = chart
    
    if (data?.data) {
      const lineData = data.data.map((d: OHLCVData) => ({
        time: Math.floor(d.timestamp / 1000) as Time,
        value: d.close,
      }))
      lineSeries.setData(lineData)
      chart.timeScale().fitContent()
    }
    
    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [data, height])
  
  return <div ref={chartContainerRef} style={{ height: `${height}px` }} />
}
