import { useState, useRef, useEffect, useCallback } from 'react'
import { useChatStore } from '@/stores/chatStore'

export function ChatView() {
  const { messages, activeConversationId, sending, sendMessage } = useChatStore()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const activeMessages = activeConversationId
    ? (messages[activeConversationId] ?? [])
    : []

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeMessages])

  const handleSend = useCallback(() => {
    if (!input.trim() || sending) return
    sendMessage(input)
    setInput('')
  }, [input, sending, sendMessage])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <>
      {/* TopAppBar */}
      <header className="sticky top-0 z-40 flex items-center justify-between px-6 h-14 w-full border-b border-border-100 bg-surface-000/80 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <span className="text-base font-semibold text-text-000 tracking-tight">Neural Core</span>
          <div className="relative ml-4 hidden md:flex items-center">
            <span className="absolute left-3 text-text-400 text-xs">🔍</span>
            <input
              className="pl-9 pr-4 py-1.5 bg-bg-200 border border-border-200 rounded-full text-sm text-text-100 focus:outline-none focus:border-brand-000 focus:ring-1 focus:ring-brand-000/20 w-64 transition-shadow placeholder:text-text-400"
              placeholder="Query archive..."
              type="text"
            />
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button className="p-2 rounded-full text-text-400 hover:text-text-100 hover:bg-bg-200 transition-colors duration-150">🔔</button>
          <button className="p-2 rounded-full text-text-400 hover:text-text-100 hover:bg-bg-200 transition-colors duration-150">📈</button>
          <button className="p-2 rounded-full text-text-400 hover:text-text-100 hover:bg-bg-200 transition-colors duration-150">⋯</button>
        </div>
      </header>

      {/* Chat Canvas */}
      <main className="flex-1 overflow-y-auto w-full flex flex-col items-center">
        <div className="w-full max-w-[960px] px-6 py-12 flex flex-col gap-12">
          {activeMessages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center h-[60vh]">
              <div className="text-center">
                <div className="text-5xl mb-4 opacity-20">🧠</div>
                <p className="text-text-400 text-sm">Input parameters for further synthesis...</p>
              </div>
            </div>
          ) : (
            <>
              {/* Timestamp badge */}
              <div className="text-center w-full mt-4">
                <span className="text-xs text-text-400 uppercase tracking-widest bg-bg-200 px-3 py-1 rounded-full">
                  Session 84.A — Initializing
                </span>
              </div>

              {activeMessages.map((msg) =>
                msg.role === 'user' ? (
                  <div key={msg.id} className="w-full flex flex-col gap-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-6 h-6 rounded bg-bg-300 flex items-center justify-center text-xs font-bold text-text-300">
                        U
                      </span>
                      <span className="text-xs text-text-400 font-medium uppercase tracking-wide">
                        User Prompt
                      </span>
                    </div>
                    <div className="w-full text-text-100 text-[15px] leading-relaxed pr-12">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div
                    key={msg.id}
                    className="w-full flex flex-col gap-3 p-8 bg-surface-000 rounded-xl border border-border-100 shadow-[0_2px_10px_rgba(0,0,0,0.02)]"
                  >
                    <div className="flex items-center gap-2 mb-2 border-b border-border-100 pb-3">
                      <span className="text-brand-000 text-sm font-bold">⚡</span>
                      <span className="text-xs text-brand-000 font-semibold tracking-wide uppercase">
                        Athena Core
                      </span>
                    </div>
                    <div className="text-sm text-text-100 flex flex-col gap-4 leading-relaxed">
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                ),
              )}
            </>
          )}
          <div ref={messagesEndRef} />
          <div className="h-24" />
        </div>
      </main>

      {/* Input Area */}
      <div className="w-full bg-bg-100/90 backdrop-blur pb-6 pt-2 px-6 flex justify-center border-t border-border-100">
        <div className="w-full max-w-[960px] relative shadow-[0_8px_30px_rgb(0,0,0,0.04)] rounded-xl border border-border-200 bg-surface-000 focus-within:border-brand-000 focus-within:ring-1 focus-within:ring-brand-000/20 transition-all duration-300">
          <textarea
            className="w-full bg-transparent border-none resize-none p-4 pr-16 max-h-32 focus:ring-0 text-sm text-text-100 placeholder:text-text-400"
            placeholder="Input parameters for further synthesis..."
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="absolute right-3 bottom-3 p-2 bg-brand-000 text-white rounded-lg hover:bg-brand-100 transition-colors flex items-center justify-center shadow-sm disabled:opacity-50"
          >
            <span className="text-sm">↑</span>
          </button>
        </div>
      </div>
    </>
  )
}
