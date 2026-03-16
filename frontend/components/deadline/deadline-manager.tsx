"use client"

import { useState } from "react"
import { Scale, LayoutList, Calendar, Clock } from "lucide-react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { AddDeadlineDialog } from "./add-deadline-dialog"
import { OverdueBanner } from "./overdue-banner"
import { TimelineView } from "./views/timeline-view"
import { CalendarView } from "./views/calendar-view"
import { ListView } from "./views/list-view"
import { getDaysRemaining, getUrgencyLevel } from "@/lib/deadline-types"
import type { Deadline, NewDeadlineInput } from "@/lib/deadline-types"

interface DeadlineManagerProps {
  initialDeadlines?: Deadline[]
}

function StatPill({
  label,
  value,
  dotClass,
}: {
  label: string
  value: number
  dotClass: string
}) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-secondary/60 border border-border px-3 py-1.5">
      <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      <span className="text-sm font-semibold text-foreground tabular-nums">{value}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
    </div>
  )
}

export function DeadlineManager({ initialDeadlines = [] }: DeadlineManagerProps) {
  const [deadlines, setDeadlines] = useState<Deadline[]>(initialDeadlines)

  function handleAdd(input: NewDeadlineInput) {
    const newDeadline: Deadline = {
      ...input,
      id: crypto.randomUUID(),
    }
    setDeadlines((prev) => [...prev, newDeadline])
  }

  function handleRemove(id: string) {
    setDeadlines((prev) => prev.filter((d) => d.id !== id))
  }

  // stats
  const overdue = deadlines.filter((d) => getDaysRemaining(d.eventDate) < 0).length
  const critical = deadlines.filter((d) => {
    const days = getDaysRemaining(d.eventDate)
    return days >= 0 && getUrgencyLevel(days) === "critical"
  }).length
  const urgent = deadlines.filter((d) => {
    const days = getDaysRemaining(d.eventDate)
    return days >= 0 && getUrgencyLevel(days) === "high"
  }).length
  const upcoming = deadlines.filter((d) => {
    const days = getDaysRemaining(d.eventDate)
    return days >= 0 && getUrgencyLevel(days) === "medium"
  }).length

  return (
    <div className="min-h-screen bg-background font-sans">
      {/* Top Nav */}
      <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-md bg-primary flex items-center justify-center">
                <Scale className="h-4 w-4 text-primary-foreground" />
              </div>
              <span className="font-semibold text-foreground tracking-tight">Cyphergy</span>
              <span className="text-muted-foreground/40 text-sm">/</span>
              <span className="text-sm text-muted-foreground">Deadline Manager</span>
            </div>
          </div>
          <AddDeadlineDialog onAdd={handleAdd} />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
        {/* Page heading */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-semibold text-foreground text-balance">Deadline Tracker</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Monitor court dates, filings, and procedural deadlines across all matters.
            </p>
          </div>
          {/* Stats pills */}
          <div className="flex items-center gap-2 flex-wrap">
            {overdue > 0 && (
              <StatPill label="Overdue" value={overdue} dotClass="bg-red-400 animate-pulse" />
            )}
            {critical > 0 && (
              <StatPill label="Critical" value={critical} dotClass="bg-red-400" />
            )}
            {urgent > 0 && (
              <StatPill label="Urgent" value={urgent} dotClass="bg-amber-400" />
            )}
            {upcoming > 0 && (
              <StatPill label="Due Soon" value={upcoming} dotClass="bg-sky-400" />
            )}
            <StatPill
              label="Total"
              value={deadlines.length}
              dotClass="bg-muted-foreground"
            />
          </div>
        </div>

        {/* Overdue alert */}
        <OverdueBanner deadlines={deadlines} />

        {/* View tabs */}
        <Tabs defaultValue="timeline" className="space-y-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <TabsList className="bg-secondary/60 border border-border h-9 p-0.5">
              <TabsTrigger
                value="timeline"
                className="flex items-center gap-1.5 text-xs data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground px-3 h-8"
              >
                <Clock className="h-3.5 w-3.5" />
                Timeline
              </TabsTrigger>
              <TabsTrigger
                value="calendar"
                className="flex items-center gap-1.5 text-xs data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground px-3 h-8"
              >
                <Calendar className="h-3.5 w-3.5" />
                Calendar
              </TabsTrigger>
              <TabsTrigger
                value="list"
                className="flex items-center gap-1.5 text-xs data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm text-muted-foreground px-3 h-8"
              >
                <LayoutList className="h-3.5 w-3.5" />
                List
              </TabsTrigger>
            </TabsList>
            <p className="text-xs text-muted-foreground hidden sm:block">
              {deadlines.length === 0
                ? "No deadlines yet — click Add Deadline to get started."
                : `${deadlines.length} deadline${deadlines.length !== 1 ? "s" : ""} across all matters`}
            </p>
          </div>

          <TabsContent value="timeline" className="mt-0">
            <TimelineView deadlines={deadlines} />
          </TabsContent>

          <TabsContent value="calendar" className="mt-0">
            <CalendarView deadlines={deadlines} />
          </TabsContent>

          <TabsContent value="list" className="mt-0">
            <ListView deadlines={deadlines} onRemove={handleRemove} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
