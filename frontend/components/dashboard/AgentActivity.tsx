"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, CheckCircle2, Clock, FileSearch, Loader2, Search, Zap } from "lucide-react"

type EventType = "complete" | "running" | "queued" | "flagged"

interface AgentEvent {
  id: string
  agent: string
  action: string
  detail: string
  time: string
  type: EventType
  duration?: string
}

/** Data loaded from case context via props. No hardcoded data. */

const typeConfig: Record<EventType, { icon: React.ElementType; iconClass: string; badgeClass: string; label: string }> = {
  complete: {
    icon: CheckCircle2,
    iconClass: "text-[oklch(0.64_0.18_160)]",
    badgeClass: "bg-[oklch(0.64_0.18_160/0.15)] text-[oklch(0.64_0.18_160)]",
    label: "Done",
  },
  running: {
    icon: Loader2,
    iconClass: "text-[oklch(0.6_0.2_250)] animate-spin",
    badgeClass: "bg-[oklch(0.6_0.2_250/0.15)] text-[oklch(0.6_0.2_250)]",
    label: "Running",
  },
  queued: {
    icon: Clock,
    iconClass: "text-muted-foreground",
    badgeClass: "bg-muted text-muted-foreground",
    label: "Queued",
  },
  flagged: {
    icon: Zap,
    iconClass: "text-[oklch(0.62_0.23_25)]",
    badgeClass: "bg-[oklch(0.62_0.23_25/0.15)] text-[oklch(0.62_0.23_25)]",
    label: "Flagged",
  },
}

const agentIcons: Record<string, React.ElementType> = {
  ContractAnalyst: FileSearch,
  PrecedentFinder: Search,
  RiskScorer: Zap,
  DocReview: Bot,
  TimelineBuilder: Clock,
  DiscoveryBot: FileSearch,
}

export function AgentActivity({ events = [] }: { events?: AgentEvent[] }) {
  const runningCount = events.filter((ev) => ev.type === "running").length

  return (
    <Card className="flex flex-col gap-0 border-border bg-card">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm font-semibold text-foreground">Agent Activity</CardTitle>
        </div>
        {runningCount > 0 && (
          <Badge variant="secondary" className="text-[10px] font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-[oklch(0.6_0.2_250)] mr-1.5 animate-pulse inline-block" />
            {runningCount} running
          </Badge>
        )}
      </CardHeader>

      <CardContent className="p-4 pt-0 flex flex-col gap-0">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
            <Bot className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">No agent activity yet</p>
          </div>
        ) : events.map((ev, i) => {
          const cfg = typeConfig[ev.type]
          const AgentIcon = agentIcons[ev.agent] ?? Bot
          const StatusIcon = cfg.icon
          return (
            <div key={ev.id} className="flex gap-3 group">
              {/* Timeline spine */}
              <div className="flex flex-col items-center shrink-0 pt-1">
                <StatusIcon className={`w-3.5 h-3.5 shrink-0 ${cfg.iconClass}`} />
                {i < events.length - 1 && (
                  <div className="w-px flex-1 bg-border mt-1 mb-1 min-h-[16px]" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 pb-3 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <AgentIcon className="w-3 h-3 text-muted-foreground shrink-0" />
                    <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                      {ev.agent}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {ev.duration && (
                      <span className="text-[10px] font-mono text-muted-foreground/60">{ev.duration}</span>
                    )}
                    <span className="text-[10px] text-muted-foreground">{ev.time}</span>
                  </div>
                </div>
                <p className="text-xs font-medium text-foreground mt-0.5">{ev.action}</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">{ev.detail}</p>
                <Badge className={`mt-1.5 text-[9px] px-1.5 py-0 border-0 ${cfg.badgeClass}`}>
                  {cfg.label}
                </Badge>
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
