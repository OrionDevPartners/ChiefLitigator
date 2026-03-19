"use client"

import { useState } from "react"
import { Plus, CalendarIcon, Scale, BookOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type {
  NewDeadlineInput,
  DeadlineType,
  Jurisdiction,
  ServiceMethod,
} from "@/lib/deadline-types"

const DEADLINE_TYPES: DeadlineType[] = [
  "Answer",
  "Response to Motion",
  "Appeal",
  "Discovery Cutoff",
  "Expert Disclosure",
  "Pretrial Conference",
  "Trial",
  "Statute of Limitations",
  "Mediation",
  "Deposition",
  "Objection",
  "Reply Brief",
  "Other",
]

const JURISDICTIONS: Jurisdiction[] = [
  "SDNY",
  "NDCA",
  "D. Del.",
  "D. Mass.",
  "N.D. Ill.",
  "S.D. Tex.",
  "C.D. Cal.",
  "D.N.J.",
  "E.D. Va.",
  "D. Md.",
  "CA Supreme Court",
  "CA 2nd Circuit",
  "9th Circuit",
  "11th Circuit",
  "Federal Circuit",
  "Other",
]

const SERVICE_METHODS: ServiceMethod[] = [
  "Electronic Filing (ECF)",
  "Personal Service",
  "Mail (+3 days)",
  "Email (+0 days)",
  "Overnight Courier",
  "Other",
]

interface AddDeadlineDialogProps {
  onAdd: (deadline: NewDeadlineInput) => void
}

const emptyForm = {
  title: "",
  type: "" as DeadlineType,
  jurisdiction: "" as Jurisdiction,
  ruleCitation: "",
  eventDate: "",
  serviceMethod: "" as ServiceMethod,
  notes: "",
  caseNumber: "",
  caseName: "",
}

export function AddDeadlineDialog({ onAdd }: AddDeadlineDialogProps) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [errors, setErrors] = useState<Partial<Record<keyof typeof emptyForm, string>>>({})

  function validate() {
    const newErrors: typeof errors = {}
    if (!form.title.trim()) newErrors.title = "Title is required"
    if (!form.type) newErrors.type = "Type is required"
    if (!form.jurisdiction) newErrors.jurisdiction = "Jurisdiction is required"
    if (!form.ruleCitation.trim()) newErrors.ruleCitation = "Rule citation is required"
    if (!form.eventDate) newErrors.eventDate = "Event date is required"
    if (!form.serviceMethod) newErrors.serviceMethod = "Service method is required"
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleSubmit() {
    if (!validate()) return
    onAdd({
      title: form.title.trim(),
      type: form.type,
      jurisdiction: form.jurisdiction,
      ruleCitation: form.ruleCitation.trim(),
      eventDate: new Date(form.eventDate),
      serviceMethod: form.serviceMethod,
      notes: form.notes.trim() || undefined,
      caseNumber: form.caseNumber.trim() || undefined,
      caseName: form.caseName.trim() || undefined,
    })
    setForm(emptyForm)
    setErrors({})
    setOpen(false)
  }

  function handleOpenChange(val: boolean) {
    setOpen(val)
    if (!val) {
      setForm(emptyForm)
      setErrors({})
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90 font-medium">
          <Plus className="h-4 w-4" />
          Add Deadline
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] bg-card border-border text-foreground">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-foreground text-lg">
            <Scale className="h-5 w-5 text-primary" />
            Add New Deadline
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Enter the deadline details. All fields marked with * are required.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          {/* Title */}
          <div className="space-y-1.5">
            <Label htmlFor="title" className="text-sm text-foreground">
              Matter / Description *
            </Label>
            <Input
              id="title"
              placeholder="e.g. Answer to Complaint — Smith v. Acme Corp."
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="bg-input border-border text-foreground placeholder:text-muted-foreground"
            />
            {errors.title && <p className="text-xs text-red-400">{errors.title}</p>}
          </div>

          {/* Case info */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="caseName" className="text-sm text-foreground">
                Case Name
              </Label>
              <Input
                id="caseName"
                placeholder="Smith v. Acme Corp."
                value={form.caseName}
                onChange={(e) => setForm({ ...form, caseName: e.target.value })}
                className="bg-input border-border text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="caseNumber" className="text-sm text-foreground">
                Docket / Case No.
              </Label>
              <Input
                id="caseNumber"
                placeholder="1:24-cv-00001"
                value={form.caseNumber}
                onChange={(e) => setForm({ ...form, caseNumber: e.target.value })}
                className="bg-input border-border text-foreground placeholder:text-muted-foreground"
              />
            </div>
          </div>

          {/* Type + Jurisdiction */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-sm text-foreground">Deadline Type *</Label>
              <Select
                value={form.type}
                onValueChange={(v) => setForm({ ...form, type: v as DeadlineType })}
              >
                <SelectTrigger className="bg-input border-border text-foreground data-[placeholder]:text-muted-foreground">
                  <SelectValue placeholder="Select type…" />
                </SelectTrigger>
                <SelectContent className="bg-popover border-border text-foreground">
                  {DEADLINE_TYPES.map((t) => (
                    <SelectItem key={t} value={t} className="hover:bg-accent focus:bg-accent">
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.type && <p className="text-xs text-red-400">{errors.type}</p>}
            </div>
            <div className="space-y-1.5">
              <Label className="text-sm text-foreground">Jurisdiction *</Label>
              <Select
                value={form.jurisdiction}
                onValueChange={(v) => setForm({ ...form, jurisdiction: v as Jurisdiction })}
              >
                <SelectTrigger className="bg-input border-border text-foreground data-[placeholder]:text-muted-foreground">
                  <SelectValue placeholder="Select court…" />
                </SelectTrigger>
                <SelectContent className="bg-popover border-border text-foreground">
                  {JURISDICTIONS.map((j) => (
                    <SelectItem key={j} value={j} className="hover:bg-accent focus:bg-accent">
                      {j}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.jurisdiction && (
                <p className="text-xs text-red-400">{errors.jurisdiction}</p>
              )}
            </div>
          </div>

          {/* Rule citation */}
          <div className="space-y-1.5">
            <Label htmlFor="ruleCitation" className="text-sm text-foreground flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
              Rule Citation *
            </Label>
            <Input
              id="ruleCitation"
              placeholder="e.g. Fed. R. Civ. P. 12(a)(1)(A)"
              value={form.ruleCitation}
              onChange={(e) => setForm({ ...form, ruleCitation: e.target.value })}
              className="bg-input border-border text-foreground placeholder:text-muted-foreground font-mono text-sm"
            />
            {errors.ruleCitation && <p className="text-xs text-red-400">{errors.ruleCitation}</p>}
          </div>

          {/* Date + Service */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="eventDate" className="text-sm text-foreground flex items-center gap-1.5">
                <CalendarIcon className="h-3.5 w-3.5 text-muted-foreground" />
                Deadline Date *
              </Label>
              <Input
                id="eventDate"
                type="date"
                value={form.eventDate}
                onChange={(e) => setForm({ ...form, eventDate: e.target.value })}
                className="bg-input border-border text-foreground [color-scheme:dark]"
              />
              {errors.eventDate && <p className="text-xs text-red-400">{errors.eventDate}</p>}
            </div>
            <div className="space-y-1.5">
              <Label className="text-sm text-foreground">Service Method *</Label>
              <Select
                value={form.serviceMethod}
                onValueChange={(v) => setForm({ ...form, serviceMethod: v as ServiceMethod })}
              >
                <SelectTrigger className="bg-input border-border text-foreground data-[placeholder]:text-muted-foreground">
                  <SelectValue placeholder="Select method…" />
                </SelectTrigger>
                <SelectContent className="bg-popover border-border text-foreground">
                  {SERVICE_METHODS.map((s) => (
                    <SelectItem key={s} value={s} className="hover:bg-accent focus:bg-accent">
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.serviceMethod && (
                <p className="text-xs text-red-400">{errors.serviceMethod}</p>
              )}
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="notes" className="text-sm text-foreground">
              Notes
            </Label>
            <Textarea
              id="notes"
              placeholder="Additional context, reminders, or related filings…"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="bg-input border-border text-foreground placeholder:text-muted-foreground min-h-[72px] resize-none"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="ghost"
            onClick={() => handleOpenChange(false)}
            className="text-muted-foreground hover:text-foreground"
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="bg-primary text-primary-foreground hover:bg-primary/90">
            Add Deadline
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
