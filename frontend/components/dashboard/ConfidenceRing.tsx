"use client"

interface ConfidenceRingProps {
  value: number // 0–100
  size?: number
  strokeWidth?: number
  label?: string
}

export function ConfidenceRing({
  value,
  size = 120,
  strokeWidth = 10,
  label = "Confidence",
}: ConfidenceRingProps) {
  const r = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * r
  const filled = (value / 100) * circumference
  const cx = size / 2
  const cy = size / 2

  // Color based on confidence level
  const color =
    value >= 75
      ? "oklch(0.64 0.18 160)"   // green
      : value >= 55
      ? "oklch(0.6 0.2 250)"     // blue
      : value >= 40
      ? "oklch(0.76 0.18 65)"    // amber
      : "oklch(0.62 0.23 25)"    // red

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="-rotate-90"
          role="img"
          aria-label={`${label}: ${value}%`}
        >
          {/* Track */}
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="oklch(0.22 0 0)"
            strokeWidth={strokeWidth}
          />
          {/* Progress */}
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${filled} ${circumference - filled}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.8s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-bold text-foreground">{value}%</span>
        </div>
      </div>
      <span className="text-xs text-muted-foreground font-medium uppercase tracking-widest">{label}</span>
    </div>
  )
}
