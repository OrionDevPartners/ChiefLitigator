"use client"

import { useState } from "react"
import { OnboardingProgress } from "@/components/onboarding/OnboardingProgress"
import { Step1SignUp } from "@/components/onboarding/Step1SignUp"
import { Step2Intent } from "@/components/onboarding/Step2Intent"
import { Step3Interview } from "@/components/onboarding/Step3Interview"
import { Step4Dashboard } from "@/components/onboarding/Step4Dashboard"
import { Step5Deliverable } from "@/components/onboarding/Step5Deliverable"

export default function OnboardingPage() {
  const [step, setStep] = useState(1)

  const next = () => setStep((s) => Math.min(s + 1, 5))
  const back = () => setStep((s) => Math.max(s - 1, 1))

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Progress header */}
      <header className="w-full border-b border-border bg-surface-1/50 backdrop-blur-sm sticky top-0 z-20">
        <OnboardingProgress currentStep={step} />
      </header>

      {/* Step content */}
      <div className="flex-1 flex items-start justify-center px-4 py-8 pb-16">
        <div
          className="w-full"
          style={{ maxWidth: step >= 4 ? 640 : 480 }}
        >
          {step === 1 && <Step1SignUp onNext={next} />}
          {step === 2 && <Step2Intent onNext={next} onBack={back} />}
          {step === 3 && <Step3Interview onNext={next} onBack={back} />}
          {step === 4 && <Step4Dashboard onNext={next} onBack={back} />}
          {step === 5 && <Step5Deliverable onBack={back} />}
        </div>
      </div>
    </main>
  )
}
