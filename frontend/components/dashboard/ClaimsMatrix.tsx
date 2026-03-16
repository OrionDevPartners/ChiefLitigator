"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Grid3X3 } from "lucide-react"

type Status = "Strong" | "Moderate" | "Weak" | "Unresolved" | "Supported"

interface MatrixRow {
  claim: string
  elements: { label: string; status: Status }[]
}

/** Data loaded from case context via props. No hardcoded data. */

const statusStyles: Record<Status, { cell: string; text: string }> = {
  Strong: {
    cell: "bg-[oklch(0.64_0.18_160/0.18)] border-[oklch(0.64_0.18_160/0.35)]",
    text: "text-[oklch(0.64_0.18_160)]",
  },
  Supported: {
    cell: "bg-[oklch(0.6_0.2_250/0.18)] border-[oklch(0.6_0.2_250/0.35)]",
    text: "text-[oklch(0.6_0.2_250)]",
  },
  Moderate: {
    cell: "bg-[oklch(0.76_0.18_65/0.15)] border-[oklch(0.76_0.18_65/0.3)]",
    text: "text-[oklch(0.76_0.18_65)]",
  },
  Weak: {
    cell: "bg-[oklch(0.62_0.23_25/0.15)] border-[oklch(0.62_0.23_25/0.3)]",
    text: "text-[oklch(0.62_0.23_25)]",
  },
  Unresolved: {
    cell: "bg-muted/50 border-border",
    text: "text-muted-foreground",
  },
}

const statusDot: Record<Status, string> = {
  Strong: "bg-[oklch(0.64_0.18_160)]",
  Supported: "bg-[oklch(0.6_0.2_250)]",
  Moderate: "bg-[oklch(0.76_0.18_65)]",
  Weak: "bg-[oklch(0.62_0.23_25)]",
  Unresolved: "bg-muted-foreground/40",
}

export function ClaimsMatrix({ matrix = [] }: { matrix?: MatrixRow[] }) {
  return (
    <Card className="flex flex-col gap-0 border-border bg-card">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Grid3X3 className="w-4 h-4 text-primary" />
          <CardTitle className="text-sm font-semibold text-foreground">Claims Matrix</CardTitle>
        </div>
        {matrix.length > 0 && (
          <div className="flex items-center gap-2">
            {(["Strong", "Moderate", "Weak", "Unresolved"] as Status[]).map((s) => (
              <span key={s} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <span className={`w-1.5 h-1.5 rounded-full ${statusDot[s]}`} />
                {s}
              </span>
            ))}
          </div>
        )}
      </CardHeader>

      <CardContent className="p-4 pt-0 overflow-x-auto">
        {matrix.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
            <Grid3X3 className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">No claims tracked</p>
          </div>
        ) : (
          <>
            <table className="w-full text-xs border-separate border-spacing-y-1" role="table">
              <thead>
                <tr>
                  <th className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider pb-2 pr-3 w-36">
                    Claim
                  </th>
                  {matrix[0].elements.map((e) => (
                    <th
                      key={e.label}
                      className="text-center text-[10px] font-medium text-muted-foreground uppercase tracking-wider pb-2 px-1"
                    >
                      {e.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map((row) => (
                  <tr key={row.claim}>
                    <td className="pr-3 py-0.5">
                      <span className="text-[11px] text-foreground font-medium whitespace-nowrap">
                        {row.claim}
                      </span>
                    </td>
                    {row.elements.map((el) => {
                      const styles = statusStyles[el.status]
                      return (
                        <td key={el.label} className="px-1 py-0.5">
                          <div
                            className={`rounded border px-2 py-1.5 text-center ${styles.cell}`}
                            title={el.status}
                          >
                            <span className={`text-[10px] font-medium leading-none ${styles.text}`}>
                              {el.status}
                            </span>
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Legend badges */}
            <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-border">
              {(Object.entries(statusStyles) as [Status, { cell: string; text: string }][]).map(
                ([status, styles]) => (
                  <Badge
                    key={status}
                    className={`text-[10px] border px-2 py-0.5 ${styles.cell} ${styles.text}`}
                  >
                    {status}
                  </Badge>
                )
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
