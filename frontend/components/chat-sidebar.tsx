'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  Scale,
  Plus,
  ChevronLeft,
  Folder,
  MessageSquare,
  Trash2,
  MoreHorizontal,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ScrollArea } from '@/components/ui/scroll-area'

export interface CaseItem {
  id: string
  title: string
  lastMessage: string
  updatedAt: string
  tag?: 'Motion' | 'Deadline' | 'Research' | 'Contract'
}

interface ChatSidebarProps {
  cases: CaseItem[]
  activeCaseId: string | null
  onSelectCase: (id: string) => void
  onNewChat: () => void
  onDeleteCase: (id: string) => void
  isOpen: boolean
  onToggle: () => void
}

const TAG_COLORS: Record<string, string> = {
  Motion: 'bg-blue-500/15 text-blue-400',
  Deadline: 'bg-rose-500/15 text-rose-400',
  Research: 'bg-amber-500/15 text-amber-400',
  Contract: 'bg-emerald-500/15 text-emerald-400',
}

export function ChatSidebar({
  cases,
  activeCaseId,
  onSelectCase,
  onNewChat,
  onDeleteCase,
  isOpen,
  onToggle,
}: ChatSidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          'fixed top-0 left-0 z-30 flex h-full flex-col bg-sidebar border-r border-sidebar-border',
          'transition-all duration-300 ease-in-out',
          isOpen ? 'w-64' : 'w-0 md:w-14',
          'overflow-hidden',
        )}
        aria-label="Case navigation"
      >
        {/* Header */}
        <div className="flex h-14 shrink-0 items-center justify-between px-3 border-b border-sidebar-border">
          {isOpen ? (
            <>
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
                  <Scale className="h-4 w-4 text-primary-foreground" />
                </div>
                <span className="font-semibold text-sm tracking-tight text-sidebar-foreground">
                  Cyphergy
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
                onClick={onToggle}
                aria-label="Collapse sidebar"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <div className="mx-auto flex h-7 w-7 items-center justify-center rounded-md bg-primary">
              <Scale className="h-4 w-4 text-primary-foreground" />
            </div>
          )}
        </div>

        {/* New Chat button */}
        <div className={cn('shrink-0 p-2', !isOpen && 'flex justify-center')}>
          {isOpen ? (
            <Button
              onClick={onNewChat}
              variant="ghost"
              className="w-full justify-start gap-2 text-sm text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
            >
              <Plus className="h-4 w-4 shrink-0" />
              New Chat
            </Button>
          ) : (
            <Button
              onClick={onNewChat}
              variant="ghost"
              size="icon"
              className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
              aria-label="New chat"
            >
              <Plus className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Cases label */}
        {isOpen && (
          <div className="shrink-0 px-3 pb-1">
            <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-widest">
              <Folder className="h-3 w-3" />
              Cases
            </div>
          </div>
        )}

        {/* Case list */}
        <ScrollArea className="flex-1 min-h-0">
          <nav className="flex flex-col gap-0.5 p-2" aria-label="Cases">
            {cases.map((c) => (
              <div
                key={c.id}
                className={cn(
                  'group relative flex items-center rounded-md cursor-pointer',
                  'transition-colors duration-150',
                  activeCaseId === c.id
                    ? 'bg-sidebar-accent text-sidebar-foreground'
                    : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground',
                  isOpen ? 'px-2 py-2' : 'justify-center p-2',
                )}
                onClick={() => onSelectCase(c.id)}
                onMouseEnter={() => setHoveredId(c.id)}
                onMouseLeave={() => setHoveredId(null)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && onSelectCase(c.id)}
                aria-current={activeCaseId === c.id ? 'page' : undefined}
                aria-label={c.title}
              >
                {!isOpen ? (
                  <MessageSquare className="h-4 w-4 shrink-0" />
                ) : (
                  <>
                    <div className="flex flex-col flex-1 min-w-0 gap-0.5">
                      <span className="truncate text-sm font-medium leading-tight">
                        {c.title}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {c.tag && (
                          <span
                            className={cn(
                              'text-[10px] font-medium px-1.5 py-0.5 rounded-full leading-none shrink-0',
                              TAG_COLORS[c.tag],
                            )}
                          >
                            {c.tag}
                          </span>
                        )}
                        <span className="truncate text-[11px] text-muted-foreground">
                          {c.lastMessage}
                        </span>
                      </div>
                    </div>
                    <div
                      className={cn(
                        'ml-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0',
                        activeCaseId === c.id && 'opacity-100',
                      )}
                    >
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-muted-foreground hover:text-foreground hover:bg-sidebar-border"
                            onClick={(e) => e.stopPropagation()}
                            aria-label={`Options for ${c.title}`}
                          >
                            <MoreHorizontal className="h-3.5 w-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          side="right"
                          align="start"
                          className="w-36 bg-popover border-border"
                        >
                          <DropdownMenuItem
                            className="text-destructive-foreground focus:text-destructive-foreground gap-2"
                            onClick={(e) => {
                              e.stopPropagation()
                              onDeleteCase(c.id)
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </>
                )}
              </div>
            ))}

            {cases.length === 0 && isOpen && (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                No cases yet. Start a new chat.
              </div>
            )}
          </nav>
        </ScrollArea>

        {/* Footer */}
        {isOpen && (
          <div className="shrink-0 border-t border-sidebar-border p-3">
            <div className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                <span className="text-xs font-semibold text-primary">JD</span>
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-medium text-sidebar-foreground truncate">
                  Jane Doe
                </span>
                <span className="text-[11px] text-muted-foreground truncate">
                  Attorney
                </span>
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}
