'use client'

import { useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { ArrowUp, Square, Paperclip } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  onStop?: () => void
  isLoading: boolean
  disabled?: boolean
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  onStop,
  isLoading,
  disabled,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  /* Auto-resize textarea */
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isLoading && value.trim()) {
        onSubmit()
      }
    }
  }

  const canSubmit = value.trim().length > 0 && !disabled

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 md:pb-6">
      <div
        className={cn(
          'relative flex flex-col rounded-2xl border bg-input-surface transition-colors',
          'border-input-border focus-within:border-primary/50',
        )}
        role="region"
        aria-label="Message input"
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your case, draft a motion, check a deadline..."
          disabled={disabled || isLoading}
          rows={1}
          aria-label="Message"
          aria-multiline="true"
          className={cn(
            'w-full resize-none bg-transparent px-4 pt-3.5 pb-2 text-sm text-foreground',
            'placeholder:text-muted-foreground',
            'focus:outline-none',
            'leading-relaxed min-h-[52px] max-h-[200px]',
            'disabled:opacity-50',
          )}
        />

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          {/* Left: attachment hint */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            aria-label="Attach file (coming soon)"
            disabled
            title="Attach file"
          >
            <Paperclip className="h-3.5 w-3.5" />
          </Button>

          {/* Right: submit / stop */}
          <div className="flex items-center gap-1.5">
            <span className="hidden sm:block text-[11px] text-muted-foreground select-none">
              {isLoading ? '' : 'Shift+Enter for new line'}
            </span>

            {isLoading ? (
              <Button
                onClick={onStop}
                size="icon"
                variant="ghost"
                className="h-8 w-8 rounded-lg bg-primary/10 text-primary hover:bg-primary/20"
                aria-label="Stop generating"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
              </Button>
            ) : (
              <Button
                onClick={onSubmit}
                disabled={!canSubmit}
                size="icon"
                className={cn(
                  'h-8 w-8 rounded-lg transition-all',
                  canSubmit
                    ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                    : 'bg-muted text-muted-foreground cursor-not-allowed',
                )}
                aria-label="Send message"
              >
                <ArrowUp className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      <p className="mt-2 text-center text-[11px] text-muted-foreground">
        Cyphergy may make mistakes. Verify all legal information independently.
      </p>
    </div>
  )
}
