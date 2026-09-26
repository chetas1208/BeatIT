/*
 * Typed HTTP client for the unified BeatIT conversation assistant
 * (python/hearttwin/assistant/router.py, POST /assistant/message).
 *
 * Deliberately standalone from web/lib/api.ts (that file is mid-edit by a
 * concurrent agent on an unrelated feature; this is a separate, additive
 * surface per docs/assistant/WAVE_3_HANDOFF.md). It mirrors api.ts's
 * conventions on purpose: same NEXT_PUBLIC_API_BASE env var, same
 * ApiRequestError shape, same "no silent fallback, no mock data" rule — a
 * failed request throws so the caller (BeatITCopilotPanel) can render an
 * honest state instead of fabricating a response.
 *
 * The router is not yet mounted into the live FastAPI app (Wave 3 handoff),
 * so callers should expect this to throw a 404 ApiRequestError today — that
 * is the correct, honest behavior, not a bug in this client.
 */

import type { AssistantRequest, AssistantResponse } from "@/types/assistant";

function resolveApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE;
  if (!base) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE is not set. Create web/.env.local with " +
        "NEXT_PUBLIC_API_BASE=http://localhost:8000/api/v1",
    );
  }
  return base.replace(/\/$/, "");
}

export class AssistantApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly safetyDisclaimer?: string;

  constructor(args: { status: number; detail: string; safetyDisclaimer?: string }) {
    super(`[${args.status}] /assistant/message: ${args.detail}`);
    this.name = "AssistantApiError";
    this.status = args.status;
    this.detail = args.detail;
    this.safetyDisclaimer = args.safetyDisclaimer;
  }
}

async function parseError(response: Response): Promise<AssistantApiError> {
  let detail = response.statusText || "Request failed";
  let safetyDisclaimer: string | undefined;
  try {
    const body = (await response.json()) as {
      detail?: unknown;
      error?: unknown;
      safety_disclaimer?: string;
    };
    if (typeof body.detail === "string") detail = body.detail;
    else if (typeof body.error === "string") detail = body.error;
    else if (body.detail) detail = JSON.stringify(body.detail);
    safetyDisclaimer = body.safety_disclaimer;
  } catch {
    /* non-JSON error body (e.g. a plain 404) — keep status text */
  }
  return new AssistantApiError({ status: response.status, detail, safetyDisclaimer });
}

export async function sendAssistantMessage(
  request: AssistantRequest,
): Promise<AssistantResponse> {
  const base = resolveApiBase();
  let response: Response;
  try {
    response = await fetch(`${base}/assistant/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(request),
    });
  } catch (cause) {
    throw new AssistantApiError({
      status: 0,
      detail:
        cause instanceof Error
          ? `Network error: ${cause.message}`
          : "Network error: backend unreachable",
    });
  }
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as AssistantResponse;
}
