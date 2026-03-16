"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DollarSign, TrendingUp } from "lucide-react"

interface CostLine {
  label: string
  category: string
  amount: number
  budget: number
  variance: number
}

const costLines: CostLine[] = [
  { label: "Attorney Fees", category: "Legal", amount: 184200, budget: 220000, variance: -16.3 },
  { label: "Expert Witnesses", category: "Expert", amount: 42800, budget: 50000, variance: -14.4 },
  { label: "E-Discovery (ESI)", category: "Tech", amount: 31450, budget: 28000, variance: 12.3 },
  { label: "Court Filings", category: "Filing", amount: 4890, budget: 6000, variance: -18.5 },
  { label: "Deposition Costs", category: "Discovery", amount: 12300, budget: 15000, variance: -18.0 },
  { label: "AI Platform Usage", category: "Tech", amount: 2840, budget: 4000, variance: -29.0 },
]

const categoryColors: Record<string, string> = {
  Legal: "oklch(0.6_0.2_250)",
  Expert: "oklch(0.76_0.18_65)",
  Tech: "oklch(0.64_0.18_160)",
  Filing: "oklch(0.65_0.15_300)",
  Discovery: "oklch(0.62_0.23_25)",
}

function fmt(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n)
}

export function CostTracker() {
  const totalSpent = costLines.reduce((s, c) => s + c.amount, 0)
  const totalBudget = costLines.reduce((s, c) => s + c.budget, 0)
  const pct = Math.round((totalSpent / totalBudget) * 100)

  return (
    <Card className="flex flex-col gap-0 border-border bg-card">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <DollarSign className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm font-semibold text-foreground">Cost Tracker</CardTitle>
        </div>
        <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
          YTD 2026
        </Badge>
      </CardHeader>

      <CardContent className="p-4 pt-0 flex flex-col gap-4">
        {/* Budget summary */}
        <div className="rounded-md border border-border bg-secondary/30 p-3 flex items-center justify-between gap-4">
          <div>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Total Spent</p>
            <p className="font-mono text-xl font-bold text-foreground">{fmt(totalSpent)}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              of {fmt(totalBudget)} budget · {pct}% utilized
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-1 text-[oklch(0.64_0.18_160)] text-xs font-medium">
              <TrendingUp className="w-3.5 h-3.5" />
              {100 - pct}% remaining
            </div>
            <div className="w-28 bg-muted rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full bg-[oklch(0.6_0.2_250)] transition-all duration-700"
                style={{ width: `${pct}%` }}
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Budget utilized: ${pct}%`}
              />
            </div>
          </div>
        </div>

        {/* Cost breakdown table */}
        <div className="flex flex-col gap-1">
          <div className="grid grid-cols-[1fr_auto_auto_auto] text-[10px] text-muted-foreground uppercase tracking-wider pb-1 border-b border-border px-1">
            <span>Line Item</span>
            <span className="text-right pr-3">Spent</span>
            <span className="text-right pr-3">Budget</span>
            <span className="text-right">Var</span>
          </div>
          {costLines.map((c) => {
            const color = categoryColors[c.category] ?? "oklch(0.55 0 0)"
            const overBudget = c.variance > 0
            return (
              <div
                key={c.label}
                className="grid grid-cols-[1fr_auto_auto_auto] items-center py-1.5 px-1 rounded hover:bg-muted/40 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-2 h-2 rounded-sm shrink-0"
                    style={{ backgroundColor: `oklch(${color.slice(7, -1)})` }}
                  />
                  <div className="min-w-0">
                    <p className="text-xs text-foreground truncate">{c.label}</p>
                    <p className="text-[10px] text-muted-foreground">{c.category}</p>
                  </div>
                </div>
                <span className="font-mono text-xs text-foreground text-right pr-3">
                  {fmt(c.amount)}
                </span>
                <span className="font-mono text-[10px] text-muted-foreground text-right pr-3">
                  {fmt(c.budget)}
                </span>
                <span
                  className={`font-mono text-[10px] text-right font-medium ${
                    overBudget
                      ? "text-[oklch(0.62_0.23_25)]"
                      : "text-[oklch(0.64_0.18_160)]"
                  }`}
                >
                  {overBudget ? "+" : ""}{c.variance}%
                </span>
              </div>
            )
          })}
        </div>

        {/* Stacked bar */}
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
            Spend by Category
          </p>
          <div className="flex h-2 rounded-full overflow-hidden w-full gap-px">
            {costLines.map((c) => {
              const color = categoryColors[c.category] ?? "oklch(0.55 0 0)"
              const w = ((c.amount / totalSpent) * 100).toFixed(1)
              return (
                <div
                  key={c.label}
                  title={`${c.label}: ${fmt(c.amount)}`}
                  style={{
                    width: `${w}%`,
                    backgroundColor: `oklch(${color.slice(7, -1)})`,
                  }}
                />
              )
            })}
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
            {costLines.map((c) => {
              const color = categoryColors[c.category] ?? "oklch(0.55 0 0)"
              return (
                <span key={c.label} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                  <span
                    className="w-1.5 h-1.5 rounded-sm"
                    style={{ backgroundColor: `oklch(${color.slice(7, -1)})` }}
                  />
                  {c.label}
                </span>
              )
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
