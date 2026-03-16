"use client"

const STEPS = [
  { num: 1, label: "Account" },
  { num: 2, label: "Your Need" },
  { num: 3, label: "Interview" },
  { num: 4, label: "Dashboard" },
  { num: 5, label: "Deliverable" },
]

interface OnboardingProgressProps {
  currentStep: number
}

export function OnboardingProgress({ currentStep }: OnboardingProgressProps) {
  const progressPct = ((currentStep - 1) / (STEPS.length - 1)) * 100

  return (
    <div className="w-full px-4 pt-6 pb-4">
      {/* Brand wordmark */}
      <div className="flex items-center justify-center mb-8">
        <span className="text-xl font-semibold tracking-tight text-foreground">
          Cypher<span className="text-primary">gy</span>
        </span>
      </div>

      {/* Step indicators */}
      <div className="relative flex items-center justify-between max-w-lg mx-auto">
        {/* Track */}
        <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-px bg-border" />

        {/* Filled track */}
        <div
          className="absolute left-0 top-1/2 -translate-y-1/2 h-px bg-primary transition-all duration-500 ease-out"
          style={{ width: `${progressPct}%` }}
        />

        {STEPS.map((step) => {
          const isDone = step.num < currentStep
          const isActive = step.num === currentStep

          return (
            <div key={step.num} className="relative flex flex-col items-center gap-2 z-10">
              <div
                className={[
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300",
                  isDone
                    ? "bg-primary text-primary-foreground"
                    : isActive
                    ? "bg-primary text-primary-foreground ring-4 ring-primary/20"
                    : "bg-surface-2 border border-border text-muted-foreground",
                ].join(" ")}
              >
                {isDone ? (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  step.num
                )}
              </div>
              <span
                className={[
                  "text-[10px] font-medium hidden sm:block",
                  isActive ? "text-primary" : isDone ? "text-muted-foreground" : "text-muted-foreground/50",
                ].join(" ")}
              >
                {step.label}
              </span>
            </div>
          )
        })}
      </div>

      {/* Mobile step label */}
      <p className="text-center text-xs text-muted-foreground mt-3 sm:hidden">
        Step {currentStep} of {STEPS.length} — {STEPS[currentStep - 1].label}
      </p>
    </div>
  )
}
