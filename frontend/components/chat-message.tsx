'use client'

import { cn } from '@/lib/utils'
import { Scale, User, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { UIMessage } from 'ai'

interface ChatMessageProps {
  message: UIMessage
  isStreaming?: boolean
}

function getTextFromMessage(message: UIMessage): string {
  if (!message.parts || !Array.isArray(message.parts)) return ''
  return message.parts
    .filter((p): p is { type: 'text'; text: string } => p.type === 'text')
    .map((p) => p.text)
    .join('')
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)

  const text = getTextFromMessage(message)
  const isUser = message.role === 'user'

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className={cn(
        'group w-full',
        isUser ? 'flex justify-end' : 'flex justify-start',
      )}
    >
      <div
        className={cn(
          'flex gap-3 max-w-[85%] md:max-w-[75%]',
          isUser ? 'flex-row-reverse' : 'flex-row',
        )}
      >
        {/* Avatar */}
        <div className="shrink-0 mt-0.5">
          {isUser ? (
            <div className="h-7 w-7 rounded-full bg-primary/20 flex items-center justify-center">
              <User className="h-3.5 w-3.5 text-primary" />
            </div>
          ) : (
            <div className="h-7 w-7 rounded-md bg-primary flex items-center justify-center">
              <Scale className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
          )}
        </div>

        {/* Bubble */}
        <div className="flex flex-col gap-1">
          <div
            className={cn(
              'rounded-xl px-4 py-3 text-sm leading-relaxed',
              isUser
                ? 'bg-user-bubble text-foreground rounded-tr-sm'
                : 'bg-ai-bubble text-foreground rounded-tl-sm border border-border/50',
            )}
          >
            {isStreaming && !text ? (
              <ThinkingDots />
            ) : (
              <div className="whitespace-pre-wrap break-words">{text}</div>
            )}
            {isStreaming && text && (
              <span className="inline-block w-1.5 h-4 bg-primary/70 ml-0.5 animate-pulse align-text-bottom" />
            )}
          </div>

          {/* Actions row – only for AI, only when not streaming */}
          {!isUser && !isStreaming && text && (
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity ml-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-foreground"
                onClick={handleCopy}
                aria-label="Copy response"
              >
                {copied ? (
                  <Check className="h-3 w-3" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  'h-6 w-6',
                  feedback === 'up'
                    ? 'text-primary'
                    : 'text-muted-foreground hover:text-foreground',
                )}
                onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                aria-label="Helpful"
              >
                <ThumbsUp className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  'h-6 w-6',
                  feedback === 'down'
                    ? 'text-destructive'
                    : 'text-muted-foreground hover:text-foreground',
                )}
                onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                aria-label="Not helpful"
              >
                <ThumbsDown className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ThinkingDots() {
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

/* Welcome / empty state shown before first message */
export function ChatWelcome({ onPromptClick }: { onPromptClick: (prompt: string) => void }) {
  const suggestions = [
    { label: 'Draft a motion to dismiss', tag: 'Motion' },
    { label: 'Check my statute of limitations', tag: 'Deadline' },
    { label: 'Summarize this contract clause', tag: 'Contract' },
    { label: 'Research case law on qualified immunity', tag: 'Research' },
  ]

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-4 pb-8 text-center">
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
        <Scale className="h-6 w-6 text-primary" />
      </div>
      <h1 className="text-2xl font-semibold text-foreground mb-1.5 text-balance">
        How can I help with your case?
      </h1>
      <p className="text-sm text-muted-foreground mb-8 max-w-sm text-balance">
        Ask about deadlines, draft motions, research statutes, or review
        contracts.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {suggestions.map((s) => (
          <button
            key={s.label}
            onClick={() => onPromptClick(s.label)}
            className="group flex items-start gap-3 rounded-xl border border-border bg-card px-4 py-3 text-left text-sm transition-colors hover:border-primary/40 hover:bg-muted"
          >
            <span className="text-foreground leading-snug group-hover:text-foreground">
              {s.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
