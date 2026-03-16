"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ConfidenceRing } from "./ConfidenceRing"
import { Brain, FileText, Gavel, Scale, TrendingUp } from "lucide-react"

const claims = [
  { label: "Breach of Contract", strength: 82, tag: "Strong" },
  { label: "Negligent Misrepresentation", strength: 64, tag: "Moderate" },
  { label: "Unjust Enrichment", strength: 51, tag: "Moderate" },
  { label: "Tortious Interference", strength: 38, tag: "Weak" },
]

const stats = [
  { icon: FileText, label: "Documents", value: "1,284" },
  { icon: Gavel, label: "Precedents", value: "47" },
  { icon: Brain, label: "AI Insights", value: "23" },
  { icon: TrendingUp, label: "Risk Score", value: "6.2/10" },
]

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

export function CaseSummary() {
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
        <div>
          <h2 className="text-base font-semibold text-foreground text-balance">
            Hartwell Industries v. NovaCorp Technologies
          </h2>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            Commercial litigation — breach of SaaS licensing agreement, alleged misrepresentation of
            platform capabilities, and unjust enrichment. Filed 14 Mar 2024 · U.S.D.C. S.D.N.Y.
          </p>
        </div>

        {/* Confidence ring + mini stats */}
        <div className="flex items-center justify-between gap-4">
          <ConfidenceRing value={74} size={110} strokeWidth={10} label="Win Confidence" />
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
        </div>

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
      </CardContent>
    </Card>
  )
}
