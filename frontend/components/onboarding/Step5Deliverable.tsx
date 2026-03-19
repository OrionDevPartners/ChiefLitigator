"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"

const CONTENT = {
  sections: [
    { title: "I. COMES NOW THE DEFENDANT", text: "Defendant, by and through undersigned counsel, hereby submits this Answer to Plaintiff's Complaint and respectfully states:" },
    { title: "II. GENERAL DENIALS", text: "1. Defendant denies each and every allegation in the Complaint not specifically admitted herein.\n\n2. Defendant is without sufficient information to form a belief as to the truth of the allegations in Paragraph 3, and therefore denies same." },
    { title: "III. AFFIRMATIVE DEFENSES", text: "1. STATUTE OF LIMITATIONS: The claims alleged in the Complaint are barred by the applicable statute of limitations under [State] Code § [XXX].\n\n2. FAILURE TO STATE A CLAIM: The Complaint fails to state a claim upon which relief may be granted." },
  ],
}

interface Step5Props {
  onBack: () => void
}

export function Step5Deliverable({ onBack }: Step5Props) {
  const [loading, setLoading] = useState(true)
  const [visibleSections, setVisibleSections] = useState(0)

  useEffect(() => {
    const timer1 = setTimeout(() => setLoading(false), 1800)
    const timer2 = setTimeout(() => setVisibleSections(1), 2000)
    const timer3 = setTimeout(() => setVisibleSections(2), 2400)
    const timer4 = setTimeout(() => setVisibleSections(3), 2800)
    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
      clearTimeout(timer3)
      clearTimeout(timer4)
    }
  }, [])

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
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
          </div>
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">Drafting your Answer to Complaint</p>
          <p className="text-xs text-muted-foreground mt-1">AI is analyzing case law and formatting document</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Your first deliverable is ready</h1>
          <p className="text-sm text-muted-foreground mt-0.5">AI-drafted Answer to Complaint</p>
        </div>
        <span className="shrink-0 text-[10px] font-medium px-2.5 py-1 rounded-full bg-green-400/15 text-green-400 border border-green-400/25">
          Complete
        </span>
      </div>

      {/* Document preview */}
      <div className="rounded-xl bg-surface-1 border border-border overflow-hidden">
        {/* Header */}
        <div className="bg-surface-2 border-b border-border px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-primary" aria-hidden="true">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
            <span className="text-sm font-medium text-foreground">Answer-to-Complaint-Draft.pdf</span>
          </div>
          <span className="text-xs text-muted-foreground">3 pages</span>
        </div>

        {/* Content */}
        <div className="p-6 max-h-80 overflow-y-auto space-y-5 bg-white text-black">
          <div className="text-center border-b border-black/10 pb-4">
            <p className="text-xs font-semibold tracking-wider">UNITED STATES DISTRICT COURT</p>
            <p className="text-xs font-semibold tracking-wider">CENTRAL DISTRICT OF CALIFORNIA</p>
            <div className="mt-4 text-xs leading-relaxed">
              <p>PLAINTIFF NAME,</p>
              <p className="ml-8">Plaintiff,</p>
              <p className="mt-1">v.</p>
              <p className="mt-1">DEFENDANT NAME,</p>
              <p className="ml-8">Defendant.</p>
            </div>
            <p className="text-xs mt-3">Case No. XX:XXXX-XXX</p>
            <p className="text-xs font-semibold mt-1">ANSWER TO COMPLAINT</p>
          </div>

          {CONTENT.sections.slice(0, visibleSections).map((sec, i) => (
            <div key={i} className="animate-in fade-in slide-in-from-bottom-2 duration-500">
              <h2 className="text-xs font-bold tracking-wide mb-2">{sec.title}</h2>
              <p className="text-xs leading-relaxed whitespace-pre-line text-black/80">{sec.text}</p>
            </div>
          ))}

          {visibleSections < CONTENT.sections.length && (
            <div className="flex items-center gap-1.5 text-xs text-black/40">
              <div className="w-1 h-1 rounded-full bg-black/40 animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-1 h-1 rounded-full bg-black/40 animate-bounce" style={{ animationDelay: "150ms" }} />
              <div className="w-1 h-1 rounded-full bg-black/40 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="rounded-xl bg-surface-2 border border-border p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary" aria-hidden="true">
              <polyline points="20,6 9,17 4,12" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">Ready to review and file</p>
            <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">Download, customize, or send for attorney review</p>
          </div>
        </div>
        <Button
          size="sm"
          className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 font-medium w-full sm:w-auto"
        >
          Download PDF
        </Button>
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
          onClick={() => window.location.reload()}
        >
          Go to dashboard
        </Button>
      </div>

      {/* Disclaimer */}
      <p className="text-[10px] text-muted-foreground leading-relaxed text-center px-2">
        This document is AI-generated and for informational purposes only. Review with a licensed attorney before filing.
      </p>
    </div>
  )
}
