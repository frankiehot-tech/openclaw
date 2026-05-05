import { api } from './client'
import type { Task } from '@/types'

export async function fetchTasks(): Promise<Task[]> {
  return api.get<Task[]>('/tasks')
}

export async function fetchTask(id: string): Promise<Task> {
  return api.get<Task>(`/tasks/${id}`)
}

export async function createTask(body: Partial<Task>): Promise<Task> {
  return api.post<Task>('/tasks', body)
}

export async function deleteTask(id: string): Promise<void> {
  return api.delete(`/tasks/${id}`)
}

export async function cancelTask(id: string): Promise<Task> {
  return api.post<Task>(`/tasks/${id}/cancel`, {})
}
