import { describe, it, expect, beforeEach } from 'vitest'
import { useAgentStore } from '../agentStore'
import { useTaskStore } from '../taskStore'
import { useSettingsStore } from '../settingsStore'
import { useChatStore } from '../chatStore'

describe('agentStore', () => {
  beforeEach(() => {
    useAgentStore.setState({
      agents: [],
      selectedAgentId: null,
      loading: false,
      error: null,
    })
  })

  it('starts with empty agents', () => {
    expect(useAgentStore.getState().agents).toEqual([])
    expect(useAgentStore.getState().selectedAgentId).toBeNull()
  })

  it('fetchAgents loads mock agents', async () => {
    await useAgentStore.getState().fetchAgents()
    const state = useAgentStore.getState()
    expect(state.agents.length).toBeGreaterThan(0)
    expect(state.agents[0].name).toBeDefined()
  })

  it('selectAgent sets selectedAgentId', () => {
    useAgentStore.getState().selectAgent('ag-001')
    expect(useAgentStore.getState().selectedAgentId).toBe('ag-001')
  })

  it('updateAgentStatus changes agent status', () => {
    useAgentStore.setState({
      agents: [
        { id: '1', name: 'test', type: 'test', status: 'online', load: 50, uptime: 1000 },
      ],
    })
    useAgentStore.getState().updateAgentStatus('1', 'offline')
    const agent = useAgentStore.getState().agents[0]
    expect(agent.status).toBe('offline')
  })
})

describe('taskStore', () => {
  beforeEach(() => {
    useTaskStore.setState({
      tasks: [],
      filter: { status: 'all', search: '' },
      loading: false,
    })
  })

  it('starts with empty tasks', () => {
    expect(useTaskStore.getState().tasks).toEqual([])
  })

  it('fetchTasks loads mock tasks', async () => {
    await useTaskStore.getState().fetchTasks()
    expect(useTaskStore.getState().tasks.length).toBeGreaterThan(0)
  })

  it('cancelTask marks task as cancelled', async () => {
    await useTaskStore.getState().fetchTasks()
    const taskId = useTaskStore.getState().tasks[0].id
    useTaskStore.getState().cancelTask(taskId)
    const task = useTaskStore.getState().tasks.find((t) => t.id === taskId)
    expect(task?.status).toBe('cancelled')
  })
})

describe('settingsStore', () => {
  it('starts with default theme light', () => {
    expect(useSettingsStore.getState().theme).toBe('light')
  })

  it('setTheme updates theme', () => {
    useSettingsStore.getState().setTheme('light')
    expect(useSettingsStore.getState().theme).toBe('light')
  })

  it('setLanguage updates language', () => {
    useSettingsStore.getState().setLanguage('en-US')
    expect(useSettingsStore.getState().language).toBe('en-US')
  })

  it('setAutoScaling toggles auto scaling', () => {
    useSettingsStore.getState().setAutoScaling(true)
    expect(useSettingsStore.getState().autoScaling).toBe(true)
  })

  it('persist does not throw', () => {
    expect(() => useSettingsStore.getState().persist()).not.toThrow()
  })
})

describe('chatStore', () => {
  it('starts with default conversation', () => {
    const state = useChatStore.getState()
    expect(state.conversations.length).toBeGreaterThan(0)
    expect(state.activeConversationId).toBeTruthy()
  })

  it('creates new conversation', () => {
    const id = useChatStore.getState().createConversation()
    expect(useChatStore.getState().activeConversationId).toBe(id)
    expect(
      useChatStore.getState().conversations.some((c: { id: string }) => c.id === id),
    ).toBe(true)
  })

  it('sends message and receives reply', async () => {
    const store = useChatStore.getState()
    const convId = store.activeConversationId!
    await store.sendMessage('Hello')
    const messages = useChatStore.getState().messages[convId]
    expect(messages.length).toBeGreaterThanOrEqual(2)
    expect(messages[messages.length - 1].role).toBe('assistant')
  })
})
