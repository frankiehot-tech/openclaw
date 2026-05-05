import { api } from './client'

export interface SandboxStatus {
  running: boolean
  nodeVersion: string
  npmVersion: string
  uptime: number
}

export interface ExecutionResult {
  exitCode: number
  stdout: string
  stderr: string
  duration: number
}

export async function fetchSandboxStatus(): Promise<SandboxStatus> {
  return api.get<SandboxStatus>('/sandbox/status')
}

export async function executeCode(
  code: string,
  language: string = 'javascript',
): Promise<ExecutionResult> {
  return api.post<ExecutionResult>('/sandbox/execute', { code, language })
}

export async function restartSandbox(): Promise<void> {
  return api.post<void>('/sandbox/restart', {})
}
