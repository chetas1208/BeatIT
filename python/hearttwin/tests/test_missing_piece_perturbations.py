import pytest

from python.hearttwin.missing_piece.perturbations import (
    PerturbationPolicy,
    resolve_perturbation_step,
    validate_baseline,
)


def test_fractional_step_uses_stable_parameter_scale_and_range_cap() -> None:
    policy = PerturbationPolicy("heart_rate_bpm", step=0.05)

    # Range is 170; half-range is 85, so 5% of the scale is 4.25 bpm.
    assert policy.resolved_step(60.0) == pytest.approx(4.25)

    # At a high baseline the range cap remains authoritative.
    assert policy.resolved_step(200.0) == pytest.approx(8.5)


def test_absolute_step_is_native_units_and_is_bounded() -> None:
    policy = PerturbationPolicy("preload_index", step=0.1, mode="absolute")
    assert policy.resolved_step(0.8) == pytest.approx(0.075)
    assert resolve_perturbation_step(
        "preload_index", 0.8, step=0.05, mode="absolute"
    ) == pytest.approx(0.05)


def test_points_select_one_sided_difference_at_each_bound() -> None:
    policy = PerturbationPolicy("contractility_index", step=0.05, mode="absolute")

    lower = policy.points(0.0)
    assert lower.method == "forward"
    assert lower.lower is None
    assert lower.upper == pytest.approx(0.05)

    upper = policy.points(1.5)
    assert upper.method == "backward"
    assert upper.lower == pytest.approx(1.45)
    assert upper.upper is None


@pytest.mark.parametrize(
    ("parameter_id", "baseline"),
    [
        ("not_a_parameter", 1.0),
        ("heart_rate_bpm", -1.0),
        ("heart_rate_bpm", 201.0),
        ("heart_rate_bpm", float("nan")),
    ],
)
def test_invalid_parameter_or_baseline_is_rejected(parameter_id: str, baseline: float) -> None:
    if parameter_id == "not_a_parameter":
        with pytest.raises(ValueError, match="unknown perturbation parameter"):
            PerturbationPolicy(parameter_id, step=0.05)
    else:
        with pytest.raises(ValueError, match="baseline_value"):
            validate_baseline(parameter_id, baseline)


@pytest.mark.parametrize(
    ("step", "mode"),
    [
        (0.0, "fractional"),
        (-0.1, "absolute"),
        (1.1, "fractional"),
        (float("inf"), "absolute"),
    ],
)
def test_invalid_policy_step_is_rejected(step: float, mode: str) -> None:
    with pytest.raises(ValueError):
        PerturbationPolicy("afterload_index", step=step, mode=mode)  # type: ignore[arg-type]


def test_invalid_direction_is_rejected() -> None:
    with pytest.raises(ValueError, match="direction"):
        PerturbationPolicy("heart_rate_bpm", step=0.05).value(80.0, "sideways")  # type: ignore[arg-type]
