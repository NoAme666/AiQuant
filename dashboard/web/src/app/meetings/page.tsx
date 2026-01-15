'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import useSWR from 'swr'
import {
  MessageSquare,
  Plus,
  Filter,
  Clock,
  User,
  ArrowUpCircle,
  ThumbsUp,
  Calendar,
  Users,
  AlertTriangle,
  CheckCircle,
  Play,
  Pause,
  ChevronRight,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const fetcher = (url: string) => fetch(url).then(res => res.json()).catch(() => null)

interface AgentStatus {
  id: string
  name: string
  current_task: string | null
  in_meeting: boolean
}

interface Message {
  agent_id: string
  agent_name: string
  content: string
  timestamp: string
  type: 'message' | 'proposal' | 'vote' | 'decision'
}

interface Meeting {
  id: string
  title: string
  topic: string
  status: 'scheduled' | 'in_progress' | 'completed'
  start_time: string
  attendees: string[]
  messages: Message[]
  decisions?: string[]
}

// Agent 状态和会议数据从 API 获取

function AgentStatusBadge({ agent }: { agent: AgentStatus }) {
  return (
    <div className={`flex items-center gap-2 p-2 rounded-lg ${agent.in_meeting ? 'bg-accent-primary/20' : 'bg-terminal-muted/30'}`}>
      <span className={`w-2 h-2 rounded-full ${agent.in_meeting ? 'bg-accent-primary animate-pulse' : 'bg-gray-400'}`}></span>
      <Link href={`/chat/${agent.id}`} className="text-xs font-medium text-gray-300 hover:text-accent-primary">
        {agent.name}
      </Link>
      <span className="text-[10px] text-gray-500 truncate flex-1">{agent.current_task || '空闲'}</span>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const typeConfig = {
    message: { bg: 'bg-terminal-muted/30', border: '' },
    proposal: { bg: 'bg-yellow-500/10', border: 'border-l-2 border-yellow-500' },
    vote: { bg: 'bg-accent-success/10', border: 'border-l-2 border-accent-success' },
    decision: { bg: 'bg-accent-primary/10', border: 'border-l-2 border-accent-primary' },
  }
  const config = typeConfig[message.type]

  return (
    <div className={`p-3 rounded-lg ${config.bg} ${config.border}`}>
      <div className="flex items-center gap-2 mb-1">
        <Link href={`/chat/${message.agent_id}`} className="text-sm font-medium text-accent-primary hover:underline">
          {message.agent_name}
        </Link>
        <span className="text-[10px] text-gray-500">{message.timestamp}</span>
        {message.type === 'proposal' && <span className="badge badge-warning text-[8px]">提议</span>}
        {message.type === 'vote' && <span className="badge badge-success text-[8px]">投票</span>}
        {message.type === 'decision' && <span className="badge badge-primary text-[8px]">决议</span>}
      </div>
      <p className="text-sm text-gray-300">{message.content}</p>
    </div>
  )
}

function MeetingCard({ meeting, agentStatuses }: { meeting: Meeting; agentStatuses: AgentStatus[] }) {
  const [expanded, setExpanded] = useState(meeting.status === 'in_progress')

  const statusConfig = {
    scheduled: { label: '即将开始', color: 'text-gray-400', bg: 'bg-gray-500/20' },
    in_progress: { label: '进行中', color: 'text-accent-primary', bg: 'bg-accent-primary/20' },
    completed: { label: '已结束', color: 'text-gray-500', bg: 'bg-gray-600/20' },
  }
  const status = statusConfig[meeting.status]

  return (
    <div className="card">
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-3">
          <div className={`w-10 h-10 rounded-lg ${status.bg} flex items-center justify-center`}>
            {meeting.status === 'in_progress' ? (
              <Play className={`w-5 h-5 ${status.color}`} />
            ) : meeting.status === 'scheduled' ? (
              <Calendar className={`w-5 h-5 ${status.color}`} />
            ) : (
              <CheckCircle className={`w-5 h-5 ${status.color}`} />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 font-mono">{meeting.id}</span>
              <span className={`badge ${status.bg} ${status.color} text-[10px]`}>{status.label}</span>
            </div>
            <h3 className="text-base font-medium text-gray-200 mt-1">{meeting.title}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{meeting.topic}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Clock className="w-3 h-3" />
            {meeting.start_time}
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Users className="w-3 h-3" />
            {meeting.attendees.length}
          </div>
          <ChevronRight className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-terminal-border/50">
          {/* Attendees */}
          <div className="mb-4">
            <h4 className="text-xs font-medium text-gray-400 mb-2">参会人员</h4>
            <div className="flex flex-wrap gap-2">
              {meeting.attendees.map((id) => {
                const agent = agentStatuses.find(a => a.id === id)
                return (
                  <Link
                    key={id}
                    href={`/chat/${id}`}
                    className="px-2 py-1 bg-terminal-muted/30 rounded text-xs text-gray-300 hover:text-accent-primary"
                  >
                    {agent?.name || id}
                  </Link>
                )
              })}
            </div>
          </div>

          {/* Messages / Dialogue */}
          {meeting.messages.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs font-medium text-gray-400 mb-2">会议对话</h4>
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {meeting.messages.map((msg, idx) => (
                  <MessageBubble key={idx} message={msg} />
                ))}
              </div>
            </div>
          )}

          {/* Decisions */}
          {meeting.decisions && meeting.decisions.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-400 mb-2">会议决议</h4>
              <ul className="space-y-1">
                {meeting.decisions.map((decision, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm text-gray-300">
                    <CheckCircle className="w-3 h-3 text-accent-success shrink-0" />
                    {decision}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          {meeting.status === 'in_progress' && (
            <div className="mt-4 pt-4 border-t border-terminal-border/50">
              <button className="btn btn-primary btn-sm w-full">
                <MessageSquare className="w-4 h-4 mr-2" />
                加入会议
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MeetingsPage() {
  // 从 API 获取真实会议数据
  const { data: meetingsData, mutate: mutateMeetings } = useSWR(`${API_BASE}/api/v2/meetings`, fetcher, { refreshInterval: 5000 })
  const { data: agentsData } = useSWR(`${API_BASE}/api/v2/agents/status`, fetcher, { refreshInterval: 5000 })
  
  const meetings: Meeting[] = meetingsData?.meetings || []
  const agentStatuses: AgentStatus[] = Object.entries(agentsData?.agents || {}).map(([id, data]: [string, any]) => ({
    id,
    name: id,
    current_task: data.current_task,
    in_meeting: false,
  }))
  
  const inProgressMeetings = meetings.filter(m => m.status === 'in_progress')
  const scheduledMeetings = meetings.filter(m => m.status === 'scheduled')
  const completedMeetings = meetings.filter(m => m.status === 'completed')

  return (
    <div className="space-y-6 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">会议室</h1>
          <p className="page-subtitle">Agent 对话与议题讨论</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-primary btn-sm">
            <Plus className="w-4 h-4 mr-2" />
            发起会议
          </button>
        </div>
      </div>

      {/* Agent Status - Single Task */}
      <div className="card">
        <h2 className="text-sm font-medium text-gray-400 mb-3">Agent 当前状态 <span className="text-gray-600">(同时只能做一件事)</span></h2>
        <div className="grid grid-cols-6 gap-2">
          {agentStatuses.map((agent) => (
            <AgentStatusBadge key={agent.id} agent={agent} />
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card">
          <div className="text-2xl font-bold text-accent-primary">{inProgressMeetings.length}</div>
          <div className="text-sm text-gray-500">进行中</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-gray-400">{scheduledMeetings.length}</div>
          <div className="text-sm text-gray-500">即将开始</div>
        </div>
        <div className="card">
          <div className="text-2xl font-bold text-gray-500">{completedMeetings.length}</div>
          <div className="text-sm text-gray-500">已结束</div>
        </div>
      </div>

      {/* Meetings */}
      <div className="space-y-4">
        {/* In Progress */}
        {inProgressMeetings.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
              <Play className="w-5 h-5 text-accent-primary" />
              进行中的会议
            </h2>
            <div className="space-y-3">
              {inProgressMeetings.map((meeting) => (
                <MeetingCard key={meeting.id} meeting={meeting} agentStatuses={agentStatuses} />
              ))}
            </div>
          </div>
        )}

        {/* Scheduled */}
        {scheduledMeetings.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-gray-400" />
              即将开始
            </h2>
            <div className="space-y-3">
              {scheduledMeetings.map((meeting) => (
                <MeetingCard key={meeting.id} meeting={meeting} agentStatuses={agentStatuses} />
              ))}
            </div>
          </div>
        )}

        {/* Completed */}
        {completedMeetings.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-gray-100 mb-3 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-gray-500" />
              已结束
            </h2>
            <div className="space-y-3">
              {completedMeetings.map((meeting) => (
                <MeetingCard key={meeting.id} meeting={meeting} agentStatuses={agentStatuses} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
