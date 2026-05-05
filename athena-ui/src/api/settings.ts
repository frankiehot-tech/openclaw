import { api } from './client'

export interface Settings {
  theme: 'dark' | 'light'
  language: 'zh-CN' | 'en-US'
  autoScaling: boolean
  emailAlerts: boolean
  retryMode: 'exponential' | 'linear' | 'none'
}

export async function fetchSettings(): Promise<Settings> {
  return api.get<Settings>('/settings')
}

export async function updateSettings(body: Partial<Settings>): Promise<Settings> {
  return api.put<Settings>('/settings', body)
}
