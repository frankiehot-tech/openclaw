import { api } from './client'

export interface Skill {
  id: string
  name: string
  displayName: string
  description: string
  category: string
  enabled: boolean
  version: string
}

export async function fetchSkills(): Promise<Skill[]> {
  return api.get<Skill[]>('/skills')
}

export async function fetchSkill(id: string): Promise<Skill> {
  return api.get<Skill>(`/skills/${id}`)
}

export async function toggleSkill(id: string): Promise<Skill> {
  return api.post<Skill>(`/skills/${id}/toggle`, {})
}

export async function updateSkill(
  id: string,
  body: Partial<Skill>,
): Promise<Skill> {
  return api.put<Skill>(`/skills/${id}`, body)
}
