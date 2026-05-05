export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8123/api/v1'
const MAX_RETRIES = 3
const RETRY_DELAY = 1000

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retries = MAX_RETRIES,
): Promise<T> {
  const url = `${BASE_URL}${path}`

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({ message: res.statusText }))
        throw new ApiError(res.status, body.message ?? res.statusText)
      }

      return res.json()
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          window.location.href = '/login'
        }
        throw err
      }

      if (attempt === retries) throw err
      await delay(RETRY_DELAY * Math.pow(2, attempt))
    }
  }

  throw new Error('unreachable')
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path)
  },

  post<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
  },

  put<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, { method: 'PUT', body: JSON.stringify(body) })
  },

  delete(path: string): Promise<void> {
    return request<void>(path, { method: 'DELETE' })
  },
}
