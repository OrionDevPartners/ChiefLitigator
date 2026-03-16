"use client"

import { useState } from "react"
import { ChevronUp, ChevronDown, ChevronsUpDown, BookOpen, Trash2 } from "lucide-react"
import { getDaysRemaining, getUrgencyLevel, getUrgencyConfig } from "@/lib/deadline-types"
import type { Deadline } from "@/lib/deadline-types"
import { UrgencyBadge } from "@/components/deadline/urgency-badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Empty } from "@/components/ui/empty"

interface ListViewProps {
  deadlines: Deadline[]
  onRemove?: (id: string) => void
}

type SortKey = "eventDate" | "type" | "jurisdiction" | "daysRemaining" | "title"
type SortDir = "asc" | "desc"

function formatDate(date: Date) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date)
}

export function ListView({ deadlines, onRemove }: ListViewProps) {
  const [sortKey, setSortKey] = useState<SortKey>("eventDate")
  const [sortDir, setSortDir] = useState<SortDir>("asc")
  const [filter, setFilter] = useState("")

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
  }

  const filtered = deadlines.filter((d) => {
    const q = filter.toLowerCase()
    return (
      d.title.toLowerCase().includes(q) ||
      d.type.toLowerCase().includes(q) ||
      d.jurisdiction.toLowerCase().includes(q) ||
      d.ruleCitation.toLowerCase().includes(q) ||
      (d.caseName?.toLowerCase().includes(q) ?? false)
    )
  })

  const sorted = [...filtered].sort((a, b) => {
    let cmp = 0
    switch (sortKey) {
      case "eventDate":
        cmp = a.eventDate.getTime() - b.eventDate.getTime()
        break
      case "type":
        cmp = a.type.localeCompare(b.type)
        break
      case "jurisdiction":
        cmp = a.jurisdiction.localeCompare(b.jurisdiction)
        break
      case "daysRemaining":
        cmp = getDaysRemaining(a.eventDate) - getDaysRemaining(b.eventDate)
        break
      case "title":
        cmp = a.title.localeCompare(b.title)
        break
    }
    return sortDir === "asc" ? cmp : -cmp
  })

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground/40" />
    return sortDir === "asc" ? (
      <ChevronUp className="h-3.5 w-3.5 text-primary" />
    ) : (
      <ChevronDown className="h-3.5 w-3.5 text-primary" />
    )
  }

  function ColHeader({ col, label }: { col: SortKey; label: string }) {
    return (
      <button
        onClick={() => toggleSort(col)}
        className="flex items-center gap-1 group hover:text-foreground transition-colors"
      >
        <span>{label}</span>
        <SortIcon col={col} />
      </button>
    )
  }

  if (deadlines.length === 0) {
    return (
      <Empty
        title="No deadlines"
        description="Add a deadline to get started tracking your legal matters."
        className="py-20 text-muted-foreground"
      />
    )
  }

  return (
    <div className="space-y-3">
      {/* Search filter */}
      <div className="flex items-center gap-3">
        <Input
          placeholder="Filter by matter, type, court, or citation…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-sm bg-input border-border text-foreground placeholder:text-muted-foreground h-8 text-sm"
        />
        <span className="text-xs text-muted-foreground ml-auto">
          {sorted.length} of {deadlines.length} deadline{deadlines.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/50">
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">
                  <ColHeader col="title" label="Matter" />
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">
                  <ColHeader col="type" label="Type" />
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">
                  <ColHeader col="jurisdiction" label="Jurisdiction" />
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">
                  Rule Citation
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">
                  <ColHeader col="eventDate" label="Deadline" />
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">
                  <ColHeader col="daysRemaining" label="Urgency" />
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground whitespace-nowrap">
                  Service
                </th>
                {onRemove && <th className="w-10 px-2 py-2.5" />}
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr>
                  <td
                    colSpan={onRemove ? 8 : 7}
                    className="px-4 py-10 text-center text-sm text-muted-foreground"
                  >
                    No deadlines match your filter.
                  </td>
                </tr>
              ) : (
                sorted.map((dl, i) => {
                  const days = getDaysRemaining(dl.eventDate)
                  const level = getUrgencyLevel(days)
                  const config = getUrgencyConfig(level)
                  const isOverdue = days < 0

                  return (
                    <tr
                      key={dl.id}
                      className={`border-b border-border/60 last:border-0 transition-colors hover:bg-secondary/20 ${
                        isOverdue ? "bg-red-500/5" : i % 2 === 0 ? "" : "bg-secondary/10"
                      }`}
                    >
                      <td className="px-4 py-3 max-w-[200px]">
                        <div className="font-medium text-foreground truncate" title={dl.title}>
                          {dl.title}
                        </div>
                        {dl.caseName && (
                          <div className="text-xs text-muted-foreground truncate mt-0.5">
                            {dl.caseName}
                            {dl.caseNumber ? ` · ${dl.caseNumber}` : ""}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center text-xs font-mono px-2 py-0.5 rounded bg-secondary text-muted-foreground">
                          {dl.type}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-sm text-foreground font-mono">{dl.jurisdiction}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 text-xs font-mono text-muted-foreground">
                          <BookOpen className="h-3 w-3 shrink-0" />
                          {dl.ruleCitation}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-sm font-mono text-foreground">
                          {formatDate(dl.eventDate)}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <UrgencyBadge eventDate={dl.eventDate} size="sm" />
                      </td>
                      <td className="px-4 py-3 max-w-[140px]">
                        <span className="text-xs text-muted-foreground truncate block" title={dl.serviceMethod}>
                          {dl.serviceMethod}
                        </span>
                      </td>
                      {onRemove && (
                        <td className="px-2 py-3">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground/40 hover:text-red-400 hover:bg-red-500/10"
                            onClick={() => onRemove(dl.id)}
                            aria-label={`Remove ${dl.title}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      )}
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
