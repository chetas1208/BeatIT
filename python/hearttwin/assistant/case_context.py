"""Case-context hardening for the unified BeatIT conversation assistant (Wave 6.5).

See docs/architecture/CASE_CONTEXT_MODEL.md for the full write-up. Summary of
what this module is and is not:

- This is a NEW, additive companion to ``ConversationContext``
  (python/hearttwin/assistant/schemas.py), not a second context system and
  not a replacement. ``ConversationContext`` is not modified — this wave's
  brief treats it as a shared Wave 2 file other code already imports.
- ``docs/assistant/BACKLOG.md`` item 8 flagged a real, undecided gap:
  ``ConversationContext`` has no ``case_id`` field, so every physician tool
  that requires one (``get_cardiac_findings``, ``get_pv_loop``,
  ``get_raw_provenance_ledger``, ``get_findings_by_region`` — see
  ``physician_tools.py``'s tool schemas) is unreachable through the
  orchestrator's generic context-based dispatch
  (``orchestrator.py::_resolve_required_args``, which matches a tool's
  required argument names 1:1 against ``ConversationContext`` fields and
  finds no ``case_id``).
- The decision made here (evidence in CASE_CONTEXT_MODEL.md): ``case_id``
  maps directly and only onto the real backend ``CaseRecord.case_id``
  (python/hearttwin/schemas.py) — the literal key used by
  ``python.hearttwin.tools.storage.store_case``/``get_case``
  (``case:{case_id}``). It is kept as its own field here, NOT unified with
  ``ConversationContext.patient_id`` — Wave 3 already left an explicit note
  in ``orchestrator.py`` (`_resolve_required_args`'s docstring) that
  guessing ``patient_id`` is a ``case_id`` would be an unsafe assumption,
  and nothing in the current backend maps one onto the other. ``CaseRecord``
  has no separate patient-identity field at all today.
- ``case_revision``: verified against the real backend that there is no
  revision/version/history concept for a case. ``tools/storage.py::store_case``
  overwrites the single Redis/in-memory key for a ``case_id`` on every save
  — no history is retained. ``CaseRecord.updated_at`` looks like a revision
  marker but is NOT one in practice: every mutation route in ``api.py``
  reconstructs ``case = CaseRecord(**case_data)`` from the previously stored
  dict and never reassigns ``updated_at`` before calling ``store_case``
  again, so pydantic keeps the original value from the dict rather than
  re-running its ``default_factory`` — the field is effectively frozen at
  case-creation time. The only real, always-current, monotonically
  *progressing* (if not strictly ordinal) per-case signal is
  ``CaseRecord.status`` (``created`` -> ``extracted`` -> ``operated`` ->
  ``recovery_simulated`` -> ``self_improved``, or an error branch like
  ``blocked``/``extraction_failed``), set explicitly at each pipeline stage
  in ``orchestrator.py``. ``CaseContext.case_revision`` is therefore backed
  by ``CaseRecord.status`` today, documented honestly as a coarse lifecycle
  marker, not a monotonic revision counter — see CASE_CONTEXT_MODEL.md for
  what a real revision system would need.
- ``resolve_historical_reference`` is a bounded, honest implementation of
  "which prior snapshot does 'before'/'earlier' refer to" (spec §7-§8): the
  backend has no persisted snapshot timeline for a case at all (no
  ``Snapshot`` model, no history list — ``ConversationContext.snapshot_id``
  is just an opaque, frontend-supplied current value). This module accepts
  an optional, caller-supplied ``snapshot_history`` (ordered oldest-to-newest,
  a future caller's job to populate from whatever real timeline data it has
  — e.g. the frontend's ``Timeline.tsx`` snapshot list, per
  docs/assistant/wave4/contextual-interaction.md) and resolves a bare "prior"
  reference to the entry immediately before the current one *in that list*.
  With no ``snapshot_history`` supplied (today's default — nothing populates
  it yet), a "before"/"earlier" reference resolves to ``unresolved`` rather
  than guessing. This is NOT a temporal-reasoning engine: it does not
  understand "two visits ago", specific dates, or named snapshots.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from python.hearttwin.assistant.schemas import ConversationContext
from python.hearttwin.schemas import CaseRecord
from python.hearttwin.tools.storage import get_case

# ---------------------------------------------------------------------------
# CaseContext
# ---------------------------------------------------------------------------

CaseContextErrorReason = Literal["no_case_id", "case_not_found"]


class CaseContext(BaseModel):
    """Case-specific extension of ``ConversationContext``.

    Fields that already exist on ``ConversationContext`` ("what's currently
    selected" — component/scenario/ensemble/shadow-trial/pair/target-metric/
    product-space/audience) are carried over by ``resolve_case_context``
    rather than redefined with new semantics — this model does not invent a
    second vocabulary for the same selection state, it adds the case-identity
    and history layer ``ConversationContext`` does not have.
    """

    case_id: str
    conversation_id: str

    # See module docstring: backed by CaseRecord.status, a coarse lifecycle
    # marker, not a monotonic revision counter. Optional because a case
    # record predating this field's introduction could theoretically have no
    # readable status, though CaseRecord always defaults it to "created".
    case_revision: Optional[str] = None

    # Current selection, reused verbatim from ConversationContext — see class
    # docstring. current_snapshot_id is the case-context name for
    # ConversationContext.snapshot_id (renamed here only to read naturally
    # next to snapshot_history, which ConversationContext has no equivalent
    # of).
    current_snapshot_id: Optional[str] = None
    component_id: Optional[str] = None
    scenario_id: Optional[str] = None
    ensemble_id: Optional[str] = None
    shadow_trial_id: Optional[str] = None
    pair_id: Optional[str] = None
    target_metric: Optional[str] = None
    product_space: Optional[str] = None
    audience: Optional[Literal["general", "physician"]] = None

    # Ordered oldest-to-newest, caller-supplied (see module docstring) — empty
    # by default since nothing in the backend populates it yet.
    snapshot_history: list[str] = Field(default_factory=list)


class CaseContextResolutionError(BaseModel):
    """Typed, explicit failure to resolve an active case.

    Never returned as ``None`` and never silently defaulted to some other
    case — GLOBAL_ARCHITECTURE.md / this spec's §18 rule ("no hallucinated
    context — if ambiguous, ask one clarifying question") requires a caller
    to be able to distinguish "no case resolvable" from "resolved". The
    actual clarifying-question UX (surfacing this as
    ``ExecutionClass.CLARIFICATION_REQUIRED`` to the user, the way
    ``context_resolver.resolve_context`` already does for bare referents) is
    the orchestrator's job — see docs/architecture/CASE_CONTEXT_MODEL.md's
    "orchestrator.py integration points" section for exactly where and how,
    intentionally not implemented in this module or in orchestrator.py.
    """

    reason: CaseContextErrorReason
    message: str
    conversation_id: str


async def resolve_case_context(
    conversation_context: ConversationContext,
    case_id: Optional[str],
    *,
    snapshot_history: Optional[list[str]] = None,
) -> CaseContext | CaseContextResolutionError:
    """Resolve the active case for ``conversation_context``.

    Deliberately async (unlike the signature sketched in this wave's brief)
    because the only real way to verify a case exists is
    ``tools.storage.get_case``, which is itself async (it may hit Redis) —
    matching every other real case lookup in this codebase
    (``physician_tools.py::_load_case``, ``copilot.py::_load_case``). A sync
    function could not honestly answer "does this case exist" without either
    blocking the event loop or lying.

    Resolution order is intentionally simple and non-guessing:

    1. No ``case_id`` supplied (None or blank) -> ``CaseContextResolutionError``
       (reason ``"no_case_id"``). ``ConversationContext`` has no ``case_id``
       field of its own (see module docstring), so there is nothing else in
       ``conversation_context`` to fall back to — falling back to
       ``patient_id`` would repeat the exact unsafe guess Wave 3's
       ``orchestrator.py`` already refused to make.
    2. ``case_id`` supplied but ``get_case`` finds nothing ->
       ``CaseContextResolutionError`` (reason ``"case_not_found"``).
    3. Otherwise, build and return a ``CaseContext`` scoped to exactly that
       case's stored record plus ``conversation_context``'s own selection
       fields.

    Detecting a genuinely *ambiguous* case (e.g. more than one plausible
    case for this conversation) is out of scope: nothing in the current
    backend associates a conversation with more than one candidate case, so
    there is no real signal to detect ambiguity from yet — see
    CASE_CONTEXT_MODEL.md.
    """
    normalized_case_id = (case_id or "").strip()
    if not normalized_case_id:
        return CaseContextResolutionError(
            reason="no_case_id",
            message=(
                "no case_id was supplied and ConversationContext carries no case "
                "identity of its own — cannot resolve an active case without "
                "guessing"
            ),
            conversation_id=conversation_context.conversation_id,
        )

    case_data = await get_case(normalized_case_id)
    if not case_data:
        return CaseContextResolutionError(
            reason="case_not_found",
            message=f"case {normalized_case_id!r} was not found in storage",
            conversation_id=conversation_context.conversation_id,
        )

    case = CaseRecord(**case_data)
    return CaseContext(
        case_id=case.case_id,
        conversation_id=conversation_context.conversation_id,
        case_revision=case.status,
        current_snapshot_id=conversation_context.snapshot_id,
        component_id=conversation_context.component_id,
        scenario_id=conversation_context.scenario_id,
        ensemble_id=conversation_context.ensemble_id,
        shadow_trial_id=conversation_context.shadow_trial_id,
        pair_id=conversation_context.pair_id,
        target_metric=conversation_context.target_metric,
        product_space=conversation_context.product_space,
        audience=conversation_context.audience,
        snapshot_history=list(snapshot_history) if snapshot_history else [],
    )


# ---------------------------------------------------------------------------
# Historical reference resolution (spec §7-§8) — bounded scope, see module
# docstring.
# ---------------------------------------------------------------------------

ReferenceResolutionKind = Literal["current", "immediately_prior", "unresolved"]

# Ordered so an explicit "prior" cue is checked before assuming "current" —
# a message can legitimately contain both ("what's changed since before?"),
# in which case the historical intent should win.
_PRIOR_PATTERNS: tuple[str, ...] = (
    r"\bbefore\b",
    r"\bearlier\b",
    r"\bprior\b",
    r"\bpreviously\b",
    r"\blast time\b",
    r"\bused to\b",
    r"\bpre-",
)
_CURRENT_PATTERNS: tuple[str, ...] = (
    r"\bnow\b",
    r"\bcurrent(ly)?\b",
    r"\btoday\b",
    r"\bright now\b",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


class ResolvedReference(BaseModel):
    reference_text: str
    resolution_kind: ReferenceResolutionKind
    resolved_snapshot_id: Optional[str] = None
    note: str


def resolve_historical_reference(case_context: CaseContext, reference_text: str) -> ResolvedReference:
    """Resolve a "before"/"earlier"/"now" style reference against one case.

    Bounded, honest scope (see module docstring): this can only ever resolve
    to "the entry immediately before the current snapshot" within
    ``case_context.snapshot_history`` — a caller-supplied, ordered
    (oldest-to-newest) list, since the backend keeps no such history itself.
    It never guesses a snapshot id that isn't in that list, and it never
    reads or is influenced by any other ``CaseContext`` instance — this
    function is pure over its two arguments only, which is what makes cross-
    case isolation (see test_case_context.py) straightforward to guarantee.
    """
    normalized = _normalize(reference_text)
    if not normalized:
        return ResolvedReference(
            reference_text=reference_text,
            resolution_kind="unresolved",
            note="empty reference text",
        )

    wants_prior = _matches_any(normalized, _PRIOR_PATTERNS)
    wants_current = _matches_any(normalized, _CURRENT_PATTERNS)

    if wants_prior and not wants_current:
        history = case_context.snapshot_history
        current = case_context.current_snapshot_id
        if current and current in history:
            index = history.index(current)
            if index > 0:
                return ResolvedReference(
                    reference_text=reference_text,
                    resolution_kind="immediately_prior",
                    resolved_snapshot_id=history[index - 1],
                    note="resolved to the snapshot immediately before the case's current snapshot in the supplied history",
                )
        return ResolvedReference(
            reference_text=reference_text,
            resolution_kind="unresolved",
            note=(
                "reference implies a prior snapshot, but no earlier snapshot is "
                "available (snapshot_history is empty, missing the current "
                "snapshot, or the current snapshot is already the earliest known "
                "one) — do not guess; ask the user which snapshot they mean"
            ),
        )

    # No prior cue at all (or prior+current both present, treated as
    # referring to the current snapshot with a comparison mentioned) resolves
    # to "current" — the same "existing context is sufficient, don't guess a
    # new referent" default context_resolver.py already uses for bare chat
    # referents.
    return ResolvedReference(
        reference_text=reference_text,
        resolution_kind="current",
        resolved_snapshot_id=case_context.current_snapshot_id,
        note="no unresolved historical reference detected; resolved to the case's current snapshot",
    )
