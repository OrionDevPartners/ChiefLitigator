/**
 * Chat API route — proxies to Cyphergy FastAPI backend.
 *
 * In development: proxies to localhost:8000
 * In production: proxies to the Fargate-hosted API via NEXT_PUBLIC_API_URL
 *
 * NO hardcoded model names, NO direct LLM calls from frontend.
 * All LLM work happens server-side in the 5-agent orchestrator.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const maxDuration = 60;

export async function POST(req: Request) {
  const body = await req.json();
  const { messages } = body;

  // Extract the latest user message
  const lastMessage = messages?.[messages.length - 1];
  if (!lastMessage?.content) {
    return new Response(
      JSON.stringify({ error: "No message content provided" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  try {
    // Call Cyphergy backend /api/v1/chat
    const response = await fetch(`${API_BASE}/api/v1/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Forward auth token if present
        ...(req.headers.get("Authorization")
          ? { Authorization: req.headers.get("Authorization")! }
          : {}),
      },
      body: JSON.stringify({
        message: lastMessage.content,
        jurisdiction: null, // Will be set from case context
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: "Backend error" }));
      return new Response(JSON.stringify(error), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    const data = await response.json();

    // Return in the format the chat UI expects
    return new Response(
      JSON.stringify({
        role: "assistant",
        content: data.content,
        // Include metadata from the orchestrator
        metadata: {
          confidence: data.confidence,
          citations: data.citations_used,
          flags: data.flags,
          agent: data.agent_id,
        },
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (error) {
    // Backend unreachable
    return new Response(
      JSON.stringify({
        role: "assistant",
        content:
          "The Cyphergy backend is not running. Start it with: uvicorn src.api:app --reload --port 8000",
      }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}
