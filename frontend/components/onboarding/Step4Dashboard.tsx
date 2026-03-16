"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"

const TASKS = [
  { id: 1, label: "Review complaint for jurisdiction issues", priority: "High", status: "pending" },
  { id: 2, label: "Draft answer to complaint", priority: "High", status: "pending" },
  { id: 3, label: "Identify affirmative defenses", priority: "Medium", status: "pending" },
  { id: 4, label: "Gather evidence & documentation", priority: "Medium", status: "pending" },
  { id: 5, label: "Research opposing party's legal standing", priority: "Low", status: "pending" },
]

const TIMELINE = [
  { date: "Mar 16", event: "Complaint received", done: true },
  { date: "Mar 26", event: "Response due (21-day rule)", done: false, urgent: true },
  { date: "Apr 15", event: "Initial case conference", done: false },
  { date: "May 10", event: "Discovery deadline", done: false },
]

const PRIORITY_COLOR: Record<string, string> = {
  High: "text-red-400 bg-red-400/10 border-red-400/20",
  Medium: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  Low: "text-primary bg-primary/10 border-primary/20",
}

interface Step4Props {
  onNext: () => void
  onBack: () => void
}

export function Step4Dashboard({ onNext, onBack }: Step4Props) {
  const [tasks, setTasks] = useState(TASKS)
  const [loading, setLoading] = useState(true)
  const [loadStep, setLoadStep] = useState(0)

  const LOAD_LABELS = [
    "Analyzing case details…",
    "Identifying key deadlines…",
    "Mapping legal strategy…",
    "Generating action items…",
    "Dashboard ready",
  ]

  useEffect(() => {
    let step = 0
    const interval = setInterval(() => {
      step++
      setLoadStep(step)
      if (step >= LOAD_LABELS.length - 1) {
        clearInterval(interval)
        setTimeout(() => setLoading(false), 400)
      }
    }, 500)
    return () => clearInterval(interval)
  }, [])

  const toggleTask = (id: number) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: t.status === "done" ? "pending" : "done" } : t))
    )
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-6 py-12">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-2 border-border" />
          <div
            className="absolute inset-0 rounded-full border-2 border-primary border-t-transparent animate-spin"
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-primary" aria-hidden="true">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">{LOAD_LABELS[loadStep]}</p>
          <p className="text-xs text-muted-foreground mt-1">Building your case profile</p>
        </div>
        <div className="flex gap-1.5">
          {LOAD_LABELS.map((_, i) => (
            <div
              key={i}
              className={["w-1.5 h-1.5 rounded-full transition-all duration-300", i <= loadStep ? "bg-primary" : "bg-border"].join(" ")}
            />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Your case dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Auto-generated from your interview</p>
        </div>
        <span className="shrink-0 text-[10px] font-medium px-2.5 py-1 rounded-full bg-primary/15 text-primary border border-primary/25">
          Active case
        </span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "Tasks", value: tasks.length },
          { label: "Days left", value: "10", urgent: true },
          { label: "Documents", value: "0" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl bg-surface-2 border border-border p-3 text-center">
            <p className={["text-xl font-bold", stat.urgent ? "text-red-400" : "text-foreground"].join(" ")}>
              {stat.value}
            </p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Timeline */}
      <div className="rounded-xl bg-surface-1 border border-border p-4">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Key Deadlines</h2>
        <div className="flex flex-col gap-2.5">
          {TIMELINE.map((item, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="flex flex-col items-center pt-0.5">
                <div
                  className={[
                    "w-2 h-2 rounded-full shrink-0",
                    item.done ? "bg-muted-foreground" : item.urgent ? "bg-red-400" : "bg-primary",
                  ].join(" ")}
                />
                {i < TIMELINE.length - 1 && <div className="w-px h-5 bg-border mt-1" />}
              </div>
              <div className="flex-1 flex justify-between items-start gap-2 pb-2">
                <p className={["text-sm", item.done ? "line-through text-muted-foreground" : "text-foreground"].join(" ")}>
                  {item.event}
                </p>
                <span
                  className={[
                    "text-[10px] font-medium shrink-0",
                    item.done ? "text-muted-foreground" : item.urgent ? "text-red-400" : "text-muted-foreground",
                  ].join(" ")}
                >
                  {item.date}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Task list */}
      <div className="rounded-xl bg-surface-1 border border-border p-4">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Action Items</h2>
        <ul className="flex flex-col gap-2">
          {tasks.map((task) => (
            <li
              key={task.id}
              className="flex items-center gap-3 rounded-lg hover:bg-surface-2 p-1.5 -mx-1.5 transition-colors cursor-pointer group"
              onClick={() => toggleTask(task.id)}
            >
              <button
                className={[
                  "w-4 h-4 rounded shrink-0 border flex items-center justify-center transition-all",
                  task.status === "done"
                    ? "bg-primary border-primary"
                    : "border-border group-hover:border-primary/50",
                ].join(" ")}
                aria-label={task.status === "done" ? "Mark as pending" : "Mark as done"}
              >
                {task.status === "done" && (
                  <svg width="9" height="9" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                    <path d="M2 5l2 2 4-4" stroke="black" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
              <span className={["text-sm flex-1 leading-snug", task.status === "done" ? "line-through text-muted-foreground" : "text-foreground"].join(" ")}>
                {task.label}
              </span>
              <span className={["text-[10px] font-medium px-1.5 py-0.5 rounded border shrink-0", PRIORITY_COLOR[task.priority]].join(" ")}>
                {task.priority}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex gap-3">
        <Button
          variant="outline"
          className="flex-1 h-11 border-border bg-surface-2 hover:bg-surface-3 text-foreground"
          onClick={onBack}
        >
          Back
        </Button>
        <Button
          className="flex-1 h-11 bg-primary text-primary-foreground hover:bg-primary/90 font-medium"
          onClick={onNext}
        >
          See my deliverable
        </Button>
      </div>
    </div>
  )
}
