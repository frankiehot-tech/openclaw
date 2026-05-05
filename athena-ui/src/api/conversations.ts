import { api } from './client'
import type { Conversation, Message } from '@/types'

export async function fetchConversations(): Promise<Conversation[]> {
  return api.get<Conversation[]>('/conversations')
}

export async function createConversation(
  body: Partial<Conversation>,
): Promise<Conversation> {
  return api.post<Conversation>('/conversations', body)
}

export async function sendMessage(
  conversationId: string,
  content: string,
): Promise<Message> {
  return api.post<Message>(`/conversations/${conversationId}/messages`, {
    content,
  })
}

export async function fetchMessages(
  conversationId: string,
): Promise<Message[]> {
  return api.get<Message[]>(`/conversations/${conversationId}/messages`)
}
