export type Theme = 'light' | 'dark'

export type AgentStatus = 'online' | 'offline' | 'warning' | 'error'

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface Agent {
  id: string
  name: string
  type: string
  status: AgentStatus
  load: number
  uptime: number
}

export interface Task {
  id: string
  name: string
  status: TaskStatus
  progress: number
  stage: string
  agentId: string
  createdAt: number
}

export interface Message {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface Conversation {
  id: string
  title: string
  createdAt: number
  updatedAt: number
}

export interface SystemMetrics {
  cpu: number
  memory: number
  gpu: number
  gpuTemp: number
  activeAgents: number
  queueDepth: number
}
