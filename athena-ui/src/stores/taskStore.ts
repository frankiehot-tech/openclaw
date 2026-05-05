import { create } from 'zustand'
import type { Task, TaskStatus } from '@/types'

export type TaskFilter = {
  status: TaskStatus | 'all'
  search: string
}

interface TaskStore {
  tasks: Task[]
  filter: TaskFilter
  loading: boolean
  setFilter: (filter: Partial<TaskFilter>) => void
  fetchTasks: () => Promise<void>
  cancelTask: (id: string) => void
}

const mockTasks: Task[] = [
  { id: 'TK-042', name: '小红书文案自动发布', status: 'running', progress: 65, stage: '发布中', agentId: 'ag-001', createdAt: Date.now() - 3600000 },
  { id: 'TK-041', name: '竞品价格爬取分析', status: 'completed', progress: 100, stage: '完成', agentId: 'ag-002', createdAt: Date.now() - 7200000 },
  { id: 'TK-040', name: 'App 自动化回归测试', status: 'completed', progress: 100, stage: '完成', agentId: 'ag-003', createdAt: Date.now() - 14400000 },
  { id: 'TK-039', name: '多平台消息同步', status: 'failed', progress: 42, stage: '连接超时', agentId: 'ag-004', createdAt: Date.now() - 21600000 },
]

export const useTaskStore = create<TaskStore>((set) => ({
  tasks: [],
  filter: { status: 'all', search: '' },
  loading: false,

  setFilter: (filter) =>
    set((state) => ({ filter: { ...state.filter, ...filter } })),

  fetchTasks: async () => {
    set({ loading: true })
    await new Promise((r) => setTimeout(r, 300))
    set({ tasks: mockTasks, loading: false })
  },

  cancelTask: (id) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, status: 'cancelled' as const, progress: 0 } : t,
      ),
    })),
}))

export const selectFilteredTasks = (state: TaskStore) => {
  const { tasks, filter } = state
  return tasks.filter((t) => {
    if (filter.status !== 'all' && t.status !== filter.status) return false
    if (filter.search && !t.name.toLowerCase().includes(filter.search.toLowerCase())) return false
    return true
  })
}
