"use client"

import { getDaysRemaining, getUrgencyLevel, getUrgencyConfig } from "@/lib/deadline-types"

interface UrgencyBadgeProps {
  eventDate: Date
  size?: "sm" | "md"
}

export function UrgencyBadge({ eventDate, size = "md" }: UrgencyBadgeProps) {
  const days = getDaysRemaining(eventDate)
  const level = getUrgencyLevel(days)
  const config = getUrgencyConfig(level)

  const label =
    days < 0
      ? `${Math.abs(days)}d overdue`
      : days === 0
        ? "Due today"
        : `${days}d left`

  const sizeClass = size === "sm" ? "text-xs px-2 py-0.5 gap-1" : "text-xs px-2.5 py-1 gap-1.5"

  return (
    <span
      className={`inline-flex items-center rounded-full border font-mono font-medium ${sizeClass} ${config.bgClass} ${config.textClass} ${config.borderClass}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${config.dotClass} ${days < 0 ? "animate-pulse" : ""}`} />
      {label}
    </span>
  )
}
