import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' })
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono' })

export const metadata: Metadata = {
  title: 'AI Quant Company Dashboard',
  description: 'Multi-Agent 量化公司仿真系统 - 董事长办公室',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className={`${inter.variable} ${jetbrains.variable} font-sans bg-terminal-bg text-gray-100 antialiased`}>
        {children}
      </body>
    </html>
  )
}
