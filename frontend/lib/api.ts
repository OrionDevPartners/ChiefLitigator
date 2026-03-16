/**
 * Cyphergy API client — connects frontend to FastAPI backend.
 *
 * All API calls go through this module. No direct fetch() elsewhere.
 * CPAA: API_BASE from env var, never hardcoded.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ChatResponse {
  content: string;
  confidence: number;
  citations_used: string[];
  flags: string[];
  agent_id: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
}

interface CitationResult {
  citation: string;
  status: "verified" | "unverified" | "partial" | "error";
  steps_passed: string[];
  steps_failed: string[];
  external_source: string | null;
  holding_summary: string | null;
  holding_match: boolean | null;
  good_law: boolean | null;
  confidence: number;
  details: string;
}

interface DeadlineResult {
  event_date: string;
  deadline_date: string;
  jurisdiction: string;
  deadline_type: string;
  service_method: string;
  days_allowed: number;
  adjustments: string[];
  rule_citation: string;
  confidence: string;
  warning: string | null;
  conservative: boolean;
}

interface HealthStatus {
  status: string;
  agents: number;
  tests_passing: number;
}

async function apiCall<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      error: `HTTP ${response.status}`,
    }));
    throw new Error(error.error || error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  /** Check backend health */
  health: () => apiCall<HealthStatus>("/health"),

  /** Check backend readiness (API key configured) */
  ready: () => apiCall<{ ready: boolean; provider: string }>("/health/ready"),

  /** Send a message to the 5-agent orchestrator */
  chat: (message: string, jurisdiction?: string) =>
    apiCall<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message, jurisdiction }),
    }),

  /** Verify a legal citation via the 5-step chain */
  verifyCitation: (citation: string, claimedHolding?: string) =>
    apiCall<CitationResult>("/api/v1/verify-citation", {
      method: "POST",
      body: JSON.stringify({
        citation,
        claimed_holding: claimedHolding,
      }),
    }),

  /** Compute a jurisdiction-aware deadline */
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
};

export type { ChatResponse, CitationResult, DeadlineResult, HealthStatus };
