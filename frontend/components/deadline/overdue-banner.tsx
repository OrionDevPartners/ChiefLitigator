"use client"

import { useState } from "react"
import { AlertTriangle, X, ChevronDown, ChevronUp } from "lucide-react"
import { getDaysRemaining } from "@/lib/deadline-types"
import type { Deadline } from "@/lib/deadline-types"

interface OverdueBannerProps {
  deadlines: Deadline[]
}

export function OverdueBanner({ deadlines }: OverdueBannerProps) {
  const [dismissed, setDismissed] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const overdue = deadlines.filter((d) => getDaysRemaining(d.eventDate) < 0)

  if (overdue.length === 0 || dismissed) return null

  return (
    <div className="rounded-lg border border-red-500/40 bg-red-500/10 overflow-hidden">
      <div className="flex items-start gap-3 px-4 py-3">
        <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0 animate-pulse" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-red-400">
              {overdue.length} overdue deadline{overdue.length > 1 ? "s" : ""} require immediate attention
            </span>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-xs text-red-400/70 hover:text-red-400 transition-colors"
            >
              {expanded ? (
                <>
                  Hide <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  Show details <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          </div>
          {!expanded && (
            <p className="text-xs text-red-400/70 mt-0.5 truncate">
              {overdue
                .slice(0, 3)
                .map((d) => d.title)
                .join(" · ")}
              {overdue.length > 3 ? ` · +${overdue.length - 3} more` : ""}
            </p>
          )}
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-red-400/60 hover:text-red-400 transition-colors shrink-0"
          aria-label="Dismiss overdue alert"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {expanded && (
        <div className="border-t border-red-500/20 px-4 py-2 space-y-1.5">
          {overdue.map((d) => {
            const daysAgo = Math.abs(getDaysRemaining(d.eventDate))
            return (
              <div key={d.id} className="flex items-center justify-between gap-4 py-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-400 shrink-0" />
                  <span className="text-sm text-foreground truncate">{d.title}</span>
                  <span className="text-xs text-muted-foreground shrink-0">{d.type}</span>
                </div>
                <span className="text-xs font-mono text-red-400 shrink-0">
                  {daysAgo}d overdue
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
