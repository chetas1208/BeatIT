"""Legacy-provenance-vocabulary -> CanonicalProvenanceKind mapping layer (Wave 3).

WAVE_2_HANDOFF.md ("Architecture decisions" + "Next-wave dependencies" #1)
deferred unifying BeatIT's 4 independent provenance vocabularies (documented
in docs/assistant/PHYSICIAN_WORKFLOWS.md "Existing Evidence/Provenance
Model") into `assistant.schemas.CanonicalProvenanceKind`. This module is that
mapping layer.

Verified before writing a single mapping (see docs/assistant/wave3/
provenance-mapping.md for the full audit): of the 4 named vocabularies, only
ONE has a real Python-side type today:

  - backend `ValueSource` (python/hearttwin/schemas.py) -- REAL, Python, 4
    members. Mapped below (`map_value_source_to_canonical`).
  - frontend `EvidenceKind` (web/lib/heart/contracts, TS) -- TypeScript only.
    No Python definition exists anywhere under python/hearttwin/ (grep
    confirmed zero hits outside this file's own docstring/comments). NOT
    mapped here -- mapping a type that doesn't exist server-side would be
    fabricating a contract, not unifying a real one.
  - timeline `TwinEventSource` (web/lib/twin/ensemble/inspectorModel.ts, TS)
    -- same situation: TypeScript only, zero Python hits. NOT mapped.
  - causal `CausalSourceKind` (web/lib/twin/scenario/causal.ts, TS) -- same
    situation: TypeScript only, zero Python hits. NOT mapped.

Two more genuinely real, Python-side, closed vocabularies turned up while
reading `ensemble.py` for the "whatever else is provenance-shaped" part of
this wave's brief, and are mapped here too even though they aren't named in
the original list of 4:

  - `EnsembleProvenance.origin_quality` (python/hearttwin/ensemble.py) is a
    closed 4-value Literal, not an Enum class, but it is exhaustive and
    real -- mapped below (`map_origin_quality_to_canonical`).
  - `EnsembleProvenance.assumptions` is free text (not a vocabulary), so it
    is not "mapped" in the enum sense -- see `get_provenance_for_ensemble`
    for how it's turned into ProvenanceRefs directly.

Every mapping function is exhaustive and raises on an unrecognized input
(AGENTS.md: "future vocabulary growth [must not] silently misclassify") --
no `.get(x, DEFAULT)` anywhere in this file.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from python.hearttwin.assistant.schemas import CanonicalProvenanceKind, ProvenanceRef
from python.hearttwin.schemas import CaseRecord, ValueSource
from python.hearttwin.storage.ensemble_store import EnsembleStoreError, create_ensemble_store
from python.hearttwin.tools.cardiac_findings import derive_findings
from python.hearttwin.tools.storage import get_case

__all__ = [
    "UnmappedProvenanceValueError",
    "map_value_source_to_canonical",
    "map_origin_quality_to_canonical",
    "build_provenance_ref",
    "get_provenance_for_ensemble",
    "get_provenance_for_cardiac_findings",
]


class UnmappedProvenanceValueError(ValueError):
    """Raised when a legacy provenance value has no canonical mapping.

    Deliberately its own type (not a bare ValueError) so callers can
    distinguish "this vocabulary grew and nobody updated the mapping" from an
    ordinary bad-input ValueError.
    """


# ---------------------------------------------------------------------------
# backend ValueSource -> CanonicalProvenanceKind
#
# schemas.py:72-76. FILE_EXTRACTION means a value was pulled from an
# uploaded clinical file/image (real-world data, not computed) -> OBSERVED.
# USER_INPUT is exactly USER_ASSERTED. DEFAULT_MODEL_PRIOR is exactly
# MODEL_PRIOR. DERIVED is exactly DERIVED. Nothing in this 4-member enum
# means "simulated" or "external reference" -- see PHYSICIAN_WORKFLOWS.md's
# note that the backend has no "simulated" source today.
# ---------------------------------------------------------------------------

_VALUE_SOURCE_TO_CANONICAL: dict[ValueSource, CanonicalProvenanceKind] = {
    ValueSource.FILE_EXTRACTION: CanonicalProvenanceKind.OBSERVED,
    ValueSource.USER_INPUT: CanonicalProvenanceKind.USER_ASSERTED,
    ValueSource.DEFAULT_MODEL_PRIOR: CanonicalProvenanceKind.MODEL_PRIOR,
    ValueSource.DERIVED: CanonicalProvenanceKind.DERIVED,
}


def map_value_source_to_canonical(value: ValueSource) -> CanonicalProvenanceKind:
    """Map the backend's `ValueSource` (schemas.py) onto `CanonicalProvenanceKind`.

    Exhaustive over all 4 current members. Raises `UnmappedProvenanceValueError`
    (never silently defaults) if `ValueSource` grows a member this map hasn't
    been updated for.
    """
    try:
        return _VALUE_SOURCE_TO_CANONICAL[ValueSource(value)]
    except ValueError as exc:
        raise UnmappedProvenanceValueError(f"{value!r} is not a valid ValueSource") from exc


# ---------------------------------------------------------------------------
# EnsembleProvenance.origin_quality -> CanonicalProvenanceKind
#
# ensemble.py's closed Literal["observed", "derived", "interpolated",
# "synthetic"]. "interpolated" means computed between known points -- a
# derived value, not a raw observation, not a full simulation -> DERIVED.
# "synthetic" is ensemble.py's own word for non-real data (its module
# docstring: "never labels a simulation percentile as a clinical confidence
# interval") -> SIMULATED.
# ---------------------------------------------------------------------------

OriginQuality = Literal["observed", "derived", "interpolated", "synthetic"]

_ORIGIN_QUALITY_TO_CANONICAL: dict[str, CanonicalProvenanceKind] = {
    "observed": CanonicalProvenanceKind.OBSERVED,
    "derived": CanonicalProvenanceKind.DERIVED,
    "interpolated": CanonicalProvenanceKind.DERIVED,
    "synthetic": CanonicalProvenanceKind.SIMULATED,
}


def map_origin_quality_to_canonical(value: str) -> CanonicalProvenanceKind:
    """Map `EnsembleProvenance.origin_quality` (ensemble.py) onto `CanonicalProvenanceKind`.

    Not one of the campaign's originally-named "4 legacy vocabularies," but a
    real, closed, Python-side vocabulary found while auditing `ensemble.py`
    for provenance-shaped data -- mapped for the same reason: it's real,
    it's closed, and something will eventually need to cite it.
    """
    try:
        return _ORIGIN_QUALITY_TO_CANONICAL[value]
    except KeyError as exc:
        raise UnmappedProvenanceValueError(f"{value!r} is not a recognized origin_quality") from exc


# ---------------------------------------------------------------------------
# ProvenanceRef builder
# ---------------------------------------------------------------------------


def build_provenance_ref(
    source_module: str,
    source_kind: ValueSource | str,
    detail: str,
    *,
    source_id: str | None = None,
    confidence: float | None = None,
) -> ProvenanceRef:
    """Build a `ProvenanceRef` (assistant/schemas.py) from a legacy source value.

    `ProvenanceRef` already exists in `assistant/schemas.py` (Wave 2, Agent 6)
    -- reused as-is here, not redefined, per this wave's constraint not to
    touch schemas.py and not to fork a second provenance-ref shape.

    `source_module` + `detail` are folded into `description` rather than
    added as new ProvenanceRef fields, since ProvenanceRef is deliberately
    thin (schemas.py: "it never carries a second copy of the value itself")
    and adding fields would mean editing a file this wave may not touch.

    `source_kind` accepts either a real `ValueSource` member or the
    `origin_quality` string literal -- both real, Python-side, closed
    vocabularies mapped above.
    """
    if isinstance(source_kind, ValueSource):
        kind = map_value_source_to_canonical(source_kind)
    else:
        kind = map_origin_quality_to_canonical(source_kind)
    return ProvenanceRef(
        kind=kind,
        source_id=source_id,
        description=f"{source_module}: {detail}",
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# get_provenance_for_ensemble
#
# Pulls from the REAL EnsembleProvenance fields (ensemble.py:223-239):
#   - origin_quality (closed vocabulary, mapped above)
#   - assumptions (free text -- each entry is a genuine modeling-assumption
#     statement, closest canonical bucket is MODEL_PRIOR: an assumption is a
#     prior belief baked into how the model samples, not an observation, a
#     computed value, or a simulation result)
#   - evidence_ids (pointers to case evidence, not values themselves ->
#     EXTERNAL_REFERENCE, since from the ensemble's point of view an
#     evidence_id is a reference to evidence living elsewhere)
#
# origin_provenance (list[dict[str, Any]]) is deliberately NOT included:
# it's freeform dicts (ensemble.py only ever inspects an ad hoc "source" key
# for one validation check, `.get("source") == "synthetic_replay"`) rather
# than a closed, enumerable vocabulary -- mapping it would mean inventing a
# taxonomy for keys that don't exist as a real type anywhere in the
# codebase. See docs/assistant/wave3/provenance-mapping.md.
# ---------------------------------------------------------------------------


async def _load_ensemble_record(ensemble_id: str) -> dict[str, Any]:
    store = create_ensemble_store()
    try:
        result = await asyncio.to_thread(store.get, ensemble_id)
    except (EnsembleStoreError, OSError) as exc:
        raise RuntimeError("ensemble persistence is unavailable") from exc
    if result is None:
        raise RuntimeError(f"ensemble {ensemble_id!r} not found")
    return result


async def get_provenance_for_ensemble(ensemble_id: str) -> list[ProvenanceRef]:
    """Real provenance for a persisted ensemble, as canonical `ProvenanceRef`s.

    Plain importable function (not a `ToolRegistry` handler) so it can be
    called directly by Wave 2's `get_ensemble_assumptions` tool or by a later
    physician-brief builder -- per this wave's brief, deliberately not
    coupled to `tool_registry.py`.
    """
    record = await _load_ensemble_record(ensemble_id)
    provenance = record["provenance"]

    refs: list[ProvenanceRef] = [
        build_provenance_ref(
            "ensemble.py:EnsembleProvenance.origin_quality",
            provenance["origin_quality"],
            f"origin snapshot {provenance['origin_snapshot_id']!r} quality",
            source_id=provenance["origin_snapshot_id"],
        ),
    ]
    for assumption_text in provenance.get("assumptions", []):
        refs.append(ProvenanceRef(
            kind=CanonicalProvenanceKind.MODEL_PRIOR,
            source_id=ensemble_id,
            description=f"ensemble.py:EnsembleProvenance.assumptions: {assumption_text}",
            confidence=None,
        ))
    for evidence_id in provenance.get("evidence_ids", []):
        refs.append(ProvenanceRef(
            kind=CanonicalProvenanceKind.EXTERNAL_REFERENCE,
            source_id=evidence_id,
            description=f"ensemble.py:EnsembleProvenance.evidence_ids: {evidence_id}",
            confidence=None,
        ))
    return refs


# ---------------------------------------------------------------------------
# get_provenance_for_cardiac_findings
#
# derive_findings() (tools/cardiac_findings.py) tags each finding with a
# free-text `source` path (e.g. "visualization.summary.ef_pct",
# "state.tissue_state.damage_zone_location + scar_fraction",
# "ct_segmentation.vista3d") -- not a `ValueSource` member. Where that path
# names a field genuinely tracked in `CardiacTwinState.source_map`
# (schemas.py:232-260, itself real and carries a real `ValueSource` per
# entry), this looks the real entry up and maps its actual `source` through
# `map_value_source_to_canonical` -- the honest per-value provenance.
#
# Findings whose source path doesn't correspond to any source_map field
# (the visualization.* paths: ef_pct, qrs_duration_ms, qtc_ms) are outputs of
# the deterministic simulation pipeline itself, not raw source_map entries --
# they are classified DERIVED, consistent with AGENTS.md's "the deterministic
# physics core is sacred" (these are exactly the kind of computed-not-observed
# value that rule describes).
# ---------------------------------------------------------------------------


def _source_map_lookup(source_map: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["field"]: entry for entry in source_map if isinstance(entry, dict) and entry.get("field")}


def _finding_provenance_ref(finding: dict[str, Any], source_map_by_field: dict[str, dict[str, Any]]) -> ProvenanceRef:
    finding_source = str(finding.get("source", ""))
    # Longest matching field first: "tissue_state.damage_zone_location" must
    # win over a shorter false-positive substring before a shorter one would.
    matched_field = max(
        (field for field in source_map_by_field if field in finding_source),
        key=len,
        default=None,
    )
    if matched_field is not None:
        entry = source_map_by_field[matched_field]
        return build_provenance_ref(
            "tools/cardiac_findings.py:derive_findings (via CardiacTwinState.source_map)",
            ValueSource(entry["source"]),
            f"finding {finding.get('id')!r} traced to source_map field {matched_field!r}: {finding_source}",
            source_id=finding.get("id"),
            confidence=entry.get("confidence"),
        )
    # No source_map entry covers this finding's field -- it's a deterministic
    # simulation-pipeline output (visualization.* path), not a raw tracked
    # field, so it's DERIVED rather than left unclassified.
    return ProvenanceRef(
        kind=CanonicalProvenanceKind.DERIVED,
        source_id=finding.get("id"),
        description=f"tools/cardiac_findings.py:derive_findings: {finding_source} (deterministic pipeline output)",
        confidence=None,
    )


async def get_provenance_for_cardiac_findings(case_id: str) -> list[ProvenanceRef]:
    """Real provenance for a case's derived cardiac findings, as canonical `ProvenanceRef`s.

    Plain importable function, not coupled to `tool_registry.py` (same
    rationale as `get_provenance_for_ensemble`) -- usable by the existing
    `get_cardiac_findings` tool or a later physician-brief builder.
    """
    case_data = await get_case(case_id)
    if not case_data:
        raise RuntimeError(f"case {case_id!r} not found")
    case = CaseRecord(**case_data)
    if case.state is None:
        raise RuntimeError(f"case {case_id!r} has no simulated state yet")

    state_dump = case.state.model_dump(mode="json")
    findings = derive_findings(state_dump, case.simulation_result)["findings"]
    source_map_by_field = _source_map_lookup(state_dump.get("source_map") or [])
    return [_finding_provenance_ref(finding, source_map_by_field) for finding in findings]
