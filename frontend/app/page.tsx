'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { ChatSidebar, type CaseItem } from '@/components/chat-sidebar'
import { ChatMessage, ChatWelcome } from '@/components/chat-message'
import { ChatInput } from '@/components/chat-input'
import { ChatHeader } from '@/components/chat-header'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'

/* ------------------------------------------------------------------
   Seed data – realistic legal cases
------------------------------------------------------------------ */
const SEED_CASES: CaseItem[] = [
  {
    id: 'c1',
    title: 'Hargrove v. Meridian Corp.',
    lastMessage: 'Draft motion to compel discovery',
    updatedAt: '2h ago',
    tag: 'Motion',
  },
  {
    id: 'c2',
    title: 'Estate of Whitfield',
    lastMessage: 'Statute of limitations analysis',
    updatedAt: '1d ago',
    tag: 'Deadline',
  },
  {
    id: 'c3',
    title: 'TechNova IP License Review',
    lastMessage: 'Exclusivity clause interpretation',
    updatedAt: '3d ago',
    tag: 'Contract',
  },
  {
    id: 'c4',
    title: 'State v. Caldwell',
    lastMessage: '4th Amendment suppression brief',
    updatedAt: '1w ago',
    tag: 'Research',
  },
]

/* ------------------------------------------------------------------
   ChatSession – isolated hook instance per case
------------------------------------------------------------------ */
function useChatSession(caseId: string | null) {
  return useChat({
    id: caseId ?? 'new',
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  })
}

/* ------------------------------------------------------------------
   Main page
------------------------------------------------------------------ */
export default function CyphergyChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [cases, setCases] = useState<CaseItem[]>(SEED_CASES)
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null)
  const [input, setInput] = useState('')

  const { messages, sendMessage, status, stop } = useChatSession(activeCaseId)
  const isLoading = status === 'streaming' || status === 'submitted'

  const bottomRef = useRef<HTMLDivElement>(null)

  /* Auto-scroll to bottom on new messages */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(() => {
    if (!input.trim() || isLoading) return
    const text = input.trim()
    setInput('')

    // Create a new case if none is active
    if (!activeCaseId) {
      const id = `c${Date.now()}`
      const newCase: CaseItem = {
        id,
        title: text.slice(0, 40) + (text.length > 40 ? '…' : ''),
        lastMessage: text,
        updatedAt: 'just now',
      }
      setCases((prev) => [newCase, ...prev])
      setActiveCaseId(id)
    } else {
      // Update last message preview
      setCases((prev) =>
        prev.map((c) =>
          c.id === activeCaseId
            ? { ...c, lastMessage: text, updatedAt: 'just now' }
            : c,
        ),
      )
    }

    sendMessage({ text })
  }, [input, isLoading, activeCaseId, sendMessage])

  const handleNewChat = useCallback(() => {
    setActiveCaseId(null)
    setInput('')
    if (window.innerWidth < 768) setSidebarOpen(false)
  }, [])

  const handleSelectCase = useCallback((id: string) => {
    setActiveCaseId(id)
    setInput('')
    if (window.innerWidth < 768) setSidebarOpen(false)
  }, [])

  const handleDeleteCase = useCallback(
    (id: string) => {
      setCases((prev) => prev.filter((c) => c.id !== id))
      if (activeCaseId === id) setActiveCaseId(null)
    },
    [activeCaseId],
  )

  const activeCaseTitle = cases.find((c) => c.id === activeCaseId)?.title

  return (
    <div className="flex h-dvh bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <ChatSidebar
        cases={cases}
        activeCaseId={activeCaseId}
        onSelectCase={handleSelectCase}
        onNewChat={handleNewChat}
        onDeleteCase={handleDeleteCase}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
      />

      {/* Main content area – offset by sidebar width */}
      <div
        className={cn(
          'flex flex-col flex-1 min-w-0 transition-all duration-300',
          sidebarOpen ? 'md:ml-64' : 'md:ml-14',
        )}
      >
        {/* Header */}
        <ChatHeader
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
          onNewChat={handleNewChat}
          caseTitle={activeCaseTitle}
        />

        {/* Message area */}
        <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
          {messages.length === 0 ? (
            <div className="flex flex-col flex-1 overflow-y-auto">
              <ChatWelcome
                onPromptClick={(prompt) => {
                  setInput(prompt)
                }}
              />
            </div>
          ) : (
            <ScrollArea className="flex-1 min-h-0">
              <div
                className="flex flex-col gap-5 px-4 py-6 max-w-3xl mx-auto w-full"
                role="log"
                aria-label="Conversation"
                aria-live="polite"
              >
                {messages.map((message, idx) => {
                  const isLast = idx === messages.length - 1
                  const isAiStreaming =
                    isLast && message.role === 'assistant' && isLoading
                  return (
                    <ChatMessage
                      key={message.id}
                      message={message}
                      isStreaming={isAiStreaming}
                    />
                  )
                })}

                {/* Submitted but no AI message yet */}
                {isLoading &&
                  messages[messages.length - 1]?.role === 'user' && (
                    <div className="flex justify-start">
                      <div className="flex gap-3">
                        <div className="h-7 w-7 mt-0.5 rounded-md bg-primary flex items-center justify-center shrink-0">
                          <span className="text-xs font-bold text-primary-foreground">C</span>
                        </div>
                        <div className="rounded-xl rounded-tl-sm border border-border/50 bg-ai-bubble px-4 py-3">
                          <ThinkingDotsInline />
                        </div>
                      </div>
                    </div>
                  )}

                <div ref={bottomRef} />
              </div>
            </ScrollArea>
          )}

          {/* Input */}
          <div className="shrink-0 pt-2">
            <ChatInput
              value={input}
              onChange={setInput}
              onSubmit={handleSend}
              onStop={stop}
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function ThinkingDotsInline() {
  return (
    <div className="flex items-center gap-1 py-0.5" aria-label="Thinking">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-muted-foreground animate-bounce"
          style={{ animationDelay: `${i * 150}ms` }}
        />
      ))}
    </div>
  )
}
