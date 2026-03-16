"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Calendar, Clock } from "lucide-react"

interface Deadline {
  id: string
  title: string
  type: string
  date: string
  daysLeft: number
  assignee: string
  court?: string
}

const deadlines: Deadline[] = [
  {
    id: "d1",
    title: "Motion to Compel — Discovery Response",
    type: "Motion",
    date: "Mar 19, 2026",
    daysLeft: 3,
    assignee: "J. Mercer",
    court: "SDNY",
  },
  {
    id: "d2",
    title: "Expert Witness Disclosure",
    type: "Disclosure",
    date: "Mar 23, 2026",
    daysLeft: 7,
    assignee: "A. Voss",
  },
  {
    id: "d3",
    title: "Deposition of R. Hartwell",
    type: "Deposition",
    date: "Mar 26, 2026",
    daysLeft: 10,
    assignee: "J. Mercer",
  },
  {
    id: "d4",
    title: "Mediation Session — Pre-Trial",
    type: "Hearing",
    date: "Mar 28, 2026",
    daysLeft: 12,
    assignee: "Full Team",
    court: "SDNY",
  },
  {
    id: "d5",
    title: "Summary Judgment Response Brief",
    type: "Filing",
    date: "Apr 2, 2026",
    daysLeft: 17,
    assignee: "A. Voss",
    court: "SDNY",
  },
  {
    id: "d6",
    title: "Pretrial Conference",
    type: "Hearing",
    date: "Apr 14, 2026",
    daysLeft: 29,
    assignee: "J. Mercer",
    court: "SDNY",
  },
]

function urgencyConfig(days: number) {
  if (days <= 3) return {
    dot: "bg-[oklch(0.62_0.23_25)]",
    badge: "bg-[oklch(0.62_0.23_25/0.15)] text-[oklch(0.62_0.23_25)]",
    label: "Critical",
    border: "border-l-[oklch(0.62_0.23_25)]",
  }
  if (days <= 7) return {
    dot: "bg-[oklch(0.76_0.18_65)]",
    badge: "bg-[oklch(0.76_0.18_65/0.15)] text-[oklch(0.76_0.18_65)]",
    label: "Soon",
    border: "border-l-[oklch(0.76_0.18_65)]",
  }
  if (days <= 14) return {
    dot: "bg-[oklch(0.6_0.2_250)]",
    badge: "bg-[oklch(0.6_0.2_250/0.15)] text-[oklch(0.6_0.2_250)]",
    label: "Upcoming",
    border: "border-l-[oklch(0.6_0.2_250)]",
  }
  return {
    dot: "bg-[oklch(0.64_0.18_160)]",
    badge: "bg-[oklch(0.64_0.18_160/0.15)] text-[oklch(0.64_0.18_160)]",
    label: "Planned",
    border: "border-l-[oklch(0.64_0.18_160)]",
  }
}

export function UpcomingDeadlines() {
  return (
    <Card className="flex flex-col gap-0 border-border bg-card">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm font-semibold text-foreground">Upcoming Deadlines</CardTitle>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[oklch(0.62_0.23_25)] inline-block" />
            {String.fromCharCode(8804)}3d
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[oklch(0.76_0.18_65)] inline-block" />
            7d
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[oklch(0.6_0.2_250)] inline-block" />
            14d
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[oklch(0.64_0.18_160)] inline-block" />
            14d+
          </span>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-2 p-4 pt-0">
        {deadlines.map((d) => {
          const urg = urgencyConfig(d.daysLeft)
          return (
            <div
              key={d.id}
              className={`flex items-start gap-3 p-3 rounded-md border border-border border-l-2 bg-secondary/30 hover:bg-secondary/60 transition-colors cursor-pointer ${urg.border}`}
              role="listitem"
            >
              {/* dot */}
              <div className="mt-0.5 shrink-0">
                <span className={`block w-2 h-2 rounded-full ${urg.dot}`} />
              </div>

              {/* content */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground leading-snug truncate">{d.title}</p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="text-[10px] text-muted-foreground">{d.type}</span>
                  {d.court && (
                    <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1 rounded">
                      {d.court}
                    </span>
                  )}
                  <span className="text-[10px] text-muted-foreground">{d.assignee}</span>
                </div>
              </div>

              {/* right: date + badge */}
              <div className="shrink-0 flex flex-col items-end gap-1">
                <div className="flex items-center gap-1 text-[10px] text-muted-foreground font-mono">
                  <Clock className="w-3 h-3" />
                  {d.date}
                </div>
                <Badge className={`text-[9px] px-1.5 py-0 border-0 font-medium ${urg.badge}`}>
                  {d.daysLeft}d left
                </Badge>
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
