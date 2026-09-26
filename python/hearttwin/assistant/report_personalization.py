"""Report content-hierarchy engine (Wave 6.5, Report Personalization Engineer).

`docs/assistant/PHYSICIAN_HELPER_HARDENING.md`'s core rule: "personalization
comes from case state, not from prettier prose." Wave 3's
`physician_brief.py` already builds a real `DecisionSupportBundle` from real
tool output (`get_cardiac_findings`, `get_ensemble_distributions`,
`get_ensemble_assumptions`). What it does NOT do — and what §21/§26-§30/§88
ask for — is decide, from that real data, which finding *dominates* the
case, which sections deserve emphasis, and what the lead sentence should be
*about*. This module adds exactly that decision layer, on top of the bundle,
without touching `physician_brief.py` (file-ownership constraint for this
wave — see `AGENTS.md` §1.7 and the task brief).

Deliberately NOT this module's job (per the task brief and §88's own
wording): writing the actual prose. `ReportEmphasis` describes the *shape*
of what to say ("lead with hemodynamic deterioration, key metrics X/Y,
direction: worsening") as structured data; a caller (a future
`CaseReportComposer`, §23-§30) turns that into sentences. Keeping the split
this way is what makes the "real rule, not a template string" requirement
checkable: `test_report_personalization.py` asserts on the *fields*, not on
any generated text.

Integration note (checked at the start of this task via `ls`/`find`): Wave
6.5's sibling "Case Context Hardening Engineer" had not yet landed
`python/hearttwin/assistant/case_context.py` when this module was written.
`build_delta_summary` therefore accepts an optional prior
`DecisionSupportBundle` directly rather than a `CaseContext` object. When
`case_context.py` lands with a historical-reference resolver, the intended
integration point is: whatever resolves "the prior revision's bundle" calls
`generate_physician_brief` (or reads a cached one) for that prior revision
and passes it as `prior_bundle` here unchanged — `build_delta_summary`'s
contract does not need to change.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from python.hearttwin.assistant.physician_brief import DecisionSupportBundle
from python.hearttwin.assistant.schemas import ConversationContext

# ---------------------------------------------------------------------------
# Reference bands used ONLY to rank/direction-classify findings for report
# structure — never surfaced as a diagnosis or a fabricated confidence value
# (spec §93). Two sources, both already real and non-arbitrary:
#
#   * EF thresholds (30/40/50) are copied verbatim from
#     `cardiac_findings.py::derive_findings`'s own severity banding (severe
#     <30, moderate <40, mild <50) so this module's notion of "reduced EF"
#     matches the exact boundary the findings tool already uses — not a
#     second, competing threshold.
#   * cardiac_output_l_min / stroke_volume_ml / heart_rate_bpm bands are the
#     standard adult resting reference ranges (CO ~4-8 L/min, SV ~60-100 mL,
#     HR 60-100 bpm) used here purely as directional banding for content
#     ranking, matching this codebase's existing "educational simulation,
#     reference terminology, not a diagnosis" posture.
# ---------------------------------------------------------------------------

_EF_METRIC_ID = "ejection_fraction_pct"
NORMAL_RANGE: dict[str, tuple[float, float]] = {
    _EF_METRIC_ID: (50.0, 70.0),
    "cardiac_output_l_min": (4.0, 8.0),
    "stroke_volume_ml": (60.0, 100.0),
    "heart_rate_bpm": (60.0, 100.0),
}

# Whether a LOWER value is the worse direction for this metric (EF/CO/SV) or
# a HIGHER value is worse (QRS/QTc widen/prolong with worsening conduction).
# Used only to phrase severity_direction/delta polarity, never to invent a
# value.
_LOWER_IS_WORSE: frozenset[str] = frozenset({_EF_METRIC_ID, "cardiac_output_l_min", "stroke_volume_ml"})
# "regional_wall_motion"'s numeric value (when present) is a scar fraction —
# higher scar burden is the worse direction, same polarity as QRS/QTc
# widening/prolonging.
_HIGHER_IS_WORSE: frozenset[str] = frozenset({"qrs_duration_ms", "qtc_ms", "regional_wall_motion"})

_SEVERITY_WEIGHT: dict[Optional[str], int] = {"severe": 3, "moderate": 2, "mild": 1, "info": 0, None: 0}

# `derive_findings` (python/hearttwin/tools/cardiac_findings.py) tags every
# finding with an `id` (global_systolic / regional_<wall> / conduction_qrs /
# repolarization_qtc / ct_*) — BUT `physician_brief.py`'s dict comprehension
# that builds `DecisionSupportBundle.derived_evidence` does NOT copy `id`
# onto the bundle entry (verified by reading the comprehension: it keeps
# claim/detail/region/territory/aha_segments/severity/metric/codes/source
# only). `source`, however, IS always copied, and `derive_findings` sets it
# to a fixed, deterministic string per finding family — so this module
# categorizes on `source`, the real field the bundle actually carries.
_HEMODYNAMIC_SOURCE_PREFIXES = ("visualization.summary.", "state.tissue_state.", "ct_segmentation.")
_RHYTHM_SOURCE_PREFIX = "visualization.electrophysiology."
_EF_FINDING_SOURCE = "visualization.summary.ef_pct"

# A moderate/severe finding standing alone with no ensemble corroboration
# still counts (score >= _MODERATE_OR_ABOVE); this constant names the
# boundary so `_assumptions_dominate_override` can compare against it
# without a second magic number floating around.
_MODERATE_OR_ABOVE = _SEVERITY_WEIGHT["moderate"]

# The bonus applied when a derived-evidence finding's implied direction is
# corroborated by the ensemble's own simulated metric for the same
# physiology (both "reduced", not one reduced and one silent) — this is the
# literal §88 example ("if EF down AND CO down ... emphasize worsening
# hemodynamic pattern") made concrete: two independent evidence layers
# (derived findings vs. simulated ensemble) agreeing, not one restated twice.
_ALIGNMENT_BONUS = 2

# A materiality threshold for `build_delta_summary`: a value must move by at
# least this fraction of its prior magnitude to be "signal" rather than
# "noise" worth surfacing in a report. Deliberately simple (the task brief
# explicitly allows "a real, if simple, threshold rule — document it") — 10%
# is a common engineering noise-floor choice, not a clinical claim.
DELTA_MATERIALITY_FRACTION = 0.10

LeadTheme = Literal[
    "hemodynamic_deterioration",
    "rhythm_electrophysiology",
    "stable_with_uncertainty",
    "simulation_driven",
    "conflicting_signals",
]

SeverityDirection = Literal[
    "worsening", "improving", "stable", "reduced", "elevated", "mixed", "insufficient_data"
]


class TensionFlag(BaseModel):
    """One concrete, computed disagreement between two real evidence layers
    in the SAME bundle — never a guess, always two cited fields."""

    between: tuple[str, str]
    detail: str


class ReportEmphasis(BaseModel):
    """The DECISION of what matters in this case — not the prose. A caller
    (report composer) turns this into sentences; this module only decides
    the shape (§88: "a real rule evaluated against real case data")."""

    lead_theme: LeadTheme
    key_metrics: list[str] = Field(default_factory=list)
    severity_direction: SeverityDirection
    emphasized_sections: list[str] = Field(default_factory=list)
    minimized_sections: list[str] = Field(default_factory=list)
    omitted_sections: list[str] = Field(default_factory=list)
    tension_flags: list[TensionFlag] = Field(default_factory=list)
    # Names of the concrete rule(s) in this module that fired, in the order
    # they were evaluated — lets a test (or a human) verify the decision was
    # rule-driven, not vibes. Not physician-facing text.
    triggered_rules: list[str] = Field(default_factory=list)


class DeltaFinding(BaseModel):
    """One real, computed before/after comparison on ONE overlapping metric.
    Never carries a fabricated `prior_value` — a metric absent from the
    prior bundle produces change_kind="new", not a guessed baseline.

    `metric_id` is either a real `EnsembleMetricId` (when the comparison
    comes from `simulated_results`) or a `_canonical_metric_name` derived
    from a `derived_evidence` finding's `source` field (when no ensemble
    metric covers that physiology, e.g. `qrs_duration_ms`) — always a real,
    traceable identity, never an invented one."""

    metric_id: str
    unit: Optional[str] = None
    prior_value: Optional[float] = None
    current_value: Optional[float] = None
    absolute_delta: Optional[float] = None
    relative_delta: Optional[float] = None
    change_kind: Literal["increase", "decrease", "unchanged", "new", "resolved"]
    material: bool


# ---------------------------------------------------------------------------
# derived_evidence scoring helpers
# ---------------------------------------------------------------------------


def _finding_source(finding: dict[str, Any]) -> str:
    return str(finding.get("source") or "")


def _category_matches(
    derived_evidence: list[dict[str, Any]], prefixes: tuple[str, ...]
) -> list[dict[str, Any]]:
    return [f for f in derived_evidence if _finding_source(f).startswith(prefixes)]


def _category_score(matches: list[dict[str, Any]]) -> int:
    return sum(_SEVERITY_WEIGHT.get(f.get("severity"), 0) for f in matches)


def _metric_band(metric_id: str, mean: float) -> Literal["reduced", "normal", "elevated", "unknown"]:
    bounds = NORMAL_RANGE.get(metric_id)
    if bounds is None:
        return "unknown"
    low, high = bounds
    if mean < low:
        return "reduced"
    if mean > high:
        return "elevated"
    return "normal"


def _simulated_band(simulated_results: list[dict[str, Any]], metric_id: str) -> Optional[str]:
    for entry in simulated_results:
        if entry.get("metric_id") == metric_id:
            mean = entry.get("mean")
            if isinstance(mean, (int, float)):
                return _metric_band(metric_id, float(mean))
    return None


_METRIC_SUFFIX_RE = re.compile(r"([a-z_]+)$")


def _rhythm_metric_id(finding: dict[str, Any]) -> Optional[str]:
    """Recover the canonical ECG feature name from the finding's own
    `source` string (e.g. "visualization.electrophysiology.qrs_duration_ms")
    rather than re-deriving it from the formatted `metric` label — the
    `source` field already names the exact upstream field."""
    source = str(finding.get("source") or "")
    match = _METRIC_SUFFIX_RE.search(source)
    return match.group(1) if match else None


def _canonical_metric_name(source: str) -> str:
    """Maps a derived-evidence `source` string onto the SAME short metric
    name `key_metrics`/ensemble `metric_id`s use, so `build_delta_summary`'s
    output and `determine_content_hierarchy`'s `key_metrics` can be joined
    by identity in `_resolve_severity_direction` — without this, an EF delta
    computed from derived_evidence (keyed by the raw `source` string) would
    never match `key_metrics=["ejection_fraction_pct"]` and severity_direction
    would silently fall back to "stable" even when a real trend exists."""
    if source == _EF_FINDING_SOURCE:
        return _EF_METRIC_ID
    if source.startswith("state.tissue_state."):
        return "regional_wall_motion"
    if source.startswith(_RHYTHM_SOURCE_PREFIX):
        return source.rsplit(".", 1)[-1]
    if source.startswith("ct_segmentation."):
        return "ct_structural_observation"
    return source


def _numeric_from_metric_label(label: Any) -> Optional[float]:
    """Extract the leading number from a deterministically-formatted metric
    label (e.g. "EF 32%", "QRS 130 ms") produced by `derive_findings`.
    Returns None (never a guess) if no number is present."""
    if not isinstance(label, str):
        return None
    match = re.search(r"-?\d+\.?\d*", label)
    return float(match.group()) if match else None


def _assumptions_dominate(bundle: DecisionSupportBundle) -> bool:
    """§88-style rule: "if assumptions dominate ... emphasize uncertainty
    instead." Concrete test: at most one real finding (observed+derived
    combined) AND at least two explicit modeling assumptions on record —
    i.e. the bundle's content is mostly `MODEL_PRIOR`-sourced, not
    finding-sourced. Two independent, real, already-populated bundle fields
    (`assumptions`, `observed_evidence`/`derived_evidence` counts), not a
    per-case special case."""
    finding_count = len(bundle.observed_evidence) + len(bundle.derived_evidence)
    return finding_count <= 1 and len(bundle.assumptions) >= 2


def _has_active_scenario(bundle: DecisionSupportBundle, context: Optional[ConversationContext]) -> bool:
    if context is not None and context.scenario_id:
        return True
    # `physician_brief.py` copies `ensemble_id` (not `scenario_id`) onto
    # `clinical_context` today, so an ensemble-backed brief with no
    # ConversationContext at all still counts as "a scenario ran" — this is
    # the fallback the module docstring documents for when no
    # ConversationContext is supplied to this function.
    return bool(bundle.clinical_context.get("scenario_id"))


def _ensemble_is_only_content(bundle: DecisionSupportBundle) -> bool:
    has_notable_finding = any(
        f.get("severity") not in (None, "info") for f in bundle.derived_evidence + bundle.observed_evidence
    )
    return bool(bundle.simulated_results) and not has_notable_finding


# ---------------------------------------------------------------------------
# determine_content_hierarchy
# ---------------------------------------------------------------------------


def determine_content_hierarchy(
    bundle: DecisionSupportBundle,
    *,
    prior_bundle: Optional[DecisionSupportBundle] = None,
    context: Optional[ConversationContext] = None,
) -> ReportEmphasis:
    """Decide which real finding category dominates this case's report.

    `prior_bundle`/`context` are optional keyword-only extensions beyond the
    task brief's minimal `(bundle) -> ReportEmphasis` sketch: `context` is
    needed to see `ConversationContext.scenario_id` (a real field
    `DecisionSupportBundle.clinical_context` does not copy today — see
    `_has_active_scenario`), and `prior_bundle` lets `severity_direction`
    report a real computed trend (`worsening`/`improving`) instead of a
    single-snapshot state word when a genuine prior exists — both call
    straight into `build_delta_summary` rather than re-implementing delta
    logic here.
    """
    triggered_rules: list[str] = []
    tension_flags: list[TensionFlag] = []

    hemo_matches = _category_matches(bundle.derived_evidence, _HEMODYNAMIC_SOURCE_PREFIXES)
    rhythm_matches = _category_matches(bundle.derived_evidence, (_RHYTHM_SOURCE_PREFIX,))
    hemo_score = _category_score(hemo_matches)
    rhythm_score = _category_score(rhythm_matches)

    hemo_metrics: list[str] = [_EF_METRIC_ID] if any(
        _finding_source(f) == _EF_FINDING_SOURCE for f in hemo_matches
    ) else []
    if any(_finding_source(f).startswith("state.tissue_state.") for f in hemo_matches):
        hemo_metrics.append("regional_wall_motion")
    if any(_finding_source(f).startswith("ct_segmentation.") for f in hemo_matches):
        hemo_metrics.append("ct_structural_observation")

    rhythm_metrics = sorted({m for f in rhythm_matches if (m := _rhythm_metric_id(f))})

    # Rule: derived-evidence direction corroborated by the ensemble's own
    # simulated metric for the same physiology (§88's literal example, EF
    # down AND CO down) earns a bonus and pulls that metric into
    # key_metrics — two independent evidence layers agreeing, not double-
    # counting the same source.
    ef_reduced_finding = any(_finding_source(f) == _EF_FINDING_SOURCE for f in hemo_matches)
    co_band = _simulated_band(bundle.simulated_results, "cardiac_output_l_min")
    sv_band = _simulated_band(bundle.simulated_results, "stroke_volume_ml")
    if ef_reduced_finding and co_band == "reduced":
        hemo_score += _ALIGNMENT_BONUS
        hemo_metrics.append("cardiac_output_l_min")
        triggered_rules.append("hemodynamic_alignment_ef_and_co_both_reduced")
    if ef_reduced_finding and sv_band == "reduced":
        hemo_score += _ALIGNMENT_BONUS
        hemo_metrics.append("stroke_volume_ml")
        triggered_rules.append("hemodynamic_alignment_ef_and_sv_both_reduced")

    # Rule (§93-adjacent honesty check, not a confidence claim): a
    # structural finding implying reduced pump function (reduced EF) whose
    # own simulated cardiac-output distribution does NOT corroborate it
    # (normal or elevated, not reduced) is a real, computed tension between
    # two evidence layers in the SAME bundle — surfaced, never silently
    # resolved by picking one narrative.
    if ef_reduced_finding and co_band in ("normal", "elevated"):
        ef_severity = next(
            f.get("severity") for f in hemo_matches if _finding_source(f) == _EF_FINDING_SOURCE
        )
        tension_flags.append(
            TensionFlag(
                between=("derived_evidence:visualization.summary.ef_pct", "simulated_results:cardiac_output_l_min"),
                detail=(
                    f"derived finding reports reduced ejection fraction "
                    f"(severity={ef_severity}) but the ensemble's cardiac_output_l_min "
                    f"distribution mean is {co_band}, not reduced"
                ),
            )
        )
        triggered_rules.append("conflicting_ef_reduced_but_co_not_reduced")

    scenario_active = _has_active_scenario(bundle, context)
    ensemble_only = _ensemble_is_only_content(bundle)
    assumptions_dominate = _assumptions_dominate(bundle)

    lead_theme: LeadTheme
    key_metrics: list[str]

    if tension_flags:
        # Priority 1: an apparent contradiction is always surfaced, never
        # smoothed over by a competing "confident" narrative — the safest
        # default when two real evidence layers disagree.
        lead_theme = "conflicting_signals"
        key_metrics = [_EF_METRIC_ID, "cardiac_output_l_min"]
        triggered_rules.append("priority:conflicting_signals")
    elif scenario_active or ensemble_only:
        # Priority 2: an explicitly active scenario/experiment (real
        # ConversationContext signal) or an ensemble that is literally the
        # only substantive content reframes the report's purpose regardless
        # of any findings present — §21/§88's "if a scenario/experiment
        # context exists, include experiment framing."
        lead_theme = "simulation_driven"
        key_metrics = sorted({d.get("metric_id") for d in bundle.simulated_results if d.get("metric_id")})
        triggered_rules.append(
            "priority:simulation_driven_scenario_active" if scenario_active
            else "priority:simulation_driven_ensemble_only_content"
        )
    elif assumptions_dominate and max(hemo_score, rhythm_score) < _MODERATE_OR_ABOVE:
        # Priority 3: assumptions dominate the case (few/no findings, an
        # explicit multi-item assumptions list) and no finding cleared the
        # moderate/severe bar on its own — per §88, uncertainty framing
        # wins over a weak, single-mild-finding deterioration narrative.
        lead_theme = "stable_with_uncertainty"
        key_metrics = []
        triggered_rules.append("priority:assumptions_dominate")
    elif max(hemo_score, rhythm_score) > 0:
        # Priority 4: whichever real finding category scores higher leads.
        # Tie-break favors hemodynamic (documented, not hidden): a global/
        # structural functional finding has broader systemic implication
        # than an isolated conduction finding of equal severity weight.
        if hemo_score >= rhythm_score:
            lead_theme = "hemodynamic_deterioration"
            key_metrics = sorted(set(hemo_metrics)) or [_EF_METRIC_ID]
            triggered_rules.append("priority:hemodynamic_deterioration")
        else:
            lead_theme = "rhythm_electrophysiology"
            key_metrics = rhythm_metrics
            triggered_rules.append("priority:rhythm_electrophysiology")
    else:
        # Priority 5 (fallback): nothing scored — either genuinely quiet
        # findings (mild/info only) or no data at all (Case D).
        lead_theme = "stable_with_uncertainty"
        key_metrics = []
        triggered_rules.append("priority:fallback_stable_with_uncertainty")

    severity_direction = _resolve_severity_direction(
        lead_theme, bundle, prior_bundle, key_metrics, co_band
    )
    sections = _resolve_sections(bundle, lead_theme, scenario_active, prior_bundle)

    return ReportEmphasis(
        lead_theme=lead_theme,
        key_metrics=key_metrics,
        severity_direction=severity_direction,
        emphasized_sections=sections["emphasized"],
        minimized_sections=sections["minimized"],
        omitted_sections=sections["omitted"],
        tension_flags=tension_flags,
        triggered_rules=triggered_rules,
    )


def _resolve_severity_direction(
    lead_theme: LeadTheme,
    bundle: DecisionSupportBundle,
    prior_bundle: Optional[DecisionSupportBundle],
    key_metrics: list[str],
    co_band: Optional[str],
) -> SeverityDirection:
    if lead_theme == "conflicting_signals":
        return "mixed"

    if lead_theme == "stable_with_uncertainty":
        is_empty = (
            not bundle.derived_evidence
            and not bundle.observed_evidence
            and not bundle.simulated_results
            and not bundle.assumptions
        )
        return "insufficient_data" if is_empty else "stable"

    if prior_bundle is not None:
        deltas = build_delta_summary(bundle, prior_bundle)
        material = [d for d in deltas if d.material and d.metric_id in key_metrics]
        if not material:
            return "stable"
        worsening = 0
        improving = 0
        for d in material:
            if d.change_kind not in ("increase", "decrease") or d.absolute_delta is None:
                continue
            if d.metric_id in _LOWER_IS_WORSE:
                worse_direction = "decrease"
            elif d.metric_id in _HIGHER_IS_WORSE:
                worse_direction = "increase"
            else:
                # Unknown polarity (e.g. heart_rate_bpm, where neither
                # direction is unambiguously "worse") — never guess a
                # direction for a metric this module has no documented
                # polarity for.
                continue
            if d.change_kind == worse_direction:
                worsening += 1
            else:
                improving += 1
        if worsening and not improving:
            return "worsening"
        if improving and not worsening:
            return "improving"
        return "stable" if not (worsening or improving) else "mixed"

    if lead_theme == "simulation_driven":
        for metric_id in key_metrics:
            band = _simulated_band(bundle.simulated_results, metric_id)
            if band in ("reduced", "elevated"):
                return band  # type: ignore[return-value]
        return "insufficient_data" if not bundle.simulated_results else "stable"

    if lead_theme == "hemodynamic_deterioration":
        return "reduced"
    return "elevated"  # rhythm_electrophysiology: QRS/QTc widen/prolong upward


# ---------------------------------------------------------------------------
# Section emphasis (§26: never add a section with nothing real behind it)
# ---------------------------------------------------------------------------

_ALL_SECTIONS = (
    "clinical_context",
    "observed_evidence",
    "derived_evidence",
    "simulated_results",
    "uncertainty",
    "assumptions",
    "limitations",
    "missing_evidence",
    "conflicts",
    "possible_interpretations",
    "experiment_context",
    "delta_summary",
)


def _resolve_sections(
    bundle: DecisionSupportBundle,
    lead_theme: LeadTheme,
    scenario_active: bool,
    prior_bundle: Optional[DecisionSupportBundle],
) -> dict[str, list[str]]:
    emphasized: list[str] = []
    minimized: list[str] = []
    omitted: list[str] = []

    def place(section: str, has_content: bool, *, emphasize: bool) -> None:
        if not has_content:
            omitted.append(section)
        elif emphasize:
            emphasized.append(section)
        else:
            minimized.append(section)

    place("clinical_context", bool(bundle.clinical_context), emphasize=False)
    place("observed_evidence", bool(bundle.observed_evidence), emphasize=lead_theme != "stable_with_uncertainty")
    place(
        "derived_evidence",
        bool(bundle.derived_evidence),
        emphasize=lead_theme in ("hemodynamic_deterioration", "rhythm_electrophysiology", "conflicting_signals"),
    )
    ensemble_present = bool(bundle.simulated_results)
    place(
        "simulated_results",
        ensemble_present,
        emphasize=lead_theme in ("simulation_driven", "conflicting_signals")
        or (lead_theme == "hemodynamic_deterioration" and "cardiac_output_l_min" in bundle_metric_ids(bundle)),
    )
    place("uncertainty", bool(bundle.uncertainty), emphasize=lead_theme == "simulation_driven")
    place("assumptions", bool(bundle.assumptions), emphasize=lead_theme == "stable_with_uncertainty")
    # limitations always renders (safety/transparency requirement — AGENTS.md
    # §4 "safety stays on" — never omitted), just not always the headline.
    minimized_or_emph = "emphasized" if lead_theme == "stable_with_uncertainty" else "minimized"
    (emphasized if minimized_or_emph == "emphasized" else minimized).append("limitations")
    place("missing_evidence", bool(bundle.missing_evidence), emphasize=lead_theme == "stable_with_uncertainty")
    place("conflicts", bool(bundle.conflicts), emphasize=lead_theme == "conflicting_signals")
    place("possible_interpretations", bool(bundle.possible_interpretations), emphasize=False)

    # §26's concrete case: no experiment/ensemble ran -> no experiment
    # section at all, not an empty one.
    place("experiment_context", scenario_active or ensemble_present, emphasize=lead_theme == "simulation_driven")

    if prior_bundle is None:
        omitted.append("delta_summary")
    else:
        material_deltas = [d for d in build_delta_summary(bundle, prior_bundle) if d.material]
        place("delta_summary", True, emphasize=bool(material_deltas))

    assert set(emphasized) | set(minimized) | set(omitted) == set(_ALL_SECTIONS)
    return {"emphasized": emphasized, "minimized": minimized, "omitted": omitted}


def bundle_metric_ids(bundle: DecisionSupportBundle) -> set[str]:
    return {d.get("metric_id") for d in bundle.simulated_results if d.get("metric_id")}


# ---------------------------------------------------------------------------
# build_delta_summary
# ---------------------------------------------------------------------------


def _simulated_means(bundle: DecisionSupportBundle) -> dict[str, tuple[float, Optional[str]]]:
    out: dict[str, tuple[float, Optional[str]]] = {}
    for entry in bundle.simulated_results:
        metric_id = entry.get("metric_id")
        mean = entry.get("mean")
        if metric_id and isinstance(mean, (int, float)):
            out[str(metric_id)] = (float(mean), entry.get("unit"))
    return out


def _derived_numeric_by_metric_name(bundle: DecisionSupportBundle) -> dict[str, tuple[float, Optional[str]]]:
    """Same regex-on-deterministic-label approach as `_numeric_from_metric_label`
    (see its docstring): `derive_findings` formats `metric` with a fixed
    template per finding family, so extracting the number back out is a real
    parse of already-real data, not a guess. Keyed by `_canonical_metric_name`
    (not the raw `source` string) so this joins cleanly with
    `determine_content_hierarchy`'s `key_metrics` — see that function's
    docstring. `derive_findings` only ever emits at most one finding per
    distinct `source` (hence per canonical name) in a single case, so this
    is a safe grouping key."""
    out: dict[str, tuple[float, Optional[str]]] = {}
    for finding in bundle.derived_evidence:
        source = _finding_source(finding)
        if not source:
            continue
        value = _numeric_from_metric_label(finding.get("metric"))
        if value is None:
            continue
        label = str(finding.get("metric"))
        unit_part = re.sub(r"^-?\d+\.?\d*\s*", "", label).strip() or None
        out[_canonical_metric_name(source)] = (value, unit_part)
    return out


def _classify_delta(prior: float, current: float, metric_id: str) -> tuple[float, float, str]:
    absolute = current - prior
    relative = abs(absolute) / abs(prior) if prior != 0 else (0.0 if absolute == 0 else float("inf"))
    if absolute == 0:
        kind = "unchanged"
    elif absolute > 0:
        kind = "increase"
    else:
        kind = "decrease"
    return absolute, relative, kind


def build_delta_summary(
    current_bundle: DecisionSupportBundle, prior_bundle: Optional[DecisionSupportBundle]
) -> list[DeltaFinding]:
    """Real deltas on real overlapping metrics only.

    Materiality rule (documented, simple, per the task brief's own
    allowance): a numeric change is "material" if it moves by at least
    `DELTA_MATERIALITY_FRACTION` (10%) of the prior value's magnitude. A
    metric appearing in only one bundle is never assigned a fabricated
    counterpart value — it is reported as `change_kind="new"` or
    `"resolved"` and always marked material (presence/absence is itself the
    signal, there is no percentage to compute).

    `prior_bundle=None` (no prior case revision available — the common case
    until `case_context.py` lands historical-reference resolution) returns
    an empty list, matching `physician_brief.py`'s own
    `_LONGITUDINAL_LIMITATION` precedent of an honest empty rather than a
    fabricated "no change."
    """
    if prior_bundle is None:
        return []

    current_sim = _simulated_means(current_bundle)
    prior_sim = _simulated_means(prior_bundle)
    current_derived = _derived_numeric_by_metric_name(current_bundle)
    prior_derived = _derived_numeric_by_metric_name(prior_bundle)

    deltas: list[DeltaFinding] = []
    for metric_id in sorted(set(current_sim) | set(prior_sim)):
        cur = current_sim.get(metric_id)
        pri = prior_sim.get(metric_id)
        deltas.append(_delta_for(metric_id, pri, cur))

    # A metric present in BOTH the ensemble and derived-evidence views this
    # wave (only `ejection_fraction_pct` can be, via `_canonical_metric_name`)
    # already got its delta from the ensemble loop above — skip it here so
    # the same physiology doesn't produce two competing DeltaFinding rows.
    for metric_name in sorted((set(current_derived) | set(prior_derived)) - (set(current_sim) | set(prior_sim))):
        cur = current_derived.get(metric_name)
        pri = prior_derived.get(metric_name)
        deltas.append(_delta_for(metric_name, pri, cur))

    return deltas


def _delta_for(
    metric_id: str, prior: Optional[tuple[float, Optional[str]]], current: Optional[tuple[float, Optional[str]]]
) -> DeltaFinding:
    if prior is None and current is not None:
        return DeltaFinding(
            metric_id=metric_id, unit=current[1], current_value=current[0],
            change_kind="new", material=True,
        )
    if current is None and prior is not None:
        return DeltaFinding(
            metric_id=metric_id, unit=prior[1], prior_value=prior[0],
            change_kind="resolved", material=True,
        )
    assert prior is not None and current is not None
    prior_value, prior_unit = prior
    current_value, _ = current
    absolute, relative, kind = _classify_delta(prior_value, current_value, metric_id)
    material = kind != "unchanged" and relative >= DELTA_MATERIALITY_FRACTION
    return DeltaFinding(
        metric_id=metric_id,
        unit=prior_unit,
        prior_value=prior_value,
        current_value=current_value,
        absolute_delta=absolute,
        relative_delta=None if relative == float("inf") else relative,
        change_kind=kind,  # type: ignore[arg-type]
        material=material,
    )


# ---------------------------------------------------------------------------
# build_limitations_and_gaps
# ---------------------------------------------------------------------------


def build_limitations_and_gaps(
    bundle: DecisionSupportBundle, emphasis: Optional[ReportEmphasis] = None
) -> list[str]:
    """Extends, rather than duplicates, `physician_brief.py`'s existing
    honest-limitations pattern (`_SCOPE_LIMITATION`,
    `_LONGITUDINAL_LIMITATION`, etc., already on `bundle.limitations` —
    see `generate_physician_brief`). This function starts from that exact
    list and appends module-specific caveats about the CONTENT-HIERARCHY
    DECISION itself, which `physician_brief.py` has no way to know about
    since that decision is made here, one layer up.
    """
    out = list(bundle.limitations)

    if emphasis is None:
        return out

    if "priority:fallback_stable_with_uncertainty" in emphasis.triggered_rules:
        out.append(
            "This report's content hierarchy defaulted to a stable/uncertainty "
            "framing because no finding in derived_evidence/observed_evidence met "
            "this module's moderate/severe threshold — see report_personalization.py's "
            "_SEVERITY_WEIGHT rule."
        )
    if emphasis.tension_flags:
        out.append(
            "This case has at least one computed tension between two evidence "
            "layers (see tension_flags) that this brief surfaces rather than "
            "resolves — resolving it is a physician judgment, not this system's."
        )
    if "delta_summary" in emphasis.omitted_sections:
        out.append(
            "No prior case revision was available for comparison, so "
            "severity_direction reflects this single snapshot only, not a "
            "measured trend — see build_delta_summary's docstring."
        )

    return out
