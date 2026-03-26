"use client"

import { useEffect, useState, useRef } from "react"
import { ConfidenceRing } from "../dashboard/ConfidenceRing"

interface PanelArgument {
  panel: "advocacy" | "stress_test"
  agent_role: string
  argument: string
  confidence_delta: number
  citations: string[]
  timestamp: string
}

interface GalvanizerRound {
  round_number: number
  advocacy_arguments: PanelArgument[]
  stress_test_arguments: PanelArgument[]
  round_confidence: number
  escalated: boolean
}

interface GalvanizerSession {
  session_id: string
  case_id: string
  document_type: string
  status: "in_progress" | "passed" | "failed" | "escalated"
  current_round: number
  max_rounds: number
  confidence_gate: number
  rounds: GalvanizerRound[]
  final_confidence: number
  started_at: string
  completed_at: string | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export function GalvanizerViewer({ caseId }: { caseId: string }) {
  const [session, setSession] = useState<GalvanizerSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedRound, setExpandedRound] = useState<number | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}/galvanizer`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setSession(data)
        setLoading(false)
      } catch (err: any) {
        setError(err.message)
        setLoading(false)
      }
    }

    fetchSession()

    // Poll for updates while in_progress
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}/galvanizer`)
        if (res.ok) {
          const data = await res.json()
          setSession(data)
          if (data.status !== "in_progress") clearInterval(interval)
        }
      } catch {}
    }, 3000)

    return () => clearInterval(interval)
  }, [caseId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [session?.rounds.length])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-muted-foreground">
          Initializing The Galvanizer...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-destructive text-sm">Galvanizer error: {error}</p>
      </div>
    )
  }

  if (!session) return null

  const statusColors: Record<string, string> = {
    in_progress: "text-blue-400",
    passed: "text-green-400",
    failed: "text-red-400",
    escalated: "text-amber-400",
  }

  const statusLabels: Record<string, string> = {
    in_progress: "DELIBERATING",
    passed: "GALVANIZED — APPROVED",
    failed: "BELOW THRESHOLD — NEEDS REVISION",
    escalated: "ESCALATED — HUMAN REVIEW REQUIRED",
  }

  return (
    <div className="rounded-xl border border-border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            The Galvanizer
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Adversarial panel review — {session.document_type}
          </p>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right">
            <p className={`text-sm font-mono font-bold ${statusColors[session.status]}`}>
              {statusLabels[session.status]}
            </p>
            <p className="text-xs text-muted-foreground">
              Round {session.current_round} of {session.max_rounds}
            </p>
          </div>
          <ConfidenceRing
            value={Math.round(session.final_confidence * 100)}
            size={80}
            strokeWidth={6}
            label="Confidence"
          />
        </div>
      </div>

      {/* Confidence Gate Bar */}
      <div className="px-6 py-3 border-b border-border bg-muted/30">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Gate:</span>
          <div className="flex-1 h-2 rounded-full bg-muted relative overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
              style={{
                width: `${Math.min(session.final_confidence * 100, 100)}%`,
                backgroundColor:
                  session.final_confidence >= session.confidence_gate
                    ? "oklch(0.64 0.18 160)"
                    : session.final_confidence >= session.confidence_gate * 0.8
                    ? "oklch(0.76 0.18 65)"
                    : "oklch(0.62 0.23 25)",
              }}
            />
            {/* Gate marker */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-foreground/50"
              style={{ left: `${session.confidence_gate * 100}%` }}
            />
          </div>
          <span className="text-xs font-mono text-muted-foreground">
            {Math.round(session.confidence_gate * 100)}%
          </span>
        </div>
      </div>

      {/* Debate Rounds */}
      <div ref={scrollRef} className="max-h-[500px] overflow-y-auto">
        {session.rounds.map((round) => (
          <div
            key={round.round_number}
            className="border-b border-border last:border-b-0"
          >
            {/* Round Header */}
            <button
              onClick={() =>
                setExpandedRound(
                  expandedRound === round.round_number
                    ? null
                    : round.round_number
                )
              }
              className="w-full flex items-center justify-between px-6 py-3 hover:bg-muted/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-muted-foreground">
                  R{round.round_number}
                </span>
                <span className="text-sm text-foreground">
                  {round.advocacy_arguments.length} advocacy /{" "}
                  {round.stress_test_arguments.length} stress-test
                </span>
                {round.escalated && (
                  <span className="text-xs bg-amber-500/20 text-amber-400 px-2 py-0.5 rounded-full">
                    ESCALATED
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-sm font-mono font-bold ${
                    round.round_confidence >= session.confidence_gate
                      ? "text-green-400"
                      : "text-amber-400"
                  }`}
                >
                  {Math.round(round.round_confidence * 100)}%
                </span>
                <svg
                  className={`w-4 h-4 text-muted-foreground transition-transform ${
                    expandedRound === round.round_number ? "rotate-180" : ""
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </div>
            </button>

            {/* Expanded Round Details */}
            {expandedRound === round.round_number && (
              <div className="px-6 pb-4 grid grid-cols-2 gap-4">
                {/* Advocacy Panel */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-green-400 uppercase tracking-wider">
                    Advocacy Panel
                  </h4>
                  {round.advocacy_arguments.map((arg, i) => (
                    <div
                      key={i}
                      className="rounded-lg bg-green-500/5 border border-green-500/20 p-3"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-green-400">
                          {arg.agent_role}
                        </span>
                        <span className="text-xs font-mono text-green-400/70">
                          +{(arg.confidence_delta * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-foreground/80">
                        {arg.argument}
                      </p>
                      {arg.citations.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {arg.citations.map((cite, j) => (
                            <span
                              key={j}
                              className="text-[10px] bg-green-500/10 text-green-400/80 px-1.5 py-0.5 rounded"
                            >
                              {cite}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Stress-Test Panel */}
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider">
                    Stress-Test Panel
                  </h4>
                  {round.stress_test_arguments.map((arg, i) => (
                    <div
                      key={i}
                      className="rounded-lg bg-red-500/5 border border-red-500/20 p-3"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-red-400">
                          {arg.agent_role}
                        </span>
                        <span className="text-xs font-mono text-red-400/70">
                          {(arg.confidence_delta * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-foreground/80">
                        {arg.argument}
                      </p>
                      {arg.citations.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {arg.citations.map((cite, j) => (
                            <span
                              key={j}
                              className="text-[10px] bg-red-500/10 text-red-400/80 px-1.5 py-0.5 rounded"
                            >
                              {cite}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Live indicator */}
        {session.status === "in_progress" && (
          <div className="px-6 py-4 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-xs text-muted-foreground">
              Panels deliberating...
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
