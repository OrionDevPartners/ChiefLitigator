"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  AlertCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Copy,
  RefreshCw,
  Scale,
  BookOpen,
  Calendar,
  Landmark,
  FileText,
  ThumbsUp,
  ThumbsDown,
  Minus,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// ─── Types ────────────────────────────────────────────────────────────────────

export type VerificationStatus = "verified" | "verify" | "unverified";

export type GoodLawStatus = "good" | "questioned" | "overruled" | "unknown";

export type CitingOpinion = {
  id: string;
  caseName: string;
  citation: string;
  year: number;
  treatment: "followed" | "distinguished" | "overruled" | "questioned" | "cited";
};

export type CitationData = {
  /** Bluebook-formatted citation string, e.g. "347 U.S. 483 (1954)" */
  bluebookCitation: string;
  caseName: string;
  court: string;
  year: number;
  holdingSummary: string;
  verificationStatus: VerificationStatus;
  verifiedAt?: string;
  goodLawStatus: GoodLawStatus;
  citingOpinions: CitingOpinion[];
};

export type CitationViewerProps = {
  citation?: CitationData;
  onVerifyAgain?: (citation: CitationData) => void | Promise<void>;
  className?: string;
};

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  VerificationStatus,
  {
    label: string;
    icon: React.ElementType;
    badgeClass: string;
    borderClass: string;
    dotClass: string;
  }
> = {
  verified: {
    label: "VERIFIED",
    icon: CheckCircle2,
    badgeClass:
      "bg-status-verified-bg text-status-verified border border-status-verified/30",
    borderClass: "border-status-verified/40",
    dotClass: "bg-status-verified",
  },
  verify: {
    label: "VERIFY",
    icon: AlertCircle,
    badgeClass:
      "bg-status-verify-bg text-status-verify border border-status-verify/30",
    borderClass: "border-status-verify/40",
    dotClass: "bg-status-verify",
  },
  unverified: {
    label: "UNVERIFIED",
    icon: XCircle,
    badgeClass:
      "bg-status-unverified-bg text-status-unverified border border-status-unverified/30",
    borderClass: "border-status-unverified/40",
    dotClass: "bg-status-unverified",
  },
};

const GOOD_LAW_CONFIG: Record<
  GoodLawStatus,
  { label: string; icon: React.ElementType; colorClass: string }
> = {
  good: {
    label: "Good Law",
    icon: ThumbsUp,
    colorClass: "text-status-verified",
  },
  questioned: {
    label: "Questioned",
    icon: Minus,
    colorClass: "text-status-verify",
  },
  overruled: {
    label: "Overruled",
    icon: ThumbsDown,
    colorClass: "text-status-unverified",
  },
  unknown: {
    label: "Status Unknown",
    icon: Minus,
    colorClass: "text-muted-foreground",
  },
};

const TREATMENT_CONFIG: Record<
  CitingOpinion["treatment"],
  { label: string; colorClass: string }
> = {
  followed: { label: "Followed", colorClass: "text-status-verified" },
  distinguished: { label: "Distinguished", colorClass: "text-status-verify" },
  overruled: { label: "Overruled", colorClass: "text-status-unverified" },
  questioned: { label: "Questioned", colorClass: "text-status-verify" },
  cited: { label: "Cited", colorClass: "text-muted-foreground" },
};

// ─── Sub-components ───────────────────────────────────────────────────────────

function MetaRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded bg-muted">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          {label}
        </span>
        <span className="text-sm font-medium text-foreground">{value}</span>
      </div>
    </div>
  );
}

function CitingOpinionRow({ opinion }: { opinion: CitingOpinion }) {
  const treatment = TREATMENT_CONFIG[opinion.treatment];
  return (
    <div className="group flex items-start justify-between gap-4 rounded-md px-3 py-2.5 transition-colors hover:bg-muted/60">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate text-sm font-medium text-foreground">
          {opinion.caseName}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {opinion.citation}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="text-xs text-muted-foreground">{opinion.year}</span>
        <span
          className={cn(
            "min-w-[80px] text-right text-xs font-semibold uppercase tracking-wide",
            treatment.colorClass
          )}
        >
          {treatment.label}
        </span>
        <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      </div>
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
        <Scale className="h-7 w-7 text-muted-foreground" />
      </div>
      <div className="flex flex-col gap-1.5">
        <p className="text-sm font-semibold text-foreground">
          No citation loaded
        </p>
        <p className="max-w-xs text-xs leading-relaxed text-muted-foreground">
          Pass a{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground">
            citation
          </code>{" "}
          prop to display case details, verification status, and citing
          opinions.
        </p>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function CitationViewer({
  citation,
  onVerifyAgain,
  className,
}: CitationViewerProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [verifying, setVerifying] = useState(false);

  const statusConfig = citation
    ? STATUS_CONFIG[citation.verificationStatus]
    : null;

  const goodLawConfig = citation
    ? GOOD_LAW_CONFIG[citation.goodLawStatus]
    : null;

  async function handleCopy() {
    if (!citation) return;
    try {
      await navigator.clipboard.writeText(citation.bluebookCitation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available in all environments
    }
  }

  async function handleVerifyAgain() {
    if (!citation || !onVerifyAgain) return;
    setVerifying(true);
    try {
      await onVerifyAgain(citation);
    } finally {
      setVerifying(false);
    }
  }

  return (
    <div
      className={cn(
        "w-full overflow-hidden rounded-xl border bg-card font-sans shadow-lg transition-all duration-200",
        statusConfig ? statusConfig.borderClass : "border-border",
        className
      )}
    >
      {/* ── Header / collapsed row ── */}
      <button
        type="button"
        onClick={() => citation && setExpanded((v) => !v)}
        disabled={!citation}
        aria-expanded={expanded}
        className={cn(
          "flex w-full items-center gap-3 px-5 py-4 text-left transition-colors",
          citation
            ? "cursor-pointer hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            : "cursor-default"
        )}
      >
        {/* Left — citation text + case name */}
        <div className="min-w-0 flex-1">
          {citation ? (
            <div className="flex flex-col gap-0.5">
              <span className="font-mono text-xs font-medium tracking-wide text-muted-foreground">
                {citation.bluebookCitation}
              </span>
              <span className="truncate text-sm font-semibold text-foreground text-balance">
                {citation.caseName}
              </span>
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">
              No citation loaded
            </span>
          )}
        </div>

        {/* Right — badge + chevron */}
        <div className="flex shrink-0 items-center gap-2">
          {statusConfig && (
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest",
                statusConfig.badgeClass
              )}
            >
              <statusConfig.icon className="h-3 w-3" />
              {statusConfig.label}
            </span>
          )}
          {citation && (
            <div
              className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground"
              aria-hidden="true"
            >
              {expanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </div>
          )}
        </div>
      </button>

      {/* ── Expanded panel ── */}
      {!citation ? (
        <EmptyState />
      ) : expanded ? (
        <div
          className="border-t border-border"
          role="region"
          aria-label="Citation details"
        >
          {/* Meta grid */}
          <div className="grid grid-cols-1 gap-5 px-5 py-5 sm:grid-cols-2 lg:grid-cols-4">
            <MetaRow icon={BookOpen} label="Case Name" value={citation.caseName} />
            <MetaRow icon={Landmark} label="Court" value={citation.court} />
            <MetaRow
              icon={Calendar}
              label="Year"
              value={String(citation.year)}
            />
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded bg-muted">
                {goodLawConfig && (
                  <goodLawConfig.icon
                    className={cn("h-3.5 w-3.5", goodLawConfig.colorClass)}
                  />
                )}
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Good Law
                </span>
                <span
                  className={cn(
                    "text-sm font-semibold",
                    goodLawConfig?.colorClass
                  )}
                >
                  {goodLawConfig?.label}
                </span>
              </div>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Holding summary */}
          <div className="px-5 py-5">
            <div className="mb-2 flex items-center gap-2">
              <FileText className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                Holding Summary
              </span>
            </div>
            <p className="text-sm leading-relaxed text-foreground">
              {citation.holdingSummary}
            </p>
          </div>

          {/* Verified timestamp */}
          {citation.verifiedAt && (
            <>
              <Separator className="bg-border" />
              <div className="flex items-center gap-2 px-5 py-3">
                <div
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    statusConfig?.dotClass
                  )}
                />
                <span className="text-xs text-muted-foreground">
                  Last verified{" "}
                  <time dateTime={citation.verifiedAt} className="font-medium text-foreground">
                    {citation.verifiedAt}
                  </time>
                </span>
              </div>
            </>
          )}

          {/* Citing opinions */}
          {citation.citingOpinions.length > 0 && (
            <>
              <Separator className="bg-border" />
              <div className="px-5 py-4">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Scale className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                      Citing Opinions
                    </span>
                  </div>
                  <Badge
                    variant="secondary"
                    className="h-5 min-w-[24px] justify-center px-1.5 font-mono text-[10px]"
                  >
                    {citation.citingOpinions.length}
                  </Badge>
                </div>
                <div className="flex flex-col gap-0.5">
                  {citation.citingOpinions.map((op) => (
                    <CitingOpinionRow key={op.id} opinion={op} />
                  ))}
                </div>
              </div>
            </>
          )}

          {citation.citingOpinions.length === 0 && (
            <>
              <Separator className="bg-border" />
              <div className="px-5 py-4">
                <div className="mb-3 flex items-center gap-2">
                  <Scale className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
                    Citing Opinions
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  No citing opinions on record.
                </p>
              </div>
            </>
          )}

          {/* Action bar */}
          <Separator className="bg-border" />
          <div className="flex flex-wrap items-center justify-end gap-2 px-5 py-3">
            {onVerifyAgain && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleVerifyAgain}
                disabled={verifying}
                className="h-8 gap-2 border-border bg-transparent text-xs font-medium hover:bg-muted"
              >
                <RefreshCw
                  className={cn("h-3.5 w-3.5", verifying && "animate-spin")}
                />
                {verifying ? "Verifying…" : "Verify Again"}
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="h-8 gap-2 border-border bg-transparent text-xs font-medium hover:bg-muted"
            >
              <Copy className="h-3.5 w-3.5" />
              {copied ? "Copied!" : "Copy Bluebook Citation"}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
