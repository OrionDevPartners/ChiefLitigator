'use client'

import { Menu, Scale, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatHeaderProps {
  onToggleSidebar: () => void
  onNewChat: () => void
  caseTitle?: string
}

export function ChatHeader({
  onToggleSidebar,
  onNewChat,
  caseTitle,
}: ChatHeaderProps) {
  return (
    <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-background/90 backdrop-blur-sm px-4">
      {/* Left: hamburger */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onToggleSidebar}
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        aria-label="Toggle sidebar"
      >
        <Menu className="h-4 w-4" />
      </Button>

      {/* Center: title */}
      <div className="flex items-center gap-2">
        {caseTitle ? (
          <span className="text-sm font-medium text-foreground truncate max-w-[180px] sm:max-w-xs text-balance">
            {caseTitle}
          </span>
        ) : (
          <div className="flex items-center gap-1.5">
            <Scale className="h-4 w-4 text-primary" />
            <span className="text-sm font-semibold text-foreground">
              Cyphergy
            </span>
          </div>
        )}
      </div>

      {/* Right: new chat */}
      <Button
        variant="ghost"
        size="icon"
        onClick={onNewChat}
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        aria-label="New chat"
      >
        <Plus className="h-4 w-4" />
      </Button>
    </header>
  )
}
