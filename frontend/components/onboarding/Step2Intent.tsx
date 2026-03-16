"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"

const INTENTS = [
  {
    id: "received",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14,2 14,8 20,8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10,9 9,9 8,9" />
      </svg>
    ),
    title: "I received a lawsuit",
    description: "Analyze complaint, map deadlines, draft your response",
    tag: "Most common",
  },
  {
    id: "file",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="16" />
        <line x1="8" y1="12" x2="16" y2="12" />
      </svg>
    ),
    title: "I need to file a lawsuit",
    description: "Assess your claim, identify jurisdiction, draft filing",
    tag: null,
  },
  {
    id: "documents",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    title: "I need document help",
    description: "Review, redline, or draft contracts and legal documents",
    tag: null,
  },
  {
    id: "ongoing",
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <polyline points="22,12 18,12 15,21 9,3 6,12 2,12" />
      </svg>
    ),
    title: "I have an ongoing case",
    description: "Track progress, prep for hearings, organize evidence",
    tag: null,
  },
]

interface Step2Props {
  onNext: () => void
  onBack: () => void
}

export function Step2Intent({ onNext, onBack }: Step2Props) {
  const [selected, setSelected] = useState<string | null>(null)

  return (
    <div className="flex flex-col gap-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-foreground text-balance">What do you need help with?</h1>
        <p className="text-sm text-muted-foreground mt-1.5">Select the option that best describes your situation.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {INTENTS.map((intent) => (
          <button
            key={intent.id}
            onClick={() => setSelected(intent.id)}
            className={[
              "relative text-left rounded-xl border p-5 flex flex-col gap-3 transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              selected === intent.id
                ? "border-primary bg-[var(--brand-cyan-dim)] ring-1 ring-primary"
                : "border-border bg-surface-1 hover:border-border/80 hover:bg-surface-2",
            ].join(" ")}
            aria-pressed={selected === intent.id}
          >
            {intent.tag && (
              <span className="absolute top-3 right-3 text-[10px] font-medium px-2 py-0.5 rounded-full bg-primary/20 text-primary border border-primary/30">
                {intent.tag}
              </span>
            )}
            <span className={selected === intent.id ? "text-primary" : "text-muted-foreground"}>
              {intent.icon}
            </span>
            <div>
              <p className="text-sm font-medium text-foreground">{intent.title}</p>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{intent.description}</p>
            </div>
            {selected === intent.id && (
              <span className="absolute bottom-3 right-3 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                  <path d="M2 5l2 2 4-4" stroke="black" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="flex gap-3 mt-2">
        <Button
          variant="outline"
          className="flex-1 h-11 border-border bg-surface-2 hover:bg-surface-3 text-foreground"
          onClick={onBack}
        >
          Back
        </Button>
        <Button
          className="flex-1 h-11 bg-primary text-primary-foreground hover:bg-primary/90 font-medium"
          disabled={!selected}
          onClick={onNext}
        >
          Continue
        </Button>
      </div>
    </div>
  )
}
