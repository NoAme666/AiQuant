'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Building2,
  Users,
  FlaskConical,
  TrendingUp,
  FileText,
  CheckSquare,
  MessageSquare,
  Settings,
  LayoutDashboard,
  Shield,
  Activity,
  Wallet,
} from 'lucide-react'

const navigation = [
  {
    group: '总览',
    items: [
      { name: '控制中心', href: '/', icon: LayoutDashboard },
    ],
  },
  {
    group: '公司',
    items: [
      { name: '组织架构', href: '/org', icon: Users },
      { name: '研究中心', href: '/research', icon: FlaskConical },
      { name: '交易台', href: '/trading', icon: TrendingUp },
    ],
  },
  {
    group: '管理',
    items: [
      { name: '报告中心', href: '/reports', icon: FileText },
      { name: '审批队列', href: '/approvals', icon: CheckSquare },
      { name: '会议室', href: '/meetings', icon: MessageSquare },
    ],
  },
  {
    group: '监控',
    items: [
      { name: '风控看板', href: '/risk', icon: Shield },
      { name: '系统状态', href: '/system', icon: Activity },
      { name: '资产总览', href: '/assets', icon: Wallet },
    ],
  },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-56 bg-terminal-surface border-r border-terminal-border flex flex-col z-40">
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-terminal-border">
        <Building2 className="w-6 h-6 text-accent-primary mr-2" />
        <div>
          <h1 className="text-sm font-bold text-gray-100">AI Quant</h1>
          <p className="text-[10px] text-gray-500">Company Dashboard</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {navigation.map((group) => (
          <div key={group.group} className="mb-6">
            <div className="nav-group-title">{group.group}</div>
            <ul className="space-y-1">
              {group.items.map((item) => {
                const isActive = pathname === item.href
                const Icon = item.icon
                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={`nav-item ${isActive ? 'active' : ''}`}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="text-sm">{item.name}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-terminal-border">
        <Link href="/settings" className="nav-item">
          <Settings className="w-4 h-4" />
          <span className="text-sm">设置</span>
        </Link>
        <div className="mt-3 px-3 py-2 bg-terminal-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="status-dot active"></span>
            <span className="text-xs text-gray-400">系统运行中</span>
          </div>
          <div className="text-[10px] text-gray-500 mt-1">
            18 Agents Active
          </div>
        </div>
      </div>
    </aside>
  )
}
