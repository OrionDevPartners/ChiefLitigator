"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ConfidenceRing } from "./ConfidenceRing"
import { Brain, FileText, Gavel, Scale, TrendingUp } from "lucide-react"

/** Data loaded from case context via props. No hardcoded data. */

interface Claim {
  label: string
  strength: number
  tag: string
}

interface Stat {
  icon: React.ElementType
  label: string
  value: string
}

interface CaseSummaryProps {
  caseName?: string
  caseDescription?: string
  confidence?: number
  claims?: Claim[]
  stats?: Stat[]
}

function StrengthBar({ value }: { value: number }) {
  const color =
    value >= 75 ? "bg-[oklch(0.64_0.18_160)]" :
    value >= 55 ? "bg-[oklch(0.6_0.2_250)]" :
    value >= 40 ? "bg-[oklch(0.76_0.18_65)]" :
    "bg-[oklch(0.62_0.23_25)]"

  return (
    <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${value}%` }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  )
}

export function CaseSummary({
  caseName,
  caseDescription,
  confidence,
  claims = [],
  stats = [],
}: CaseSummaryProps) {
  const hasCase = caseName || caseDescription || confidence !== undefined || claims.length > 0 || stats.length > 0

  if (!hasCase) {
    return (
      <Card className="flex flex-col gap-0 border-border bg-card">
        <CardHeader className="pb-3 flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-primary" />
            <CardTitle className="text-sm font-semibold text-foreground">Case Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
            <Scale className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">No case loaded</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="flex flex-col gap-0 border-border bg-card">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm font-semibold text-foreground">Case Summary</CardTitle>
        </div>
        <Badge variant="outline" className="text-xs font-mono text-primary border-primary/30">
          Active
        </Badge>
      </CardHeader>

      <CardContent className="flex flex-col gap-5">
        {/* Case meta */}
        {(caseName || caseDescription) && (
          <div>
            {caseName && (
              <h2 className="text-base font-semibold text-foreground text-balance">
                {caseName}
              </h2>
            )}
            {caseDescription && (
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {caseDescription}
              </p>
            )}
          </div>
        )}

        {/* Confidence ring + mini stats */}
        {(confidence !== undefined || stats.length > 0) && (
          <div className="flex items-center justify-between gap-4">
            {confidence !== undefined && (
              <ConfidenceRing value={confidence} size={110} strokeWidth={10} label="Win Confidence" />
            )}
            {stats.length > 0 && (
              <div className="flex-1 grid grid-cols-2 gap-x-3 gap-y-3">
                {stats.map(({ icon: Icon, label, value }) => (
                  <div key={label} className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-1.5">
                      <Icon className="w-3 h-3 text-muted-foreground" />
                      <span className="text-[11px] text-muted-foreground">{label}</span>
                    </div>
                    <span className="font-mono text-sm font-semibold text-foreground">{value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {claims.length > 0 && (
          <>
            <Separator className="bg-border" />

            {/* Claims strength */}
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                Claim Strength
              </p>
              <div className="flex flex-col gap-3">
                {claims.map((c) => (
                  <div key={c.label} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-foreground">{c.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-muted-foreground">{c.strength}%</span>
                        <Badge
                          variant="secondary"
                          className={`text-[10px] px-1.5 py-0 ${
                            c.tag === "Strong"
                              ? "bg-[oklch(0.64_0.18_160/0.15)] text-[oklch(0.64_0.18_160)] border-0"
                              : c.tag === "Moderate"
                              ? "bg-[oklch(0.6_0.2_250/0.15)] text-[oklch(0.6_0.2_250)] border-0"
                              : "bg-[oklch(0.62_0.23_25/0.15)] text-[oklch(0.62_0.23_25)] border-0"
                          }`}
                        >
                          {c.tag}
                        </Badge>
                      </div>
                    </div>
                    <StrengthBar value={c.strength} />
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
