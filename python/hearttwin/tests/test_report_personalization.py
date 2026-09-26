"""Tests for report_personalization.py — Wave 6.5's "Report Personalization
Engineer" task, and per `docs/assistant/PHYSICIAN_HELPER_HARDENING.md` §60/§61
the single most important test file in the wave.

Fixtures are 5 deliberately different SYNTHETIC `DecisionSupportBundle`
instances, built directly (not through `generate_physician_brief` + a real
tool registry) so each case can isolate exactly one real-data pattern per
the spec's test matrix:

  A. reduced-EF trajectory (declining EF/CO/SV across a prior -> current pair)
  B. preserved EF + a rhythm/QTc issue
  C. an active experiment/scenario is the dominant story
  D. incomplete data (sparse/empty bundle)
  E. contradictory-seeming measurements (severely reduced EF finding, but the
     ensemble's own cardiac_output_l_min distribution is NOT reduced)

Every field placed on a fixture bundle mirrors the REAL shape
`physician_brief.py::generate_physician_brief` produces (verified by reading
that file in full for this task) — `derived_evidence` entries carry
claim/detail/region/territory/aha_segments/severity/metric/codes/source
(NOT `id` — `physician_brief.py`'s dict comprehension drops it, which is why
`report_personalization.py` categorizes on `source` instead), and
`simulated_results`/`uncertainty` entries mirror
`get_ensemble_distributions`'s per-metric summary records.

Note on §60's "contradictory measurements" case: `cardiac_findings.py` and
`ensemble.py` have no explicit "contradiction" flag or field. The closest
real equivalent this data model can represent is what Case E tests: a
derived finding whose own severity implies one direction (severely reduced
EF -> expected reduced cardiac output) while the ensemble's own simulated
metric for the same physiology does NOT corroborate that direction. This is
a genuine, computed numeric tension between two real evidence layers in the
same bundle, not a fabricated contradiction.
"""

from __future__ import annotations

from python.hearttwin.assistant.physician_brief import DecisionSupportBundle
from python.hearttwin.assistant.report_personalization import (
    DELTA_MATERIALITY_FRACTION,
    ReportEmphasis,
    build_delta_summary,
    build_limitations_and_gaps,
    determine_content_hierarchy,
)
from python.hearttwin.assistant.schemas import ConversationContext


def _bundle(**overrides) -> DecisionSupportBundle:
    defaults: dict = dict(
        question="Decision support for case",
        clinical_context={},
        observed_evidence=[],
        derived_evidence=[],
        simulated_results=[],
        uncertainty=[],
        missing_evidence=[],
        conflicts=[],
        assumptions=[],
        provenance=[],
        limitations=[],
        possible_interpretations=[],
    )
    defaults.update(overrides)
    return DecisionSupportBundle(**defaults)


def _sim(metric_id: str, mean: float, unit: str, sample_count: int = 8) -> dict:
    return {
        "metric_id": metric_id,
        "unit": unit,
        "mean": mean,
        "median": mean,
        "min": mean - 3.0,
        "max": mean + 3.0,
        "sample_count": sample_count,
    }


def _uncertainty(metric_id: str, unit: str, sd: float) -> dict:
    return {
        "metric_id": metric_id,
        "unit": unit,
        "standard_deviation": sd,
        "variance": sd * sd,
        "quantiles": {"q05": 0.0, "q25": 0.0, "q75": 0.0, "q95": 0.0},
        "range": {"min": 0.0, "max": 0.0},
    }


_QTC_ASSUMPTION = (
    "Percentiles summarize accepted deterministic simulations and are not "
    "clinical confidence intervals."
)


# ---------------------------------------------------------------------------
# Case A: reduced-EF trajectory (declining EF/CO/SV, prior -> current)
# ---------------------------------------------------------------------------

_GLOBAL_SYSTOLIC_FINDING = {
    "claim": "Reduced ejection fraction",
    "detail": "Simulation shows globally reduced left-ventricular systolic function.",
    "region": "Left ventricle (global)",
    "territory": None,
    "aha_segments": list(range(1, 18)),
    "codes": [{"system": "AHA 17-segment model", "code": "1-17", "label": "Global left ventricle"}],
    "source": "visualization.summary.ef_pct",
}


def _case_a_current() -> DecisionSupportBundle:
    finding = dict(_GLOBAL_SYSTOLIC_FINDING, claim="Reduced ejection fraction (28%)", severity="severe", metric="EF 28%")
    return _bundle(
        clinical_context={"case_id": "case-a-reduced-ef", "ensemble_id": "ens-a"},
        derived_evidence=[finding],
        simulated_results=[
            _sim("ejection_fraction_pct", 29.0, "%"),
            _sim("cardiac_output_l_min", 3.2, "L/min"),
            _sim("stroke_volume_ml", 50.0, "mL"),
        ],
        uncertainty=[
            _uncertainty("ejection_fraction_pct", "%", 2.0),
            _uncertainty("cardiac_output_l_min", "L/min", 0.3),
            _uncertainty("stroke_volume_ml", "mL", 3.0),
        ],
        assumptions=[_QTC_ASSUMPTION, "Heart rate sampled from a normal distribution centered at baseline."],
        limitations=["No sensitivity or dominant-assumption analysis exists yet."],
    )


def _case_a_prior() -> DecisionSupportBundle:
    finding = dict(_GLOBAL_SYSTOLIC_FINDING, claim="Reduced ejection fraction (42%)", severity="moderate", metric="EF 42%")
    return _bundle(
        clinical_context={"case_id": "case-a-reduced-ef", "ensemble_id": "ens-a-prior"},
        derived_evidence=[finding],
        simulated_results=[
            _sim("ejection_fraction_pct", 45.0, "%"),
            _sim("cardiac_output_l_min", 4.5, "L/min"),
            _sim("stroke_volume_ml", 65.0, "mL"),
        ],
        uncertainty=[
            _uncertainty("ejection_fraction_pct", "%", 2.0),
            _uncertainty("cardiac_output_l_min", "L/min", 0.3),
            _uncertainty("stroke_volume_ml", "mL", 3.0),
        ],
        assumptions=[_QTC_ASSUMPTION],
    )


# ---------------------------------------------------------------------------
# Case B: preserved EF + rhythm/QTc issue
# ---------------------------------------------------------------------------


def _case_b() -> DecisionSupportBundle:
    qtc_finding = {
        "claim": "Prolonged QTc (470 ms)",
        "detail": "Simulation shows prolonged ventricular repolarization (QTc 470 ms, Bazett).",
        "region": "Ventricular repolarization",
        "territory": None,
        "aha_segments": [],
        "severity": "moderate",
        "metric": "QTc 470 ms",
        "codes": [{"system": "ECG interval", "code": "QTc", "label": "Corrected QT interval"}],
        "source": "visualization.electrophysiology.qtc_ms",
    }
    return _bundle(
        clinical_context={"case_id": "case-b-preserved-ef-qtc", "ensemble_id": "ens-b"},
        derived_evidence=[qtc_finding],
        simulated_results=[_sim("ejection_fraction_pct", 58.0, "%"), _sim("heart_rate_bpm", 72.0, "bpm")],
        uncertainty=[_uncertainty("ejection_fraction_pct", "%", 3.0), _uncertainty("heart_rate_bpm", "bpm", 2.0)],
        assumptions=[_QTC_ASSUMPTION],
    )


# ---------------------------------------------------------------------------
# Case C: active experiment/scenario is the dominant story
# ---------------------------------------------------------------------------


def _case_c() -> DecisionSupportBundle:
    return _bundle(
        clinical_context={"case_id": "case-c-scenario", "ensemble_id": "ens-c"},
        derived_evidence=[],
        simulated_results=[_sim("ejection_fraction_pct", 38.0, "%"), _sim("stroke_volume_ml", 55.0, "mL")],
        uncertainty=[_uncertainty("ejection_fraction_pct", "%", 4.0), _uncertainty("stroke_volume_ml", "mL", 5.0)],
        assumptions=[
            "Scenario projects an afterload increase per the requested shadow-trial parameters.",
            _QTC_ASSUMPTION,
        ],
    )


_CASE_C_CONTEXT = ConversationContext(conversation_id="conv-c", audience="physician", scenario_id="scenario-shadow-1")


# ---------------------------------------------------------------------------
# Case D: incomplete data
# ---------------------------------------------------------------------------


def _case_d() -> DecisionSupportBundle:
    return _bundle(
        clinical_context={"case_id": "case-d-incomplete"},
        limitations=["No ensemble_id was supplied for this case."],
    )


# ---------------------------------------------------------------------------
# Case E: contradictory-seeming measurements
# ---------------------------------------------------------------------------


def _case_e() -> DecisionSupportBundle:
    finding = dict(_GLOBAL_SYSTOLIC_FINDING, claim="Reduced ejection fraction (25%)", severity="severe", metric="EF 25%")
    return _bundle(
        clinical_context={"case_id": "case-e-contradictory", "ensemble_id": "ens-e"},
        derived_evidence=[finding],
        simulated_results=[
            _sim("ejection_fraction_pct", 26.0, "%"),
            _sim("cardiac_output_l_min", 6.5, "L/min"),  # NOT reduced despite severely reduced EF
        ],
        uncertainty=[_uncertainty("ejection_fraction_pct", "%", 2.5), _uncertainty("cardiac_output_l_min", "L/min", 0.4)],
        assumptions=[_QTC_ASSUMPTION],
    )


# ---------------------------------------------------------------------------
# The actual §60 test: 5 emphases must be materially different
# ---------------------------------------------------------------------------


def test_five_synthetic_cases_produce_materially_different_emphasis() -> None:
    emphasis_a = determine_content_hierarchy(_case_a_current(), prior_bundle=_case_a_prior())
    emphasis_b = determine_content_hierarchy(_case_b())
    emphasis_c = determine_content_hierarchy(_case_c(), context=_CASE_C_CONTEXT)
    emphasis_d = determine_content_hierarchy(_case_d())
    emphasis_e = determine_content_hierarchy(_case_e())

    results = {"A": emphasis_a, "B": emphasis_b, "C": emphasis_c, "D": emphasis_d, "E": emphasis_e}

    # 1. lead_theme: every one of the 5 cases lands on a DIFFERENT theme —
    # this is the concrete, structural version of "if the reports look
    # nearly identical except numbers: FAIL."
    themes = {name: r.lead_theme for name, r in results.items()}
    assert themes == {
        "A": "hemodynamic_deterioration",
        "B": "rhythm_electrophysiology",
        "C": "simulation_driven",
        "D": "stable_with_uncertainty",
        "E": "conflicting_signals",
    }
    assert len(set(themes.values())) == 5, f"expected 5 distinct lead themes, got {themes}"

    # 2. severity_direction also differs across all 5 (real computed values,
    # not a coincidence of the same default).
    directions = {name: r.severity_direction for name, r in results.items()}
    assert directions == {
        "A": "worsening",
        "B": "elevated",
        "C": "reduced",
        "D": "insufficient_data",
        "E": "mixed",
    }
    assert len(set(directions.values())) == 5, f"expected 5 distinct severity directions, got {directions}"

    # 3. key_metrics differ (structurally, not just numerically).
    key_metrics = {name: tuple(r.key_metrics) for name, r in results.items()}
    assert key_metrics["A"] == ("cardiac_output_l_min", "ejection_fraction_pct", "stroke_volume_ml")
    assert key_metrics["B"] == ("qtc_ms",)
    assert key_metrics["C"] == ("ejection_fraction_pct", "stroke_volume_ml")
    assert key_metrics["D"] == ()
    assert key_metrics["E"] == ("ejection_fraction_pct", "cardiac_output_l_min")
    assert len({tuple(sorted(v)) for v in key_metrics.values()}) == 5

    # 4. emphasized/omitted section sets differ meaningfully case to case —
    # §26's rule made concrete: D (no ensemble ran) omits simulated_results/
    # uncertainty/assumptions/experiment_context/delta_summary entirely; C
    # (ensemble IS the story) emphasizes exactly those.
    assert "simulated_results" in emphasis_d.omitted_sections
    assert "experiment_context" in emphasis_d.omitted_sections
    assert "simulated_results" in emphasis_c.emphasized_sections
    assert "uncertainty" in emphasis_c.emphasized_sections
    assert "experiment_context" in emphasis_c.emphasized_sections

    # A's derived+simulated evidence both lead -> both emphasized; B's
    # ensemble is present but not the headline -> minimized, not emphasized.
    assert "derived_evidence" in emphasis_a.emphasized_sections
    assert "simulated_results" in emphasis_a.emphasized_sections
    assert "derived_evidence" in emphasis_b.emphasized_sections  # the QTc finding IS the headline
    assert "simulated_results" in emphasis_b.minimized_sections  # ensemble present but not central

    # E's tension is real and non-empty; no other case has one.
    assert len(emphasis_e.tension_flags) == 1
    assert emphasis_e.tension_flags[0].between == (
        "derived_evidence:visualization.summary.ef_pct",
        "simulated_results:cardiac_output_l_min",
    )
    for name, r in results.items():
        if name != "E":
            assert r.tension_flags == [], f"case {name} should have no tension_flags, got {r.tension_flags}"

    # D is the only case with a delta_summary section omitted for lack of a
    # prior AND every other content section also empty/omitted — the
    # "incomplete data" signature.
    assert set(emphasis_d.omitted_sections) >= {
        "observed_evidence",
        "derived_evidence",
        "simulated_results",
        "uncertainty",
        "assumptions",
        "missing_evidence",
        "conflicts",
        "possible_interpretations",
        "experiment_context",
        "delta_summary",
    }

    # A is the only case run with a prior bundle -> the only one with a
    # populated (not omitted) delta_summary.
    assert "delta_summary" not in emphasis_a.omitted_sections
    for name, r in results.items():
        if name != "A":
            assert "delta_summary" in r.omitted_sections, f"case {name} was not given a prior bundle"

    # 5. triggered_rules names real, distinct rule ids per case (proves the
    # decision was rule-driven, not a coin flip that happened to differ).
    assert "hemodynamic_alignment_ef_and_co_both_reduced" in emphasis_a.triggered_rules
    assert "priority:rhythm_electrophysiology" in emphasis_b.triggered_rules
    assert "priority:simulation_driven_scenario_active" in emphasis_c.triggered_rules
    assert "priority:fallback_stable_with_uncertainty" in emphasis_d.triggered_rules
    assert "conflicting_ef_reduced_but_co_not_reduced" in emphasis_e.triggered_rules


def test_all_five_emphasis_objects_are_pairwise_distinct() -> None:
    """Belt-and-suspenders on the same rule: no two of the 5 ReportEmphasis
    objects (compared as full structured data, not just lead_theme) are
    equal — a stricter, mechanical version of "materially different"."""
    emphases: list[ReportEmphasis] = [
        determine_content_hierarchy(_case_a_current(), prior_bundle=_case_a_prior()),
        determine_content_hierarchy(_case_b()),
        determine_content_hierarchy(_case_c(), context=_CASE_C_CONTEXT),
        determine_content_hierarchy(_case_d()),
        determine_content_hierarchy(_case_e()),
    ]
    for i in range(len(emphases)):
        for j in range(i + 1, len(emphases)):
            assert emphases[i] != emphases[j], f"cases {i} and {j} produced identical ReportEmphasis"


# ---------------------------------------------------------------------------
# determine_content_hierarchy: individual rule behavior
# ---------------------------------------------------------------------------


def test_hemodynamic_alignment_bonus_requires_both_layers_reduced() -> None:
    """The §88 example made concrete: EF-reduced finding alone (no ensemble
    corroboration in the reduced direction) still leads hemodynamic, but
    does NOT get the alignment bonus or pull cardiac_output into key_metrics."""
    finding = dict(_GLOBAL_SYSTOLIC_FINDING, severity="moderate", metric="EF 38%")
    bundle = _bundle(derived_evidence=[finding])  # no ensemble at all
    emphasis = determine_content_hierarchy(bundle)
    assert emphasis.lead_theme == "hemodynamic_deterioration"
    assert emphasis.key_metrics == ["ejection_fraction_pct"]
    assert "hemodynamic_alignment_ef_and_co_both_reduced" not in emphasis.triggered_rules


def test_assumptions_dominate_overrides_a_single_mild_finding() -> None:
    """A single MILD finding (below the moderate/severe bar) plus a heavy
    assumptions list should read as uncertainty-dominated, not deterioration
    — this is the literal "if assumptions dominate ... emphasize uncertainty
    instead" rule."""
    mild_finding = dict(_GLOBAL_SYSTOLIC_FINDING, severity="mild", metric="EF 48%")
    bundle = _bundle(
        derived_evidence=[mild_finding],
        assumptions=[_QTC_ASSUMPTION, "Heart rate sampled from a normal distribution.", "Preload held near baseline."],
    )
    emphasis = determine_content_hierarchy(bundle)
    assert emphasis.lead_theme == "stable_with_uncertainty"
    assert "priority:assumptions_dominate" in emphasis.triggered_rules


def test_moderate_finding_is_not_overridden_by_assumptions_dominance() -> None:
    """The same heavy assumptions list must NOT suppress a real MODERATE (or
    worse) finding — the override only applies below the moderate/severe
    bar."""
    moderate_finding = dict(_GLOBAL_SYSTOLIC_FINDING, severity="moderate", metric="EF 38%")
    bundle = _bundle(
        derived_evidence=[moderate_finding],
        assumptions=[_QTC_ASSUMPTION, "Heart rate sampled from a normal distribution.", "Preload held near baseline."],
    )
    emphasis = determine_content_hierarchy(bundle)
    assert emphasis.lead_theme == "hemodynamic_deterioration"


def test_no_scenario_and_no_ensemble_never_produces_simulation_driven() -> None:
    bundle = _case_a_current()
    emphasis = determine_content_hierarchy(bundle)  # no context passed
    assert emphasis.lead_theme != "simulation_driven"


def test_experiment_section_omitted_entirely_when_no_scenario_and_no_ensemble() -> None:
    """§26's exact wording: 'if no experiment was run, don't add an
    experiment section' — assert it is OMITTED, not present-but-empty."""
    emphasis = determine_content_hierarchy(_case_d())
    assert "experiment_context" in emphasis.omitted_sections
    assert "experiment_context" not in emphasis.emphasized_sections
    assert "experiment_context" not in emphasis.minimized_sections


# ---------------------------------------------------------------------------
# build_delta_summary
# ---------------------------------------------------------------------------


def test_build_delta_summary_returns_empty_list_with_no_prior() -> None:
    assert build_delta_summary(_case_a_current(), None) == []


def test_build_delta_summary_computes_real_material_deltas() -> None:
    deltas = build_delta_summary(_case_a_current(), _case_a_prior())
    by_metric = {d.metric_id: d for d in deltas}

    ef = by_metric["ejection_fraction_pct"]
    assert ef.prior_value == 45.0
    assert ef.current_value == 29.0
    assert ef.change_kind == "decrease"
    assert ef.material is True
    assert ef.relative_delta is not None and ef.relative_delta >= DELTA_MATERIALITY_FRACTION

    co = by_metric["cardiac_output_l_min"]
    assert co.change_kind == "decrease"
    assert co.material is True


def test_build_delta_summary_never_fabricates_a_prior_value() -> None:
    current = _bundle(simulated_results=[_sim("heart_rate_bpm", 80.0, "bpm")])
    prior = _bundle(simulated_results=[])
    deltas = build_delta_summary(current, prior)
    assert len(deltas) == 1
    assert deltas[0].change_kind == "new"
    assert deltas[0].prior_value is None
    assert deltas[0].current_value == 80.0
    assert deltas[0].material is True  # presence/absence is always material


def test_build_delta_summary_marks_resolved_finding() -> None:
    current = _bundle(simulated_results=[])
    prior = _bundle(simulated_results=[_sim("heart_rate_bpm", 80.0, "bpm")])
    deltas = build_delta_summary(current, prior)
    assert deltas[0].change_kind == "resolved"
    assert deltas[0].current_value is None
    assert deltas[0].prior_value == 80.0


def test_build_delta_summary_below_threshold_is_not_material() -> None:
    """A change smaller than DELTA_MATERIALITY_FRACTION (10%) is real signal
    but classified as noise-level, per this module's documented threshold."""
    current = _bundle(simulated_results=[_sim("heart_rate_bpm", 74.0, "bpm")])
    prior = _bundle(simulated_results=[_sim("heart_rate_bpm", 72.0, "bpm")])
    deltas = build_delta_summary(current, prior)
    assert deltas[0].change_kind == "increase"
    assert deltas[0].relative_delta is not None and deltas[0].relative_delta < DELTA_MATERIALITY_FRACTION
    assert deltas[0].material is False


def test_build_delta_summary_unchanged_metric_is_not_material() -> None:
    current = _bundle(simulated_results=[_sim("heart_rate_bpm", 72.0, "bpm")])
    prior = _bundle(simulated_results=[_sim("heart_rate_bpm", 72.0, "bpm")])
    deltas = build_delta_summary(current, prior)
    assert deltas[0].change_kind == "unchanged"
    assert deltas[0].material is False


def test_build_delta_summary_does_not_double_count_ef_across_layers() -> None:
    """`ejection_fraction_pct` can be computed from BOTH simulated_results
    (ensemble mean) and derived_evidence (the formatted 'EF NN%' label).
    Only one DeltaFinding for it should be produced (the ensemble-sourced
    one), not two competing numbers for the same physiology."""
    deltas = build_delta_summary(_case_a_current(), _case_a_prior())
    ef_deltas = [d for d in deltas if d.metric_id == "ejection_fraction_pct"]
    assert len(ef_deltas) == 1
    # It's the ensemble mean (29.0/45.0), not the derived-evidence label
    # values (28/42) — confirms the simulated_results loop wins the dedup.
    assert ef_deltas[0].current_value == 29.0
    assert ef_deltas[0].prior_value == 45.0


# ---------------------------------------------------------------------------
# build_limitations_and_gaps
# ---------------------------------------------------------------------------


def test_build_limitations_and_gaps_includes_bundle_limitations_verbatim() -> None:
    bundle = _case_d()
    out = build_limitations_and_gaps(bundle)
    assert out == bundle.limitations  # no emphasis given -> passthrough, no duplication


def test_build_limitations_and_gaps_adds_fallback_caveat_for_case_d() -> None:
    bundle = _case_d()
    emphasis = determine_content_hierarchy(bundle)
    out = build_limitations_and_gaps(bundle, emphasis)
    assert len(out) > len(bundle.limitations)
    assert any("stable/uncertainty" in text for text in out)


def test_build_limitations_and_gaps_adds_tension_caveat_for_case_e() -> None:
    bundle = _case_e()
    emphasis = determine_content_hierarchy(bundle)
    out = build_limitations_and_gaps(bundle, emphasis)
    assert any("tension between two evidence" in text for text in out)


def test_build_limitations_and_gaps_notes_missing_prior_when_no_delta() -> None:
    bundle = _case_b()
    emphasis = determine_content_hierarchy(bundle)
    out = build_limitations_and_gaps(bundle, emphasis)
    assert any("No prior case revision was available" in text for text in out)


def test_build_limitations_and_gaps_omits_prior_caveat_when_prior_given() -> None:
    bundle = _case_a_current()
    emphasis = determine_content_hierarchy(bundle, prior_bundle=_case_a_prior())
    out = build_limitations_and_gaps(bundle, emphasis)
    assert not any("No prior case revision was available" in text for text in out)
