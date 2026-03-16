"use client"

import { useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { getDaysRemaining, getUrgencyLevel, getUrgencyConfig } from "@/lib/deadline-types"
import type { Deadline } from "@/lib/deadline-types"

interface CalendarViewProps {
  deadlines: Deadline[]
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

export function CalendarView({ deadlines }: CalendarViewProps) {
  const today = new Date()
  const [viewing, setViewing] = useState(new Date(today.getFullYear(), today.getMonth(), 1))

  const year = viewing.getFullYear()
  const month = viewing.getMonth()

  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells = firstDay + daysInMonth

  function prev() {
    setViewing(new Date(year, month - 1, 1))
  }
  function next() {
    setViewing(new Date(year, month + 1, 1))
  }

  function deadlinesOnDay(day: number) {
    const d = new Date(year, month, day)
    return deadlines.filter((dl) => sameDay(dl.eventDate, d))
  }

  const monthLabel = viewing.toLocaleDateString("en-US", { month: "long", year: "numeric" })

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-foreground">{monthLabel}</h3>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={prev}
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setViewing(new Date(today.getFullYear(), today.getMonth(), 1))}
            className="text-xs text-muted-foreground hover:text-foreground px-2"
          >
            Today
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={next}
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-px">
        {DAYS.map((d) => (
          <div key={d} className="text-center text-xs font-medium text-muted-foreground py-2">
            {d}
          </div>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-7 gap-px bg-border rounded-lg overflow-hidden">
        {Array.from({ length: Math.ceil(cells / 7) * 7 }).map((_, i) => {
          const dayNum = i - firstDay + 1
          const isValid = dayNum >= 1 && dayNum <= daysInMonth
          const cellDate = isValid ? new Date(year, month, dayNum) : null
          const isToday = cellDate ? sameDay(cellDate, today) : false
          const dayDeadlines = isValid ? deadlinesOnDay(dayNum) : []
          const isPast = cellDate ? cellDate < new Date(today.getFullYear(), today.getMonth(), today.getDate()) : false

          return (
            <div
              key={i}
              className={`bg-card min-h-[88px] p-1.5 flex flex-col gap-1 ${!isValid ? "opacity-30" : ""} ${isToday ? "ring-1 ring-inset ring-primary" : ""}`}
            >
              {isValid && (
                <>
                  <span
                    className={`text-xs font-mono w-5 h-5 flex items-center justify-center rounded-full self-end ${
                      isToday
                        ? "bg-primary text-primary-foreground font-semibold"
                        : isPast
                          ? "text-muted-foreground/50"
                          : "text-muted-foreground"
                    }`}
                  >
                    {dayNum}
                  </span>
                  <div className="flex flex-col gap-0.5 overflow-hidden">
                    {dayDeadlines.slice(0, 3).map((dl) => {
                      const days = getDaysRemaining(dl.eventDate)
                      const level = getUrgencyLevel(days)
                      const config = getUrgencyConfig(level)
                      return (
                        <div
                          key={dl.id}
                          title={`${dl.title}\n${dl.type} · ${dl.jurisdiction}\n${dl.ruleCitation}`}
                          className={`truncate rounded text-[10px] px-1.5 py-0.5 leading-tight cursor-default ${config.bgClass} ${config.textClass} border ${config.borderClass}`}
                        >
                          {dl.title}
                        </div>
                      )
                    })}
                    {dayDeadlines.length > 3 && (
                      <span className="text-[10px] text-muted-foreground px-1">
                        +{dayDeadlines.length - 3} more
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap pt-1">
        {[
          { label: "Critical (≤3d)", bgClass: "bg-red-500/15", textClass: "text-red-400", borderClass: "border-red-500/30" },
          { label: "Urgent (≤7d)", bgClass: "bg-amber-500/15", textClass: "text-amber-400", borderClass: "border-amber-500/30" },
          { label: "Due Soon (≤14d)", bgClass: "bg-sky-500/15", textClass: "text-sky-400", borderClass: "border-sky-500/30" },
          { label: "On Track (14d+)", bgClass: "bg-emerald-500/15", textClass: "text-emerald-400", borderClass: "border-emerald-500/30" },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div className={`h-3 w-3 rounded border ${item.bgClass} ${item.borderClass}`} />
            <span className="text-xs text-muted-foreground">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
