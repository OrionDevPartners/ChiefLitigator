"use client"

import { getDaysRemaining, getUrgencyLevel, getUrgencyConfig } from "@/lib/deadline-types"
import type { Deadline } from "@/lib/deadline-types"
import { UrgencyBadge } from "@/components/deadline/urgency-badge"
import { BookOpen, Gavel, FileText } from "lucide-react"
import { Empty } from "@/components/ui/empty"

interface TimelineViewProps {
  deadlines: Deadline[]
}

function formatDate(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date)
}

function formatMonthYear(date: Date) {
  return new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" }).format(date)
}

export function TimelineView({ deadlines }: TimelineViewProps) {
  if (deadlines.length === 0) {
    return (
      <Empty
        title="No deadlines"
        description="Add a deadline to get started tracking your legal matters."
        className="py-20 text-muted-foreground"
      />
    )
  }

  // Sort by date ascending
  const sorted = [...deadlines].sort((a, b) => a.eventDate.getTime() - b.eventDate.getTime())

  // Group by month
  const grouped: Record<string, Deadline[]> = {}
  sorted.forEach((d) => {
    const key = formatMonthYear(d.eventDate)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(d)
  })

  return (
    <div className="space-y-8">
      {Object.entries(grouped).map(([month, items]) => (
        <div key={month}>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              {month}
            </span>
            <div className="flex-1 h-px bg-border" />
            <span className="text-xs text-muted-foreground">{items.length} deadline{items.length > 1 ? "s" : ""}</span>
          </div>
          <div className="relative">
            {/* vertical track */}
            <div className="absolute left-[19px] top-0 bottom-0 w-px bg-border" />
            <div className="space-y-3">
              {items.map((deadline) => {
                const days = getDaysRemaining(deadline.eventDate)
                const level = getUrgencyLevel(days)
                const config = getUrgencyConfig(level)
                const isOverdue = days < 0

                return (
                  <div key={deadline.id} className="flex gap-4 group">
                    {/* dot */}
                    <div className="relative z-10 flex-shrink-0 mt-3.5">
                      <div
                        className={`h-[10px] w-[10px] rounded-full border-2 border-background ${config.dotClass} ${isOverdue ? "animate-pulse" : ""}`}
                      />
                    </div>

                    {/* card */}
                    <div
                      className={`flex-1 rounded-lg border bg-card p-4 transition-colors hover:bg-secondary/30 ${isOverdue ? "border-red-500/40" : "border-border"}`}
                    >
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <span className="text-sm font-semibold text-foreground leading-tight">{deadline.title}</span>
                            {deadline.caseName && (
                              <span className="text-xs text-muted-foreground">{deadline.caseName}</span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 flex-wrap">
                            <span className={`inline-flex items-center gap-1 text-xs font-mono px-1.5 py-0.5 rounded bg-secondary text-muted-foreground`}>
                              <Gavel className="h-3 w-3" />
                              {deadline.type}
                            </span>
                            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                              <FileText className="h-3 w-3" />
                              {deadline.jurisdiction}
                            </span>
                            <span className="inline-flex items-center gap-1 text-xs font-mono text-muted-foreground">
                              <BookOpen className="h-3 w-3" />
                              {deadline.ruleCitation}
                            </span>
                          </div>
                          {deadline.notes && (
                            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                              {deadline.notes}
                            </p>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-2 shrink-0">
                          <UrgencyBadge eventDate={deadline.eventDate} />
                          <span className="text-xs text-muted-foreground font-mono">
                            {formatDate(deadline.eventDate)}
                          </span>
                          {deadline.serviceMethod && (
                            <span className="text-xs text-muted-foreground/60">
                              via {deadline.serviceMethod}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
