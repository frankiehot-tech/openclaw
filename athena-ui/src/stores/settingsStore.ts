import { create } from 'zustand'

export type Theme = 'dark' | 'light'
export type Language = 'zh-CN' | 'en-US'
export type RetryMode = 'exponential' | 'linear' | 'none'

interface SettingsStore {
  theme: Theme
  language: Language
  autoScaling: boolean
  emailAlerts: boolean
  retryMode: RetryMode
  setTheme: (theme: Theme) => void
  setLanguage: (lang: Language) => void
  setAutoScaling: (enabled: boolean) => void
  setEmailAlerts: (enabled: boolean) => void
  setRetryMode: (mode: RetryMode) => void
  persist: () => void
}

const STORAGE_KEY = 'athena-settings'

function loadSettings(): Partial<SettingsStore> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveSettings(state: SettingsStore) {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      theme: state.theme,
      language: state.language,
      autoScaling: state.autoScaling,
      emailAlerts: state.emailAlerts,
      retryMode: state.retryMode,
    }),
  )
}

const saved = loadSettings()

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  theme: saved.theme ?? 'light',
  language: saved.language ?? 'zh-CN',
  autoScaling: saved.autoScaling ?? false,
  emailAlerts: saved.emailAlerts ?? true,
  retryMode: saved.retryMode ?? 'exponential',

  setTheme: (theme) => {
    set({ theme })
    document.documentElement.setAttribute('data-mode', theme)
    get().persist()
  },

  setLanguage: (language) => set({ language }),
  setAutoScaling: (autoScaling) => set({ autoScaling }),
  setEmailAlerts: (emailAlerts) => set({ emailAlerts }),
  setRetryMode: (retryMode) => set({ retryMode }),

  persist: () => saveSettings(get()),
}))
