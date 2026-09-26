"""Tests for python/hearttwin/assistant/case_context.py (Wave 6.5).

Follows test_tool_registry.py's/test_physician_tools.py's pattern for
persisting a real case through the real in-memory/Redis-fallback storage
layer (``tools.storage.store_case``) rather than mocking it — this module's
only real job is to be a faithful, isolated wrapper over that storage, so a
mock would hide the exact bug class (cross-case leakage) this file exists to
catch. Every case_id is uuid4-suffixed (matching cardiac_findings_case_id's
convention in test_tool_registry.py) because the in-memory store is a
module-level dict with no per-test teardown.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from python.hearttwin.assistant.case_context import (
    CaseContext,
    CaseContextResolutionError,
    resolve_case_context,
    resolve_historical_reference,
)
from python.hearttwin.assistant.schemas import ConversationContext
from python.hearttwin.schemas import CaseRecord
from python.hearttwin.tools.storage import store_case

_BASE_CONTEXT_KWARGS = dict(conversation_id="conv-1", audience="physician")


def _context(**overrides) -> ConversationContext:
    return ConversationContext(**{**_BASE_CONTEXT_KWARGS, **overrides})


@pytest.fixture
async def case_a_id() -> str:
    case_id = f"case-context-case-a-{uuid4()}"
    case = CaseRecord(case_id=case_id, patient_notes="Case A — reduced EF trajectory", status="operated")
    await store_case(case_id, case.model_dump(mode="json"))
    return case_id


@pytest.fixture
async def case_b_id() -> str:
    case_id = f"case-context-case-b-{uuid4()}"
    case = CaseRecord(case_id=case_id, patient_notes="Case B — preserved EF, rhythm issue", status="recovery_simulated")
    await store_case(case_id, case.model_dump(mode="json"))
    return case_id


# ---------------------------------------------------------------------------
# resolve_case_context — success
# ---------------------------------------------------------------------------


async def test_resolves_real_case_by_case_id(case_a_id: str) -> None:
    context = _context(component_id="LV", scenario_id="scn-1")

    result = await resolve_case_context(context, case_a_id)

    assert isinstance(result, CaseContext)
    assert result.case_id == case_a_id
    assert result.conversation_id == "conv-1"
    assert result.case_revision == "operated"
    assert result.component_id == "LV"
    assert result.scenario_id == "scn-1"


async def test_carries_over_conversation_context_selection_fields(case_a_id: str) -> None:
    context = _context(
        snapshot_id="snap-7",
        component_id="RV",
        product_space="component",
        ensemble_id="ens-1",
        shadow_trial_id="trial-1",
        pair_id="pair-1",
        target_metric="ejection_fraction",
    )

    result = await resolve_case_context(context, case_a_id)

    assert isinstance(result, CaseContext)
    assert result.current_snapshot_id == "snap-7"
    assert result.product_space == "component"
    assert result.ensemble_id == "ens-1"
    assert result.shadow_trial_id == "trial-1"
    assert result.pair_id == "pair-1"
    assert result.target_metric == "ejection_fraction"
    assert result.audience == "physician"


# ---------------------------------------------------------------------------
# resolve_case_context — typed failure, never a silent None
# ---------------------------------------------------------------------------


async def test_no_case_id_returns_typed_error_not_none() -> None:
    context = _context()

    result = await resolve_case_context(context, None)

    assert isinstance(result, CaseContextResolutionError)
    assert result.reason == "no_case_id"
    assert result.conversation_id == "conv-1"


async def test_blank_case_id_is_treated_as_missing() -> None:
    context = _context()

    result = await resolve_case_context(context, "   ")

    assert isinstance(result, CaseContextResolutionError)
    assert result.reason == "no_case_id"


async def test_unknown_case_id_returns_typed_error() -> None:
    context = _context()

    result = await resolve_case_context(context, f"nonexistent-case-{uuid4()}")

    assert isinstance(result, CaseContextResolutionError)
    assert result.reason == "case_not_found"


# ---------------------------------------------------------------------------
# resolve_historical_reference — bounded scope
# ---------------------------------------------------------------------------


def test_no_historical_cue_resolves_to_current_snapshot() -> None:
    case_context = CaseContext(
        case_id="case-x",
        conversation_id="conv-1",
        current_snapshot_id="snap-3",
    )

    resolved = resolve_historical_reference(case_context, "what is the ejection fraction now?")

    assert resolved.resolution_kind == "current"
    assert resolved.resolved_snapshot_id == "snap-3"


def test_prior_reference_with_no_history_is_honestly_unresolved() -> None:
    case_context = CaseContext(
        case_id="case-x",
        conversation_id="conv-1",
        current_snapshot_id="snap-3",
    )

    resolved = resolve_historical_reference(case_context, "what did it look like before?")

    assert resolved.resolution_kind == "unresolved"
    assert resolved.resolved_snapshot_id is None


def test_prior_reference_with_history_resolves_to_immediately_prior_snapshot() -> None:
    case_context = CaseContext(
        case_id="case-x",
        conversation_id="conv-1",
        current_snapshot_id="snap-3",
        snapshot_history=["snap-1", "snap-2", "snap-3", "snap-4"],
    )

    resolved = resolve_historical_reference(case_context, "how does this compare to earlier?")

    assert resolved.resolution_kind == "immediately_prior"
    assert resolved.resolved_snapshot_id == "snap-2"


def test_prior_reference_at_earliest_known_snapshot_is_unresolved() -> None:
    case_context = CaseContext(
        case_id="case-x",
        conversation_id="conv-1",
        current_snapshot_id="snap-1",
        snapshot_history=["snap-1", "snap-2"],
    )

    resolved = resolve_historical_reference(case_context, "what was it like before?")

    assert resolved.resolution_kind == "unresolved"
    assert resolved.resolved_snapshot_id is None


def test_empty_reference_text_is_unresolved() -> None:
    case_context = CaseContext(case_id="case-x", conversation_id="conv-1")

    resolved = resolve_historical_reference(case_context, "   ")

    assert resolved.resolution_kind == "unresolved"


# ---------------------------------------------------------------------------
# Case isolation — the most important test in this file (spec §57/§61:
# cross-case contamination target 0). Two real, independently persisted
# cases; resolving one must never read or return anything from the other.
# ---------------------------------------------------------------------------


async def test_case_isolation_resolving_one_case_never_returns_the_others_identity(
    case_a_id: str, case_b_id: str
) -> None:
    context_a = _context(conversation_id="conv-a", component_id="LV", snapshot_id="a-snap-1")
    context_b = _context(conversation_id="conv-b", component_id="RV", snapshot_id="b-snap-1")

    result_a = await resolve_case_context(context_a, case_a_id)
    result_b = await resolve_case_context(context_b, case_b_id)

    assert isinstance(result_a, CaseContext)
    assert isinstance(result_b, CaseContext)

    # Identity never crosses over.
    assert result_a.case_id == case_a_id
    assert result_b.case_id == case_b_id
    assert result_a.case_id != result_b.case_id

    # case_revision came from each case's own stored status, not the other's.
    assert result_a.case_revision == "operated"
    assert result_b.case_revision == "recovery_simulated"
    assert result_a.case_revision != result_b.case_revision

    # Per-conversation selection state never crosses over either.
    assert result_a.component_id == "LV"
    assert result_b.component_id == "RV"
    assert result_a.current_snapshot_id == "a-snap-1"
    assert result_b.current_snapshot_id == "b-snap-1"
    assert result_a.conversation_id == "conv-a"
    assert result_b.conversation_id == "conv-b"


async def test_case_isolation_wrong_case_id_never_falls_back_to_another_real_case(
    case_a_id: str, case_b_id: str
) -> None:
    """Resolving with a case_id that doesn't exist must return a typed error,
    never silently substitute some other real case (e.g. the last one
    resolved, or a process-global "current case")."""
    context = _context()

    await resolve_case_context(context, case_a_id)  # warm up any accidental shared state
    result = await resolve_case_context(context, f"definitely-not-a-real-case-{uuid4()}")

    assert isinstance(result, CaseContextResolutionError)
    assert result.reason == "case_not_found"


def test_historical_reference_resolution_is_isolated_per_case_context() -> None:
    """Two CaseContext instances for different cases, with different
    snapshot histories, must never leak into each other's resolution."""
    case_context_a = CaseContext(
        case_id="case-a",
        conversation_id="conv-a",
        current_snapshot_id="a-2",
        snapshot_history=["a-1", "a-2", "a-3"],
    )
    case_context_b = CaseContext(
        case_id="case-b",
        conversation_id="conv-b",
        current_snapshot_id="b-2",
        snapshot_history=["b-1", "b-2", "b-3"],
    )

    resolved_a = resolve_historical_reference(case_context_a, "what did it look like before?")
    resolved_b = resolve_historical_reference(case_context_b, "what did it look like before?")

    assert resolved_a.resolved_snapshot_id == "a-1"
    assert resolved_b.resolved_snapshot_id == "b-1"
    assert resolved_a.resolved_snapshot_id != resolved_b.resolved_snapshot_id
