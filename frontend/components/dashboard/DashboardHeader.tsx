"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Bell, ChevronDown, Scale, Settings, Users } from "lucide-react"

export function DashboardHeader() {
  return (
    <header className="border-b border-border bg-card sticky top-0 z-40">
      <div className="flex items-center justify-between px-6 h-14">
        {/* Left: Logo + breadcrumb */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center">
              <Scale className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-foreground tracking-tight">Cyphergy</span>
          </div>
          <nav className="hidden md:flex items-center gap-1 text-sm text-muted-foreground">
            <span>Cases</span>
            <ChevronDown className="w-3 h-3" />
            <span className="mx-1 text-border">/</span>
            <span className="text-foreground font-medium">Hartwell v. NovaCorp</span>
          </nav>
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="font-mono text-xs hidden sm:flex">
            Case #CVL-2024-0892
          </Badge>
          <Button variant="ghost" size="icon" className="w-8 h-8 relative">
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-urgent-red rounded-full" />
            <span className="sr-only">Notifications</span>
          </Button>
          <Button variant="ghost" size="icon" className="w-8 h-8">
            <Users className="w-4 h-4" />
            <span className="sr-only">Team</span>
          </Button>
          <Button variant="ghost" size="icon" className="w-8 h-8">
            <Settings className="w-4 h-4" />
            <span className="sr-only">Settings</span>
          </Button>
        </div>
      </div>

      {/* Sub-nav */}
      <div className="flex items-center gap-1 px-6 pb-0 text-sm overflow-x-auto">
        {["Overview", "Documents", "Discovery", "Filings", "Billing", "Timeline"].map((item) => (
          <button
            key={item}
            className={`px-3 py-2 border-b-2 whitespace-nowrap transition-colors ${
              item === "Overview"
                ? "border-primary text-foreground font-medium"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {item}
          </button>
        ))}
      </div>
    </header>
  )
}
