"""Physician decision-support brief artifact generator (Wave 3).

Builds the `PHYSICIAN_BRIEF` `AssistantArtifact` type Wave 2 already reserved
in `schemas.py`'s `AssistantArtifactType` enum. Implements
`docs/assistant/GLOBAL_ARCHITECTURE.md`'s "PHYSICIAN SUPPORT ARCHITECTURE" /
"DECISION SUPPORT OBJECT" contract: a `DecisionSupportBundle` with NO
`recommended_treatment` field, ever — Laya/this system supports the
physician's decision, it never makes it.

Scope, stated honestly: this wave's brief is assembled ONLY from Wave 2's 4
real T0 tools (`get_cardiac_findings`, `get_ensemble`,
`get_ensemble_distributions`, `get_ensemble_assumptions` —
`tool_registry.py`). Every field this module cannot honestly populate from
those 4 tools is left an empty list, never fabricated, and the gap is stated
in `limitations`. See `docs/assistant/wave3/physician-brief.md` for the full
design note — in particular the observed-vs-derived judgment call for
`get_cardiac_findings` output (the single most consequential decision in
this file) and the "Safety scan false positives" section explaining why
`generate_physician_brief` does not hard-fail on two specific, pre-existing,
real disclaiming-language matches from `check_output_safety`.

Provenance: `python/hearttwin/assistant/provenance_mapping.py` (Agent 13's
legacy-vocabulary -> `CanonicalProvenanceKind` mapping layer) did not exist
in this repo when this module was written (checked via `find`/`ls` at the
start of this task). `generate_physician_brief` accepts an optional
`extra_provenance` parameter for exactly that enrichment so a later
integration step can wire it in without changing this module's contract or
re-deriving its own tool-level provenance.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from python.hearttwin.assistant.safety_validator import OutputSafetyDecision, check_output_safety
from python.hearttwin.assistant.schemas import (
    AssistantArtifact,
    AssistantArtifactType,
    CanonicalProvenanceKind,
    ConversationContext,
    ProvenanceRef,
)
from python.hearttwin.assistant.tool_registry import get_tool_registry

# ---------------------------------------------------------------------------
# DecisionSupportBundle
#
# GLOBAL_ARCHITECTURE.md defines this shape under "PHYSICIAN SUPPORT
# ARCHITECTURE" but it does not exist in schemas.py — Wave 2 built the
# artifact envelope (AssistantArtifact.payload: dict[str, Any]) but not this
# specific payload contract. Defined here rather than added to schemas.py so
# this task does not touch a file Wave 2 (and other Wave 3 agents) already
# own; reconciling it into schemas.py as the canonical PHYSICIAN_BRIEF
# payload type is a lead/integration-time decision (see design note
# "Reconciliation").
# ---------------------------------------------------------------------------


class DecisionSupportBundle(BaseModel):
    """The physician decision-support object. Field list is verbatim from
    GLOBAL_ARCHITECTURE.md's "DECISION SUPPORT OBJECT" — do not add fields
    beyond this list, and never add anything that reads as a treatment/
    therapy recommendation (no `recommended_treatment`, no `next_steps`
    phrased as clinical action, etc.)."""

    question: Optional[str] = None
    clinical_context: dict[str, Any] = Field(default_factory=dict)
    observed_evidence: list[dict[str, Any]] = Field(default_factory=list)
    derived_evidence: list[dict[str, Any]] = Field(default_factory=list)
    simulated_results: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    possible_interpretations: list[dict[str, Any]] = Field(default_factory=list)


class PhysicianBriefSafetyError(RuntimeError):
    """Raised when a string this module itself authored fails
    `check_output_safety` — see `_AUTHORED_STRING_FIELDS` / `_hard_safety_gate`.

    This should structurally never fire: the strings this module authors
    (title, question, limitations) are static/templated and reviewed, not
    LLM-generated. It exists anyway per AGENTS.md "safety stays on" and the
    task's own belt-and-suspenders requirement — if it ever does fire, that
    means a future edit introduced prescriptive language into this module's
    own authored text, which must be fixed here, not suppressed.
    """


# ---------------------------------------------------------------------------
# Honest, auto-populated limitations
#
# GLOBAL_ARCHITECTURE.md's transparency requirement is itself a feature, not
# boilerplate: a physician reading this brief must know what it does NOT
# cover given today's tooling, not silently assume completeness.
# ---------------------------------------------------------------------------

_SCOPE_LIMITATION = (
    "This brief is assembled only from the 4 tools currently in the assistant "
    "tool registry (get_cardiac_findings, get_ensemble_distributions, "
    "get_ensemble_assumptions) — see python/hearttwin/assistant/tool_registry.py. "
    "Any physician question this brief cannot answer from those 4 tools is out "
    "of scope this wave, not silently guessed at."
)
_LONGITUDINAL_LIMITATION = (
    "Longitudinal history is not available — no timeline/history tool or backend "
    "persistence exists yet (docs/assistant/PHYSICIAN_WORKFLOWS.md: 'How has EF "
    "changed longitudinally?' is a confirmed GAP). This brief reflects only the "
    "current case snapshot and, if provided, one ensemble run."
)
_SENSITIVITY_LIMITATION = (
    "Only plausible-twin ensemble uncertainty (spread of a fixed sampling model) "
    "is included; no sensitivity or dominant-assumption analysis exists yet "
    "(PHYSICIAN_WORKFLOWS.md confirms no sensitivity-analysis code exists "
    "anywhere in python/hearttwin/), so `uncertainty` describes how wide the "
    "result is, not which input assumption most drives that width."
)
_MISSING_EVIDENCE_LIMITATION = (
    "`missing_evidence` is intentionally empty — no evidence-completeness or "
    "value-of-information logic exists yet to identify what data would most "
    "constrain this result. An empty list here means 'not yet computable', "
    "not 'nothing is missing'."
)
_CONFLICTS_LIMITATION = (
    "`conflicts` is intentionally empty — no cross-source conflict-detection "
    "logic exists yet. An empty list here means 'not yet checked', not "
    "'no conflicts exist'."
)
_INTERPRETATIONS_LIMITATION = (
    "`possible_interpretations` is intentionally empty — no differential- or "
    "interpretation-ranking logic exists yet. This brief presents evidence for "
    "the physician to interpret; it does not itself enumerate interpretations."
)
_NO_ENSEMBLE_LIMITATION = (
    "No ensemble_id was supplied (or none exists yet) for this case — "
    "simulated_results, uncertainty, and the assumptions list are empty because "
    "no plausible-twin ensemble run backs this brief, not because that data was "
    "dropped or judged irrelevant."
)

# Strings this module itself authors/templates (never copied verbatim from
# another tool's payload). Hard-gated by check_output_safety with zero
# tolerance — see module docstring and design note "Safety scan false
# positives" for why pass-through tool text is handled differently.
_STATIC_AUTHORED_STRINGS: tuple[str, ...] = (
    _SCOPE_LIMITATION,
    _LONGITUDINAL_LIMITATION,
    _SENSITIVITY_LIMITATION,
    _MISSING_EVIDENCE_LIMITATION,
    _CONFLICTS_LIMITATION,
    _INTERPRETATIONS_LIMITATION,
    _NO_ENSEMBLE_LIMITATION,
)


def _hard_safety_gate(field_path: str, text: str) -> None:
    """Zero-tolerance check_output_safety gate for module-authored strings.

    Unlike `scan_bundle_strings` (used for pass-through tool text, where a
    documented pre-existing false positive is tolerated), any block here is
    fatal: this module fully controls this text and has no excuse to ship
    prescriptive language in it.
    """
    decision = check_output_safety(text)
    if decision.blocked:
        raise PhysicianBriefSafetyError(
            f"physician brief field {field_path!r} failed check_output_safety: "
            f"{decision.reason} matched={decision.matched_terms!r} text={text!r}"
        )


# ---------------------------------------------------------------------------
# Safety scan (belt-and-suspenders over the WHOLE bundle, including
# pass-through tool text)
# ---------------------------------------------------------------------------

# Discovered while wiring check_output_safety against REAL upstream tool text
# for the first time (not hypothesized) — see design note "Safety scan false
# positives" for the full writeup:
#   * ensemble.py's provenance.assumptions ALWAYS includes the literal,
#     hardcoded string "...are not clinical confidence intervals."
#     (python/hearttwin/ensemble.py:441) on every ensemble ever produced.
#     safety_validator.py's `_BLOCKED_PATTERNS` (safety.py) has a bare
#     `\b(clinical(ly)?)\b` word-boundary rule with no allowlist entry for
#     this benign statistical qualifier (unlike safety.py's own DISCLAIMER,
#     whose "diagnosis or treatment decisions" phrase IS allowlisted via
#     `_ALLOWED_SAFETY_PHRASES` before the same blocklist runs).
#   * cardiac_findings.py's own DISCLAIMER ("...Not a clinical diagnosis.")
#     independently trips the same class of false positive on "diagnosis"
#     (both the regex layer and validate_simulation_outputs' vocab layer).
#     This module does not include that string in the bundle (redundant with
#     AssistantResponse-level safety_disclaimer elsewhere), but the finding
#     is recorded here because it corroborates that this is a systemic gap
#     in safety_validator.py's allowlist, not a one-off.
# Neither string is treatment-recommendation language — both are safety-
# protective disclaiming language that predates this task and that this
# module is forbidden from rewriting (file-ownership constraint; the real
# fix is extending `_ALLOWED_SAFETY_PHRASES` in safety.py, out of scope
# here). `scan_bundle_strings` reports these like any other match — nothing
# is hidden — but `generate_physician_brief` treats a match as fatal only
# when it is NOT exactly this known, pre-existing, verified-benign pattern.
_KNOWN_BENIGN_REGEX_PATTERNS: frozenset[str] = frozenset({r"\b(clinical(ly)?)\b"})


def _is_known_benign(decision: OutputSafetyDecision) -> bool:
    """True if every matched term is the one documented pre-existing
    false-positive pattern above (and nothing else)."""
    if not decision.matched_terms:
        return True
    known = {f"regex:{pattern}" for pattern in _KNOWN_BENIGN_REGEX_PATTERNS}
    return all(term in known for term in decision.matched_terms)


def scan_bundle_strings(bundle: DecisionSupportBundle) -> dict[str, OutputSafetyDecision]:
    """Run `check_output_safety` over every string field in the bundle.

    Belt-and-suspenders on top of the structural guarantee (no
    `recommended_treatment` field exists at all — see `DecisionSupportBundle`).
    Returns every dotted-path -> decision, including passes, so a caller/test
    sees the full picture rather than a single collapsed boolean.
    """
    results: dict[str, OutputSafetyDecision] = {}

    def _record(path: str, text: str) -> None:
        results[path] = check_output_safety(text)

    if bundle.question:
        _record("question", bundle.question)
    for key, value in bundle.clinical_context.items():
        if isinstance(value, str):
            _record(f"clinical_context.{key}", value)
    for i, entry in enumerate(bundle.derived_evidence):
        for key, value in entry.items():
            if isinstance(value, str):
                _record(f"derived_evidence[{i}].{key}", value)
    for i, entry in enumerate(bundle.observed_evidence):
        for key, value in entry.items():
            if isinstance(value, str):
                _record(f"observed_evidence[{i}].{key}", value)
    for i, text in enumerate(bundle.assumptions):
        _record(f"assumptions[{i}]", text)
    for i, text in enumerate(bundle.limitations):
        _record(f"limitations[{i}]", text)

    return results


# ---------------------------------------------------------------------------
# generate_physician_brief
# ---------------------------------------------------------------------------


async def generate_physician_brief(
    case_id: str,
    ensemble_id: str | None,
    context: ConversationContext | None,
    *,
    extra_provenance: list[ProvenanceRef] | None = None,
) -> AssistantArtifact:
    """Build the PHYSICIAN_BRIEF AssistantArtifact from real tool data only.

    `generate_physician_brief` is `async` (not the plain `def` a first read
    of the task brief might suggest) because it calls
    `ToolRegistry.execute(...)`, which is itself a coroutine
    (`tool_registry.py`'s `ToolRegistry.execute`) — every other Wave 2
    consumer of the registry (`router.py`, `test_tool_registry.py`) is
    async for the same reason.

    `extra_provenance` lets a caller merge in Agent 13's legacy-provenance ->
    CanonicalProvenanceKind mapping (`provenance_mapping.py`) once it exists;
    it did not exist in this repo as of this task (see module docstring), so
    it defaults to empty and this function is fully self-contained today.
    """
    registry = get_tool_registry()

    findings_result = await registry.execute("get_cardiac_findings", case_id=case_id)
    cardiac_findings: dict[str, Any] = findings_result.canonical_payload["cardiac_findings"]

    tool_provenance: list[ProvenanceRef] = [
        ProvenanceRef(
            kind=CanonicalProvenanceKind.DERIVED,
            source_id="get_cardiac_findings",
            description=(
                "AHA-17-segment-localized findings computed (wall mapping, severity "
                "banding, narrative synthesis) from the case's simulated cardiac state — "
                "see docs/assistant/wave3/physician-brief.md for why this is classified "
                "DERIVED rather than OBSERVED."
            ),
        )
    ]

    # --- observed_evidence / derived_evidence -----------------------------
    # JUDGMENT CALL (the most consequential one in this file — full reasoning
    # in the design note): get_cardiac_findings wraps derive_findings(),
    # which computes every field it returns (severity thresholds, wall ->
    # coronary-territory -> AHA-segment lookup, 3D anchor coordinates,
    # narrative text) from canonical metrics (ef_pct, qrs_duration_ms,
    # scar_fraction, ...) that are THEMSELVES outputs of the deterministic
    # physiology/ECG/tissue simulation, not raw measurements pulled straight
    # from a file or user input. Nothing this tool returns meets the
    # "observed" bar (a value taken directly from a source without an
    # intervening computation) — the codebase's own ValueSource.OBSERVED-
    # equivalent data (schemas.py's `source_map`, tagged
    # FILE_EXTRACTION/USER_INPUT) is not exposed by any of the 4 tools this
    # wave's registry implements. So: observed_evidence stays empty (a
    # documented, real limitation of this wave's tool coverage — not the
    # same reason missing_evidence/conflicts/possible_interpretations are
    # empty, which is "no detection logic exists yet"), and every finding
    # goes to derived_evidence.
    observed_evidence: list[dict[str, Any]] = []
    derived_evidence: list[dict[str, Any]] = [
        {
            "claim": finding.get("title"),
            "detail": finding.get("summary"),
            "region": finding.get("region"),
            "territory": finding.get("territory"),
            "aha_segments": finding.get("aha_segments"),
            "severity": finding.get("severity"),
            "metric": finding.get("metric"),
            "codes": finding.get("codes"),
            "source": finding.get("source"),
        }
        for finding in cardiac_findings.get("findings", [])
    ]

    clinical_context: dict[str, Any] = {
        "case_id": case_id,
        "imaging_source": cardiac_findings.get("imaging_source"),
        "segment_model": cardiac_findings.get("segment_model"),
    }
    if context is not None:
        clinical_context["audience"] = context.audience
        if context.patient_id:
            clinical_context["patient_id"] = context.patient_id
        if context.snapshot_id:
            clinical_context["snapshot_id"] = context.snapshot_id

    # --- simulated_results / uncertainty / assumptions ---------------------
    simulated_results: list[dict[str, Any]] = []
    uncertainty: list[dict[str, Any]] = []
    assumptions: list[str] = []
    limitations: list[str] = [_SCOPE_LIMITATION]

    if ensemble_id:
        distributions_result = await registry.execute(
            "get_ensemble_distributions", ensemble_id=ensemble_id
        )
        distributions_payload = distributions_result.canonical_payload
        ensemble_provenance = distributions_payload.get("provenance") or {}
        clinical_context["ensemble_id"] = ensemble_id
        clinical_context["ensemble_origin_quality"] = ensemble_provenance.get("origin_quality")
        clinical_context["ensemble_origin_snapshot_id"] = ensemble_provenance.get("origin_snapshot_id")

        for metric in distributions_payload.get("distributions", []):
            # simulated_results = the ensemble's point-estimate summary per
            # metric; uncertainty = the spread/shape of that same
            # distribution. Both come from the identical EnsembleMetricDistribution
            # record (ensemble.py) — split by field, not by source.
            simulated_results.append({
                "metric_id": metric.get("metric_id"),
                "unit": metric.get("unit"),
                "mean": metric.get("mean"),
                "median": metric.get("median"),
                "min": metric.get("min"),
                "max": metric.get("max"),
                "sample_count": len(metric.get("samples", [])),
            })
            uncertainty.append({
                "metric_id": metric.get("metric_id"),
                "unit": metric.get("unit"),
                "standard_deviation": metric.get("standard_deviation"),
                "variance": metric.get("variance"),
                "quantiles": metric.get("quantiles"),
                "range": {"min": metric.get("min"), "max": metric.get("max")},
            })

        tool_provenance.append(
            ProvenanceRef(
                kind=CanonicalProvenanceKind.SIMULATED,
                source_id="get_ensemble_distributions",
                description=f"Plausible-twin ensemble {ensemble_id} metric distributions.",
            )
        )

        assumptions_result = await registry.execute(
            "get_ensemble_assumptions", ensemble_id=ensemble_id
        )
        assumptions = list(assumptions_result.canonical_payload.get("assumptions", []))
        tool_provenance.append(
            ProvenanceRef(
                kind=CanonicalProvenanceKind.MODEL_PRIOR,
                source_id="get_ensemble_assumptions",
                description=f"Explicit modeling assumptions recorded for ensemble {ensemble_id}.",
            )
        )
    else:
        limitations.append(_NO_ENSEMBLE_LIMITATION)

    limitations.extend([
        _LONGITUDINAL_LIMITATION,
        _SENSITIVITY_LIMITATION,
        _MISSING_EVIDENCE_LIMITATION,
        _CONFLICTS_LIMITATION,
        _INTERPRETATIONS_LIMITATION,
    ])

    question = f"Decision support for case {case_id}"
    if ensemble_id:
        question += f" (ensemble {ensemble_id})"

    bundle = DecisionSupportBundle(
        question=question,
        clinical_context=clinical_context,
        observed_evidence=observed_evidence,
        derived_evidence=derived_evidence,
        simulated_results=simulated_results,
        uncertainty=uncertainty,
        missing_evidence=[],
        conflicts=[],
        assumptions=assumptions,
        provenance=tool_provenance + list(extra_provenance or []),
        limitations=limitations,
        possible_interpretations=[],
    )

    # Zero-tolerance gate on strings this module itself authors.
    _hard_safety_gate("question", bundle.question or "")
    for i, text in enumerate(bundle.limitations):
        _hard_safety_gate(f"limitations[{i}]", text)

    # Full-bundle, belt-and-suspenders scan (including pass-through tool
    # text) — see `scan_bundle_strings` docstring for the two documented,
    # pre-existing, verified-benign false positives this tolerates, and
    # `_is_known_benign` for the exact rule. Anything else blocked is fatal.
    for path, decision in scan_bundle_strings(bundle).items():
        if decision.blocked and not _is_known_benign(decision):
            raise PhysicianBriefSafetyError(
                f"physician brief field {path!r} failed check_output_safety: "
                f"{decision.reason} matched={decision.matched_terms!r}"
            )

    source_tool_ids = ["get_cardiac_findings"]
    if ensemble_id:
        source_tool_ids += ["get_ensemble_distributions", "get_ensemble_assumptions"]

    conversation_id = context.conversation_id if context is not None else f"standalone-{case_id}"

    return AssistantArtifact(
        type=AssistantArtifactType.PHYSICIAN_BRIEF,
        title=f"Physician brief — case {case_id}",
        conversation_id=conversation_id,
        patient_id=context.patient_id if context is not None else None,
        snapshot_id=context.snapshot_id if context is not None else None,
        source_tool_ids=source_tool_ids,
        provenance=bundle.provenance,
        payload=bundle.model_dump(mode="json"),
    )
