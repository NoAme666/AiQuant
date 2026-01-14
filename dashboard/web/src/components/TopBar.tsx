'use client'

import { useState, useEffect } from 'react'
import { Bell, Search, User, ChevronDown, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import useSWR from 'swr'

interface Notification {
  id: string
  type: 'approval' | 'alert' | 'info'
  title: string
  time: string
  read: boolean
}

export default function TopBar() {
  const [showNotifications, setShowNotifications] = useState(false)
  const [currentTime, setCurrentTime] = useState('')

  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(new Date().toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }))
    }
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  // Mock notifications
  const notifications: Notification[] = [
    { id: '1', type: 'approval', title: '交易计划待审批', time: '2分钟前', read: false },
    { id: '2', type: 'alert', title: 'BTC 价格异常波动', time: '15分钟前', read: false },
    { id: '3', type: 'info', title: '周报已生成', time: '1小时前', read: true },
  ]

  const unreadCount = notifications.filter(n => !n.read).length

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'approval':
        return <CheckCircle className="w-4 h-4 text-accent-primary" />
      case 'alert':
        return <AlertTriangle className="w-4 h-4 text-accent-warning" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  return (
    <header className="top-bar">
      {/* Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="搜索 Agent、报告、策略..."
            className="input pl-9 py-1.5 text-sm bg-terminal-muted border-transparent focus:bg-terminal-bg"
          />
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Live Time */}
        <div className="text-xs text-gray-500 font-mono">
          {currentTime}
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-gray-400 hover:text-gray-200 transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-accent-danger text-[10px] text-white rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-terminal-surface border border-terminal-border rounded-lg shadow-xl z-50">
              <div className="px-4 py-3 border-b border-terminal-border flex items-center justify-between">
                <span className="text-sm font-medium">通知</span>
                <button className="text-xs text-accent-primary hover:underline">全部已读</button>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    className={`px-4 py-3 flex items-start gap-3 hover:bg-terminal-muted/50 cursor-pointer ${
                      !n.read ? 'bg-terminal-muted/30' : ''
                    }`}
                  >
                    {getNotificationIcon(n.type)}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${!n.read ? 'text-gray-100' : 'text-gray-400'}`}>
                        {n.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">{n.time}</p>
                    </div>
                    {!n.read && (
                      <span className="w-2 h-2 rounded-full bg-accent-primary flex-shrink-0 mt-1.5"></span>
                    )}
                  </div>
                ))}
              </div>
              <div className="px-4 py-2 border-t border-terminal-border">
                <button className="text-xs text-gray-400 hover:text-gray-200">查看全部通知</button>
              </div>
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="flex items-center gap-2 pl-4 border-l border-terminal-border">
          <div className="w-8 h-8 rounded-full bg-accent-primary/20 flex items-center justify-center">
            <User className="w-4 h-4 text-accent-primary" />
          </div>
          <div className="text-sm">
            <div className="text-gray-100 font-medium">董事长</div>
            <div className="text-[10px] text-gray-500">Chairman</div>
          </div>
          <ChevronDown className="w-4 h-4 text-gray-500" />
        </div>
      </div>
    </header>
  )
}
