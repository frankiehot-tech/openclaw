import { api } from './client'
import type { Agent } from '@/types'

export async function fetchAgents(): Promise<Agent[]> {
  return api.get<Agent[]>('/agents')
}

export async function fetchAgent(id: string): Promise<Agent> {
  return api.get<Agent>(`/agents/${id}`)
}

export async function createAgent(body: Partial<Agent>): Promise<Agent> {
  return api.post<Agent>('/agents', body)
}

export async function deleteAgent(id: string): Promise<void> {
  return api.delete(`/agents/${id}`)
}
