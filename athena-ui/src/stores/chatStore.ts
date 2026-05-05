import { create } from 'zustand'
import type { Conversation, Message } from '@/types'

interface ChatStore {
  conversations: Conversation[]
  activeConversationId: string | null
  messages: Record<string, Message[]>
  loading: boolean
  sending: boolean
  createConversation: () => string
  selectConversation: (id: string) => void
  sendMessage: (content: string) => Promise<void>
}

function randomId() {
  return Math.random().toString(36).slice(2, 10)
}

const defaultConv: Conversation = {
  id: 'conv-001',
  title: '新对话',
  createdAt: Date.now(),
  updatedAt: Date.now(),
}

const defaultMessages: Record<string, Message[]> = {
  'conv-001': [
    {
      id: 'msg-001',
      conversationId: 'conv-001',
      role: 'assistant',
      content: '您好，我是 Athena。我可以帮您控制设备、执行自动化任务、爬取数据、分析语义意图。您想做什么？',
      timestamp: Date.now() - 3600000,
    },
  ],
}

export const useChatStore = create<ChatStore>((set, get) => ({
  conversations: [defaultConv],
  activeConversationId: 'conv-001',
  messages: defaultMessages,
  loading: false,
  sending: false,

  createConversation: () => {
    const id = randomId()
    set((state) => ({
      conversations: [
        ...state.conversations,
        { id, title: '新对话', createdAt: Date.now(), updatedAt: Date.now() },
      ],
      messages: { ...state.messages, [id]: [] },
      activeConversationId: id,
    }))
    return id
  },

  selectConversation: (id) => set({ activeConversationId: id }),

  sendMessage: async (content) => {
    const { activeConversationId } = get()
    if (!activeConversationId) return

    const userMsg: Message = {
      id: randomId(),
      conversationId: activeConversationId,
      role: 'user',
      content,
      timestamp: Date.now(),
    }

    set((state) => ({
      sending: true,
      messages: {
        ...state.messages,
        [activeConversationId]: [
          ...(state.messages[activeConversationId] ?? []),
          userMsg,
        ],
      },
      conversations: state.conversations.map((c) =>
        c.id === activeConversationId
          ? { ...c, title: content.slice(0, 30), updatedAt: Date.now() }
          : c,
      ),
    }))

    await new Promise((r) => setTimeout(r, 800))

    const reply: Message = {
      id: randomId(),
      conversationId: activeConversationId,
      role: 'assistant',
      content: `收到您的指令："${content}"。正在通过 Operon 平台调度相应的 Agent 能力模块来执行此任务。`,
      timestamp: Date.now(),
    }

    set((state) => ({
      sending: false,
      messages: {
        ...state.messages,
        [activeConversationId]: [
          ...(state.messages[activeConversationId] ?? []),
          reply,
        ],
      },
    }))
  },
}))
