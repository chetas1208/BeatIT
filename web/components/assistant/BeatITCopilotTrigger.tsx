"use client";

/*
 * CONTRACT: small persistent floating control for the new unified BeatIT
 *   Copilot (docs/assistant/GLOBAL_ARCHITECTURE.md). Owns open/close state so
 *   AppShell only needs one flag-gated line to mount this feature. Placed at
 *   bottom-left (CopilotDock/CareGuardCopilot use bottom-right) so both can
 *   coexist on screen without overlapping while this is being built out.
 * Only rendered by AppShell when NEXT_PUBLIC_UNIFIED_ASSISTANT_ENABLED=true.
 */

import { useState } from "react";
import { ChatCircleDots, X } from "@phosphor-icons/react";
import { BeatITCopilotPanel } from "@/components/assistant/BeatITCopilotPanel";

export function BeatITCopilotTrigger() {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-4 left-4" style={{ zIndex: "var(--ht-z-dock)" }}>
      <BeatITCopilotPanel open={open} onClose={() => setOpen(false)} />
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="ht-btn ht-btn-primary size-12 rounded-full p-0 shadow-[var(--ht-shadow-raised)]"
        aria-expanded={open}
        aria-label={open ? "Close BeatIT Copilot" : "Open BeatIT Copilot"}
      >
        {open ? (
          <X weight="bold" className="size-5" />
        ) : (
          <ChatCircleDots weight="fill" className="size-5" />
        )}
      </button>
    </div>
  );
}
