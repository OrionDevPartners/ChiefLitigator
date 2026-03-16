"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, CheckCircle2, Circle, Clock, FileSearch, Loader2, Search, Zap } from "lucide-react"

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

const events: AgentEvent[] = [
  {
    id: "e1",
    agent: "ContractAnalyst",
    action: "Clause extraction complete",
    detail: "Identified 14 potentially adverse clauses in Exhibit C",
    time: "2m ago",
    type: "complete",
    duration: "38s",
  },
  {
    id: "e2",
    agent: "PrecedentFinder",
    action: "Searching case law database",
    detail: "Querying SDNY rulings on SaaS breach 2019–2024",
    time: "5m ago",
    type: "running",
    duration: "ongoing",
  },
  {
    id: "e3",
    agent: "RiskScorer",
    action: "Liability exposure updated",
    detail: "Tortious interference risk elevated to 6.8 — new deposition transcript",
    time: "14m ago",
    type: "flagged",
    duration: "12s",
  },
  {
    id: "e4",
    agent: "DocReview",
    action: "Privilege log generated",
    detail: "312 documents flagged for attorney-client privilege review",
    time: "31m ago",
    type: "complete",
    duration: "2m 14s",
  },
  {
    id: "e5",
    agent: "TimelineBuilder",
    action: "Chronology analysis queued",
    detail: "Waiting for deposition transcripts D4-D9 upload",
    time: "1h ago",
    type: "queued",
  },
  {
    id: "e6",
    agent: "DiscoveryBot",
    action: "ESI processing complete",
    detail: "84,200 emails processed — 1,284 responsive documents identified",
    time: "3h ago",
    type: "complete",
    duration: "47m",
  },
]

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

export function AgentActivity() {
  return (
    <Card className="flex flex-col gap-0 border-border bg-card">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm font-semibold text-foreground">Agent Activity</CardTitle>
        </div>
        <Badge variant="secondary" className="text-[10px] font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-[oklch(0.6_0.2_250)] mr-1.5 animate-pulse inline-block" />
          1 running
        </Badge>
      </CardHeader>

      <CardContent className="p-4 pt-0 flex flex-col gap-0">
        {events.map((ev, i) => {
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
