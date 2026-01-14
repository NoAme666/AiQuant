import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import TopBar from '@/components/TopBar'

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' })
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' })

export const metadata: Metadata = {
  title: 'AI Quant Company',
  description: 'Multi-Agent 量化公司仿真与自动研究系统',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className={`${inter.variable} ${jetbrains.variable} font-sans bg-terminal-bg text-gray-100 antialiased`}>
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex-1 ml-56 flex flex-col min-h-screen">
            <TopBar />
            <main className="flex-1 p-6 pb-8 overflow-auto">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  )
}
