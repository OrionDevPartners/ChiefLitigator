/**
 * ChiefLitigator API client — connects frontend to FastAPI backend.
 *
 * All API calls go through this module. No direct fetch() elsewhere.
 * CPAA: API_BASE from env var, never hardcoded.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// ─── Response Types ──────────────────────────────────────────────────────────

interface ChatResponse {
  content: string
  confidence: number
  citations_used: string[]
  flags: string[]
  agent_id: string
  input_tokens: number
  output_tokens: number
  latency_ms: number
  galvanizer_session_id?: string
}

interface CitationResult {
  citation: string
  status: "verified" | "unverified" | "partial" | "error"
  steps_passed: string[]
  steps_failed: string[]
  external_source: string | null
  holding_summary: string | null
  holding_match: boolean | null
  good_law: boolean | null
  confidence: number
  details: string
}

interface DeadlineResult {
  event_date: string
  deadline_date: string
  jurisdiction: string
  deadline_type: string
  service_method: string
  days_allowed: number
  adjustments: string[]
  rule_citation: string
  confidence: string
  warning: string | null
  conservative: boolean
}

interface CaseInfo {
  id: string
  title: string
  case_type: string
  jurisdiction: string
  status: string
  confidence_score: number
  created_at: string
  updated_at: string
  parties: { name: string; role: string }[]
  deadlines: DeadlineResult[]
}

interface DocumentInfo {
  id: string
  case_id: string
  document_type: string
  title: string
  status: "draft" | "galvanizing" | "approved" | "filed"
  confidence_score: number
  galvanizer_session_id?: string
  content_url: string
  created_at: string
}

interface GalvanizerSession {
  session_id: string
  case_id: string
  document_type: string
  status: "in_progress" | "passed" | "failed" | "escalated"
  current_round: number
  max_rounds: number
  confidence_gate: number
  rounds: GalvanizerRound[]
  final_confidence: number
  started_at: string
  completed_at: string | null
}

interface GalvanizerRound {
  round_number: number
  advocacy_arguments: PanelArgument[]
  stress_test_arguments: PanelArgument[]
  round_confidence: number
  escalated: boolean
}

interface PanelArgument {
  panel: "advocacy" | "stress_test"
  agent_role: string
  argument: string
  confidence_delta: number
  citations: string[]
  timestamp: string
}

interface IntakeAnalysis {
  legal_issues: { issue: string; confidence: number; statutes: string[] }[]
  jurisdiction: string
  recommended_actions: string[]
  deadlines: DeadlineResult[]
  document_types_needed: string[]
  estimated_complexity: "simple" | "moderate" | "complex"
}

interface HealthStatus {
  status: string
  agents: number
  tests_passing: number
  version: string
  environment: string
}

interface SystemInfo {
  version: string
  environment: string
  agents_loaded: string[]
  siphon_status: { last_run: string; records_total: number }
  bedrock_models: string[]
}

// ─── API Client ──────────────────────────────────────────────────────────────

async function apiCall<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`
  const token = typeof window !== "undefined" ? localStorage.getItem("cl_token") : null

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      error: `HTTP ${response.status}`,
    }))
    throw new Error(
      error.error || error.detail || `API error: ${response.status}`
    )
  }

  return response.json()
}

export const api = {
  // ─── System ──────────────────────────────────────────────────────────────
  health: () => apiCall<HealthStatus>("/api/v1/system/health"),
  ready: () => apiCall<{ ready: boolean; provider: string }>("/api/v1/system/ready"),
  info: () => apiCall<SystemInfo>("/api/v1/system/info"),

  // ─── Chat (Main Interface) ──────────────────────────────────────────────
  chat: (message: string, caseId?: string, jurisdiction?: string) =>
    apiCall<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message, case_id: caseId, jurisdiction }),
    }),

  streamChat: (message: string, caseId?: string, jurisdiction?: string) =>
    fetch(`${API_BASE}/api/v1/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, case_id: caseId, jurisdiction }),
    }),

  // ─── Intake (Context-to-Law Matching) ───────────────────────────────────
  intake: (narrative: string, jurisdiction?: string) =>
    apiCall<IntakeAnalysis>("/api/v1/chat/intake", {
      method: "POST",
      body: JSON.stringify({ narrative, jurisdiction }),
    }),

  // ─── Cases ──────────────────────────────────────────────────────────────
  cases: {
    list: () => apiCall<CaseInfo[]>("/api/v1/cases"),
    get: (id: string) => apiCall<CaseInfo>(`/api/v1/cases/${id}`),
    create: (data: {
      title: string
      case_type: string
      jurisdiction: string
      narrative: string
    }) =>
      apiCall<CaseInfo>("/api/v1/cases", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<CaseInfo>) =>
      apiCall<CaseInfo>(`/api/v1/cases/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  // ─── Documents ──────────────────────────────────────────────────────────
  documents: {
    list: (caseId: string) =>
      apiCall<DocumentInfo[]>(`/api/v1/documents?case_id=${caseId}`),
    get: (id: string) => apiCall<DocumentInfo>(`/api/v1/documents/${id}`),
    generate: (caseId: string, documentType: string) =>
      apiCall<DocumentInfo>("/api/v1/documents/generate", {
        method: "POST",
        body: JSON.stringify({ case_id: caseId, document_type: documentType }),
      }),
    galvanize: (id: string) =>
      apiCall<GalvanizerSession>(`/api/v1/documents/${id}/galvanize`, {
        method: "POST",
      }),
    download: (id: string) =>
      `${API_BASE}/api/v1/documents/${id}/download`,
  },

  // ─── Galvanizer ─────────────────────────────────────────────────────────
  galvanizer: {
    getSession: (caseId: string) =>
      apiCall<GalvanizerSession>(`/api/v1/cases/${caseId}/galvanizer`),
    getSessionById: (sessionId: string) =>
      apiCall<GalvanizerSession>(`/api/v1/galvanizer/${sessionId}`),
  },

  // ─── Citations ──────────────────────────────────────────────────────────
  verifyCitation: (citation: string, claimedHolding?: string) =>
    apiCall<CitationResult>("/api/v1/verify-citation", {
      method: "POST",
      body: JSON.stringify({
        citation,
        claimed_holding: claimedHolding,
      }),
    }),

  // ─── Deadlines ──────────────────────────────────────────────────────────
  computeDeadline: (
    eventDate: string,
    deadlineType: string,
    jurisdiction: string,
    serviceMethod?: string
  ) =>
    apiCall<DeadlineResult>("/api/v1/compute-deadline", {
      method: "POST",
      body: JSON.stringify({
        event_date: eventDate,
        deadline_type: deadlineType,
        jurisdiction,
        service_method: serviceMethod || "personal",
      }),
    }),
}

export type {
  ChatResponse,
  CitationResult,
  DeadlineResult,
  CaseInfo,
  DocumentInfo,
  GalvanizerSession,
  GalvanizerRound,
  PanelArgument,
  IntakeAnalysis,
  HealthStatus,
  SystemInfo,
}
