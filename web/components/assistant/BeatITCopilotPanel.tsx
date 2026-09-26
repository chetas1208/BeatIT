"use client";

/*
 * CONTRACT: the third, standalone chat surface for the BeatIT unified
 *   assistant (docs/assistant/GLOBAL_ARCHITECTURE.md, Wave 4). Does NOT
 *   replace CopilotDock or CareGuardCopilot yet — those stay as-is until a
 *   later wave consolidates all three. Plain React + fetch via
 *   lib/assistantApi.ts; no CopilotKit SDK here.
 * NO UI COMPLEXITY LEAK: only ever shows "BeatIT Copilot" — never Laya,
 *   NVIDIA, model names, or execution-class internals.
 * The backend route (POST /assistant/message) is not mounted yet (Wave 3
 *   handoff), so a request failing with a 404 is expected today, not a bug —
 *   render it as an honest inline notice, never fabricate an answer.
 * Artifacts render as compact placeholder chips only ("[ View evidence ]");
 *   full artifact rendering is a separate, later work item (Agent 18) — keep
 *   this stub swappable, do not build a competing artifact viewer here.
 */

import { useMemo, useRef, useState, type FormEvent } from "react";
import { FileText, PaperPlaneRight, Sparkle } from "@phosphor-icons/react";
import { sendAssistantMessage, AssistantApiError } from "@/lib/assistantApi";
import { useFocusTrap } from "@/lib/assistant/useFocusTrap";
import type { AssistantArtifact, ExecutionClass } from "@/types/assistant";

interface ChatTurn {
  id: string;
  role: "user" | "assistant" | "notice";
  content: string;
  artifacts?: AssistantArtifact[];
  executionClass?: ExecutionClass;
}

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `turn-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** Compact, swappable stub — the real artifact viewer lands in a later wave. */
function ArtifactChip({ artifact }: { artifact: AssistantArtifact }) {
  return (
    <button
      type="button"
      className="ht-chip max-w-full"
      title={artifact.title}
      disabled
    >
      <FileText weight="duotone" className="size-3.5" />
      <span className="truncate">[ View evidence: {artifact.title} ]</span>
    </button>
  );
}

export function BeatITCopilotPanel({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const conversationId = useMemo(() => newId(), []);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  // Traps Tab inside the panel, closes on Escape, and restores focus to the
  // trigger button on close — the panel renders via `if (!open) return null`
  // below rather than unmounting, so `open` doubles as the trap's active flag.
  useFocusTrap(containerRef, open, onClose);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    setInput("");
    setTurns((prev) => [...prev, { id: newId(), role: "user", content: message }]);
    setLoading(true);

    try {
      const response = await sendAssistantMessage({
        conversation_id: conversationId,
        message,
        context: { conversation_id: conversationId, audience: "general" },
      });
      setTurns((prev) => [
        ...prev,
        {
          id: newId(),
          role: "assistant",
          content: response.message,
          artifacts: response.artifacts,
          executionClass: response.execution_class,
        },
      ]);
    } catch (cause) {
      const detail =
        cause instanceof AssistantApiError && cause.status === 404
          ? "The assistant is still warming up — this feature isn't connected yet."
          : cause instanceof Error
            ? cause.message
            : "The assistant is unavailable right now.";
      setTurns((prev) => [...prev, { id: newId(), role: "notice", content: detail }]);
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div
      ref={containerRef}
      className="ht-panel-raised fixed bottom-20 left-4 flex h-[min(34rem,calc(100dvh-7rem))] w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden"
      style={{ zIndex: "var(--ht-z-dock)" }}
      role="dialog"
      aria-modal="true"
      aria-label="BeatIT Copilot"
    >
      <header className="flex items-center gap-2 px-4 py-3">
        <span
          aria-hidden
          className="grid size-7 place-items-center rounded-[var(--ht-r-sm)] border border-[var(--ht-accent-line)] bg-[var(--ht-accent-soft)] text-accent-bright"
        >
          <Sparkle weight="fill" className="size-4" />
        </span>
        <div className="flex flex-col leading-none">
          <span className="ht-panel-title text-[0.9rem]">BeatIT Copilot</span>
          <span className="text-[0.62rem] text-muted">Educational simulation only</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ht-btn ht-btn-ghost ml-auto size-8 rounded-[var(--ht-r-sm)] p-0"
          aria-label="Close BeatIT Copilot"
        >
          &times;
        </button>
      </header>
      <div className="ht-hairline" />

      <div
        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-4 py-3"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
      >
        {turns.length === 0 ? (
          <p className="text-[0.78rem] leading-relaxed text-muted">
            Ask about this case. Answers are educational simulation output, not
            medical advice.
          </p>
        ) : null}
        {turns.map((turn) => (
          <div
            key={turn.id}
            className={`max-w-[85%] rounded-[var(--ht-r-md)] px-3 py-2 text-[0.82rem] leading-relaxed ${
              turn.role === "user"
                ? "self-end bg-[var(--ht-accent)] text-[var(--ht-accent-ink)]"
                : turn.role === "notice"
                  ? "self-start border border-[var(--ht-line)] bg-surface-2/50 text-muted"
                  : "self-start border border-[var(--ht-line)] bg-[var(--ht-surface-3)] text-ink"
            }`}
          >
            <div>{turn.content}</div>
            {turn.artifacts && turn.artifacts.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {turn.artifacts.map((artifact) => (
                  <ArtifactChip key={artifact.id} artifact={artifact} />
                ))}
              </div>
            ) : null}
          </div>
        ))}
        {loading ? (
          <div className="self-start text-[0.74rem] text-muted">BeatIT Copilot is thinking&hellip;</div>
        ) : null}
      </div>

      <div className="ht-hairline" />
      <form onSubmit={handleSubmit} className="flex items-center gap-2 px-3 py-2.5">
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about this case"
          aria-label="Message BeatIT Copilot"
          disabled={loading}
          className="h-9 min-w-0 flex-1 rounded-[var(--ht-r-md)] border border-[var(--ht-line-strong)] bg-[var(--ht-surface-1)] px-3 text-[0.82rem] text-ink outline-none focus:border-[var(--ht-signal-line)]"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="ht-btn ht-btn-primary size-9 rounded-[var(--ht-r-md)] p-0"
          aria-label="Send message"
        >
          <PaperPlaneRight weight="fill" className="size-4" />
        </button>
      </form>
    </div>
  );
}
