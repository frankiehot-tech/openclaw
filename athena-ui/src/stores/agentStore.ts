import { create } from 'zustand'
import type { Agent, AgentStatus } from '@/types'

interface AgentStore {
  agents: Agent[]
  selectedAgentId: string | null
  loading: boolean
  error: string | null
  fetchAgents: () => Promise<void>
  selectAgent: (id: string) => void
  updateAgentStatus: (id: string, status: AgentStatus) => void
}

const mockAgents: Agent[] = [
  { id: 'ag-001', name: 'content-agent', type: '内容生产', status: 'online', load: 67, uptime: 34200 },
  { id: 'ag-002', name: 'research-agent', type: '数据研究', status: 'online', load: 43, uptime: 51800 },
  { id: 'ag-003', name: 'test-agent', type: '自动化测试', status: 'online', load: 22, uptime: 86400 },
  { id: 'ag-004', name: 'bridge-agent', type: '消息桥接', status: 'offline', load: 0, uptime: 0 },
  { id: 'ag-005', name: 'semantic-agent', type: '语义理解', status: 'online', load: 55, uptime: 26800 },
  { id: 'ag-006', name: 'vision-agent', type: '视觉处理', status: 'warning', load: 89, uptime: 14200 },
]

export const useAgentStore = create<AgentStore>((set) => ({
  agents: [],
  selectedAgentId: null,
  loading: false,
  error: null,

  fetchAgents: async () => {
    set({ loading: true, error: null })
    await new Promise((r) => setTimeout(r, 400))
    set({ agents: mockAgents, loading: false })
  },

  selectAgent: (id) => set({ selectedAgentId: id }),

  updateAgentStatus: (id, status) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, status } : a)),
    })),
}))

export const selectAgentById = (id: string) => (state: AgentStore) =>
  state.agents.find((a) => a.id === id) ?? null
