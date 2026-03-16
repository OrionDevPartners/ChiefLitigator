export type DeadlineType =
  | "Answer"
  | "Response to Motion"
  | "Appeal"
  | "Discovery Cutoff"
  | "Expert Disclosure"
  | "Pretrial Conference"
  | "Trial"
  | "Statute of Limitations"
  | "Mediation"
  | "Deposition"
  | "Objection"
  | "Reply Brief"
  | "Other"

export type Jurisdiction =
  | "SDNY"
  | "NDCA"
  | "D. Del."
  | "D. Mass."
  | "N.D. Ill."
  | "S.D. Tex."
  | "C.D. Cal."
  | "D.N.J."
  | "E.D. Va."
  | "D. Md."
  | "CA Supreme Court"
  | "CA 2nd Circuit"
  | "9th Circuit"
  | "11th Circuit"
  | "Federal Circuit"
  | "Other"

export type ServiceMethod =
  | "Electronic Filing (ECF)"
  | "Personal Service"
  | "Mail (+3 days)"
  | "Email (+0 days)"
  | "Overnight Courier"
  | "Other"

export type UrgencyLevel = "critical" | "high" | "medium" | "low"

export interface Deadline {
  id: string
  title: string
  type: DeadlineType
  jurisdiction: Jurisdiction
  ruleCitation: string
  eventDate: Date
  serviceMethod: ServiceMethod
  notes?: string
  caseNumber?: string
  caseName?: string
}

export interface NewDeadlineInput {
  title: string
  type: DeadlineType
  jurisdiction: Jurisdiction
  ruleCitation: string
  eventDate: Date
  serviceMethod: ServiceMethod
  notes?: string
  caseNumber?: string
  caseName?: string
}

export function getDaysRemaining(eventDate: Date): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(eventDate)
  target.setHours(0, 0, 0, 0)
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

export function getUrgencyLevel(daysRemaining: number): UrgencyLevel {
  if (daysRemaining <= 3) return "critical"
  if (daysRemaining <= 7) return "high"
  if (daysRemaining <= 14) return "medium"
  return "low"
}

export function getUrgencyConfig(level: UrgencyLevel) {
  switch (level) {
    case "critical":
      return {
        label: "Critical",
        bgClass: "bg-red-500/15",
        textClass: "text-red-400",
        borderClass: "border-red-500/30",
        dotClass: "bg-red-400",
        barClass: "bg-red-500",
      }
    case "high":
      return {
        label: "Urgent",
        bgClass: "bg-amber-500/15",
        textClass: "text-amber-400",
        borderClass: "border-amber-500/30",
        dotClass: "bg-amber-400",
        barClass: "bg-amber-500",
      }
    case "medium":
      return {
        label: "Due Soon",
        bgClass: "bg-sky-500/15",
        textClass: "text-sky-400",
        borderClass: "border-sky-500/30",
        dotClass: "bg-sky-400",
        barClass: "bg-sky-500",
      }
    case "low":
      return {
        label: "On Track",
        bgClass: "bg-emerald-500/15",
        textClass: "text-emerald-400",
        borderClass: "border-emerald-500/30",
        dotClass: "bg-emerald-400",
        barClass: "bg-emerald-500",
      }
  }
}
