"""Context resolution for the unified BeatIT conversation assistant (Wave 3).

Two responsibilities, per docs/assistant/GLOBAL_ARCHITECTURE.md's "CONTEXT
ARCHITECTURE" section:

1. ``resolve_context`` — decide whether a chat message with a bare referent
   ("this", "that", "it", "here") can be safely routed using the
   ConversationContext that already exists, or whether the pipeline must
   short-circuit to ``ExecutionClass.CLARIFICATION_REQUIRED`` instead of
   guessing which component/snapshot/scenario the user means.
2. ``apply_context_event`` — apply an explicit UI context-update event (a
   click, a timeline scrub, a pair-open, ...) to a ConversationContext. This
   is the backend-side half of GLOBAL_ARCHITECTURE.md's context-source list
   ("click LV -> component_id=LV; scrub timeline -> snapshot_id updates;
   open paired Twin #284 -> pair_id=284") — no frontend wiring is built here,
   only the pure data transformation the frontend will eventually call into.

Deliberately NOT built here: any NLP/entity-extraction step that reads "the
LV" or "snapshot 12" out of free chat text and writes a new id into
ConversationContext. No such extractor exists anywhere in Wave 1-2's work,
and inferring an id out of prose is exactly the kind of unsafe guess
CLARIFICATION_REQUIRED exists to avoid — ``resolve_context`` only ever
answers "can the referents already in `message` be satisfied by the context
we already have," never "what new context does this text imply." That
inference step (if ever built) is separate, later work, not a gap in this
module.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from python.hearttwin.assistant.laya_adapter import LayaAdapter
from python.hearttwin.assistant.schemas import ConversationContext

ContextEventType = Literal[
    "component_selected",
    "snapshot_selected",
    "pair_opened",
    "scenario_created",
    "target_metric_changed",
]

# One UI event maps to exactly one ConversationContext field. Kept as a
# lookup table (not an if/elif chain) so adding a new event type is a
# one-line addition here, never new branching logic in a caller.
_EVENT_FIELD: dict[str, str] = {
    "component_selected": "component_id",
    "snapshot_selected": "snapshot_id",
    "pair_opened": "pair_id",
    "scenario_created": "scenario_id",
    "target_metric_changed": "target_metric",
}


class ContextResolution(BaseModel):
    """Result of resolving one chat message against the current context.

    ``context`` is returned unchanged from the input — see the module
    docstring for why no text-derived field write happens here yet — but is
    still carried on the result so callers have one stable return shape to
    extend if a real entity-resolution step is ever added, without changing
    every call site.
    """

    context: ConversationContext
    needs_clarification: bool
    note: str


async def resolve_context(
    message: str,
    context: ConversationContext,
    laya: Optional[LayaAdapter] = None,
) -> ContextResolution:
    """Decide whether `message` can be routed safely against `context`.

    Delegates the actual ambiguity judgment to
    ``LayaAdapter.needs_clarification`` (env-guarded, deterministic-fallback
    — see laya_adapter.py) rather than re-implementing its bare-referent
    heuristic here, per GLOBAL_ARCHITECTURE.md's "ONE decision-control plane"
    rule: this module is a thin caller of that one decision, not a second
    ambiguity detector.
    """
    adapter = laya or LayaAdapter()
    decision = await adapter.needs_clarification(message, context.model_dump())
    if decision.answer:
        note = (
            "message contains an unresolved referent (e.g. 'this'/'that'/'it'/"
            "'here', or too little content to route) with no matching context "
            "id already set — surfacing CLARIFICATION_REQUIRED instead of guessing"
        )
    else:
        note = "no unresolved referent detected; existing context is sufficient to route this message"
    return ContextResolution(context=context, needs_clarification=decision.answer, note=note)


def apply_context_event(
    context: ConversationContext,
    event_type: ContextEventType,
    value: str,
) -> ConversationContext:
    """Apply one explicit UI context-update event (never chat text).

    Pure data transformation: returns a new ConversationContext with exactly
    one field set to ``value``, every other field carried over unchanged.

    Expected frontend call shape (future work, not built here — see
    docs/assistant/wave3/context-and-orchestration.md): the UI posts
    ``{conversation_id, event_type, value}`` whenever it already knows the
    user changed selection (component click, timeline scrub, pair-open,
    scenario creation, target-metric picker), and the backend loads the
    conversation's current ConversationContext and calls this function with
    it — this function never looks anything up itself.
    """
    if event_type not in _EVENT_FIELD:
        raise ValueError(
            f"unknown context event type {event_type!r}; expected one of {sorted(_EVENT_FIELD)}"
        )
    field = _EVENT_FIELD[event_type]
    return context.model_copy(update={field: value})
