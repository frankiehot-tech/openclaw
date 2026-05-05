import { NavLink } from 'react-router-dom'
import { useChatStore } from '@/stores/chatStore'

const navItems = [
  { id: 'chat', path: '/chat', icon: '💬', label: '对话' },
  { id: 'dashboard', path: '/dashboard', icon: '📊', label: '仪表板' },
  { id: 'agents', path: '/agents', icon: '🐝', label: 'Agent' },
  { id: 'skills', path: '/skills', icon: '⚡', label: '技能' },
  { id: 'monitoring', path: '/monitoring', icon: '📡', label: '监控' },
  { id: 'settings', path: '/settings', icon: '⚙️', label: '设置' },
]

export function Sidebar() {
  const createConversation = useChatStore((s) => s.createConversation)

  return (
    <aside className="fixed left-0 top-0 h-full flex flex-col p-4 w-64 border-r border-border-100 bg-surface-100 z-50">
      <div className="flex items-center gap-3 mb-8 px-2">
        <div className="w-10 h-10 rounded-full bg-brand-200/30 flex items-center justify-center overflow-hidden border border-border-200">
          <span className="text-brand-000 text-lg font-bold">A</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-bold tracking-tight text-text-000">Intelligence OS</span>
          <span className="text-[11px] text-text-400">v4.2.0-stable</span>
        </div>
      </div>

      <button
        onClick={() => { createConversation(); window.location.href = '/chat' }}
        className="mb-6 w-full py-2 px-4 bg-brand-000 text-white rounded text-xs font-semibold shadow-sm hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
      >
        <span className="text-base">+</span>
        New Thread
      </button>

      <nav className="flex-1 flex flex-col gap-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 cursor-pointer transition-all duration-150 rounded text-sm font-medium ${
                isActive
                  ? 'bg-brand-000/10 text-brand-000'
                  : 'text-text-400 hover:text-text-100 hover:bg-bg-200'
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
