import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/templates/AppLayout'
import { DashboardView } from '@/views/DashboardView'
import { ChatView } from '@/views/ChatView'
import { AgentView } from '@/views/AgentView'
import { SkillsView } from '@/views/SkillsView'
import { CodeView } from '@/views/CodeView'
import { MonitoringView } from '@/views/MonitoringView'
import { SettingsView } from '@/views/SettingsView'

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="dashboard" element={<DashboardView />} />
        <Route path="chat" element={<ChatView />} />
        <Route path="chat/:conversationId" element={<ChatView />} />
        <Route path="agents" element={<AgentView />} />
        <Route path="agents/:agentId" element={<AgentView />} />
        <Route path="skills" element={<SkillsView />} />
        <Route path="arsenal" element={<CodeView />} />
        <Route path="monitoring" element={<MonitoringView />} />
        <Route path="settings" element={<SettingsView />} />
      </Route>
    </Routes>
  )
}
