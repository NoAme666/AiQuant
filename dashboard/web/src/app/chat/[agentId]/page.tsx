'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { 
  ArrowLeft, 
  Send, 
  User,
  Bot,
  Paperclip,
  Loader2
} from 'lucide-react'

// Agent 信息映射
const AGENTS: Record<string, { name: string; nameEn: string; persona: string }> = {
  chief_of_staff: { 
    name: '办公室主任', 
    nameEn: 'Chief of Staff',
    persona: 'COO/参谋长风格，流程控，追求效率与规范' 
  },
  cio: { 
    name: '首席投资官', 
    nameEn: 'CIO',
    persona: 'Dalio 风格，原则化、透明归因、重视可复现性' 
  },
  cro: { 
    name: '首席风险官', 
    nameEn: 'CRO',
    persona: 'Howard Marks 风格，风险第一、关注尾部风险' 
  },
  skeptic: { 
    name: '质疑者', 
    nameEn: 'Skeptic',
    persona: 'Munger 风格，反向思维、毒舌、默认你是错的' 
  },
  head_of_research: { 
    name: '研究总监', 
    nameEn: 'Head of Research',
    persona: 'Simons 风格，数据至上、讨厌无法证伪的叙事' 
  },
  alpha_a_lead: { 
    name: 'Alpha A 组长', 
    nameEn: 'Alpha Team A Lead',
    persona: 'AQR 风格，因子分解、追求可解释性、学术严谨' 
  },
  alpha_b_lead: { 
    name: 'Alpha B 组长', 
    nameEn: 'Alpha Team B Lead',
    persona: '反叙事/结构派，质疑主流观点、寻找结构性机会' 
  },
  data_quality_auditor: { 
    name: '数据质量审计', 
    nameEn: 'Data Quality Auditor',
    persona: '数据闸门守护者，对未来函数零容忍' 
  },
  backtest_lead: { 
    name: '回测主管', 
    nameEn: 'Backtest Lead',
    persona: '可复现至上，追求实验标准化' 
  },
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export default function ChatPage() {
  const params = useParams()
  const agentId = params.agentId as string
  const agent = AGENTS[agentId] || { name: agentId, nameEn: agentId, persona: '' }
  
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  
  useEffect(() => {
    scrollToBottom()
  }, [messages])
  
  // 发送消息
  const sendMessage = async () => {
    if (!input.trim() || isLoading) return
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    
    // 模拟 API 调用
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: getSimulatedResponse(agent.persona, input),
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
      setIsLoading(false)
    }, 1500)
  }
  
  // 模拟回复
  const getSimulatedResponse = (persona: string, query: string): string => {
    const responses: Record<string, string[]> = {
      'CRO': [
        '从风险角度来看，这个策略的最大回撤超过了我们的阈值。在批准之前，我需要看到压力测试的结果。',
        '我的第一反应是保守的。能告诉我这个策略在 2020 年 3 月会如何表现吗？',
        '每个策略都需要明确的 Kill Switch 条件。这个策略的止损线是什么？',
      ],
      'Skeptic': [
        '让我来挑战一下这个假设。你怎么证明这不是过拟合？样本外的表现如何？',
        '等等，这个策略看起来太好了。告诉我它会怎么失败。',
        '我需要看到参数敏感性分析。如果参数变化 20%，结果会怎样？',
      ],
      'default': [
        '收到您的消息。让我仔细分析一下这个问题。',
        '这是一个有趣的观点。基于我的分析，我认为...',
        '我理解您的关注。让我从专业角度给出一些建议...',
      ],
    }
    
    const key = Object.keys(responses).find(k => persona.includes(k)) || 'default'
    const options = responses[key]
    return options[Math.floor(Math.random() * options.length)]
  }
  
  return (
    <div className="h-screen flex flex-col">
      {/* 顶部导航 */}
      <header className="flex items-center gap-4 p-4 border-b border-terminal-border bg-terminal-surface">
        <Link href="/org-chart" className="p-2 rounded-lg hover:bg-terminal-muted transition-colors">
          <ArrowLeft className="w-5 h-5 text-gray-400" />
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-terminal-muted flex items-center justify-center">
            <Bot className="w-5 h-5 text-accent-primary" />
          </div>
          <div>
            <h1 className="font-semibold text-gray-100">{agent.name}</h1>
            <p className="text-xs text-gray-400">{agent.persona}</p>
          </div>
        </div>
        <span className="ml-auto flex items-center gap-2 text-sm text-gray-400">
          <span className="status-dot active"></span>
          在线
        </span>
      </header>
      
      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <Bot className="w-16 h-16 text-terminal-border mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">开始与 {agent.name} 对话</h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              作为董事长，您可以与任何 Agent 进行 1v1 对话。
              您的指令将形成 ChairmanDirective 并进入审计链。
            </p>
          </div>
        )}
        
        {messages.map(message => (
          <div 
            key={message.id}
            className={`flex items-start gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
              message.role === 'user' 
                ? 'bg-accent-primary/20' 
                : 'bg-terminal-muted'
            }`}>
              {message.role === 'user' 
                ? <User className="w-4 h-4 text-accent-primary" />
                : <Bot className="w-4 h-4 text-gray-400" />
              }
            </div>
            <div className={`max-w-[70%] rounded-lg px-4 py-3 ${
              message.role === 'user' 
                ? 'bg-accent-primary text-terminal-bg' 
                : 'bg-terminal-surface border border-terminal-border'
            }`}>
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <p className={`text-xs mt-2 ${
                message.role === 'user' ? 'text-terminal-bg/60' : 'text-gray-500'
              }`}>
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-terminal-muted flex items-center justify-center">
              <Bot className="w-4 h-4 text-gray-400" />
            </div>
            <div className="bg-terminal-surface border border-terminal-border rounded-lg px-4 py-3">
              <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* 输入区域 */}
      <div className="p-4 border-t border-terminal-border bg-terminal-surface">
        <div className="flex items-center gap-3">
          <button className="p-2 rounded-lg hover:bg-terminal-muted transition-colors text-gray-400">
            <Paperclip className="w-5 h-5" />
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder={`向 ${agent.name} 发送消息...`}
            className="input flex-1"
            disabled={isLoading}
          />
          <button 
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          提示：您作为董事长只能进行 1v1 对话，所有对话都会被记录审计
        </p>
      </div>
    </div>
  )
}
