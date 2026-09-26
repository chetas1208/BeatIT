"""Tests for python/hearttwin/assistant/context_resolver.py (Wave 3).

Uses a fresh, unconfigured LayaAdapter throughout (no LAYA_ENABLED in this
test environment — see test_laya_adapter.py), so `needs_clarification`
always runs its deterministic keyword fallback, never a network call.
"""

from __future__ import annotations

from python.hearttwin.assistant.context_resolver import apply_context_event, resolve_context
from python.hearttwin.assistant.schemas import ConversationContext

_BASE_CONTEXT_KWARGS = dict(conversation_id="conv-1", audience="general")


def _context(**overrides) -> ConversationContext:
    return ConversationContext(**{**_BASE_CONTEXT_KWARGS, **overrides})


# ---------------------------------------------------------------------------
# resolve_context
# ---------------------------------------------------------------------------


async def test_bare_referent_with_no_resolving_context_needs_clarification() -> None:
    context = _context()
    resolution = await resolve_context("what about here?", context)

    assert resolution.needs_clarification is True
    assert resolution.context == context
    assert "clarif" in resolution.note.lower() or "unresolved" in resolution.note.lower()


async def test_same_bare_referent_with_component_id_set_does_not_need_clarification() -> None:
    context = _context(component_id="LV")
    resolution = await resolve_context("what about here?", context)

    assert resolution.needs_clarification is False


async def test_unambiguous_question_does_not_need_clarification() -> None:
    context = _context()
    resolution = await resolve_context("What is the current ejection fraction?", context)

    assert resolution.needs_clarification is False


async def test_near_empty_message_needs_clarification_even_with_context_set() -> None:
    # needs_clarification's fallback treats near-empty input as ambiguous
    # regardless of resolving context — a single word can't be safely routed.
    context = _context(component_id="LV", ensemble_id="ens-1")
    resolution = await resolve_context("this?", context)

    assert resolution.needs_clarification is True


# ---------------------------------------------------------------------------
# apply_context_event
# ---------------------------------------------------------------------------


def test_component_selected_updates_only_component_id() -> None:
    context = _context()
    updated = apply_context_event(context, "component_selected", "LV")

    assert updated.component_id == "LV"
    assert updated.model_dump(exclude={"component_id"}) == context.model_dump(exclude={"component_id"})


def test_snapshot_selected_updates_only_snapshot_id() -> None:
    context = _context()
    updated = apply_context_event(context, "snapshot_selected", "snap-42")

    assert updated.snapshot_id == "snap-42"
    assert updated.model_dump(exclude={"snapshot_id"}) == context.model_dump(exclude={"snapshot_id"})


def test_pair_opened_updates_only_pair_id() -> None:
    context = _context()
    updated = apply_context_event(context, "pair_opened", "pair-284")

    assert updated.pair_id == "pair-284"
    assert updated.model_dump(exclude={"pair_id"}) == context.model_dump(exclude={"pair_id"})


def test_scenario_created_updates_only_scenario_id() -> None:
    context = _context()
    updated = apply_context_event(context, "scenario_created", "scenario-7")

    assert updated.scenario_id == "scenario-7"
    assert updated.model_dump(exclude={"scenario_id"}) == context.model_dump(exclude={"scenario_id"})


def test_target_metric_changed_updates_only_target_metric() -> None:
    context = _context()
    updated = apply_context_event(context, "target_metric_changed", "delta_sv")

    assert updated.target_metric == "delta_sv"
    assert updated.model_dump(exclude={"target_metric"}) == context.model_dump(exclude={"target_metric"})


def test_apply_context_event_does_not_mutate_input_context() -> None:
    context = _context()
    apply_context_event(context, "component_selected", "LV")

    assert context.component_id is None


def test_apply_context_event_rejects_unknown_event_type() -> None:
    import pytest

    context = _context()
    with pytest.raises(ValueError, match="unknown context event type"):
        apply_context_event(context, "totally_made_up_event", "x")  # type: ignore[arg-type]
