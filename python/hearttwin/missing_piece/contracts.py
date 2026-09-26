"""Typed contracts for the deterministic M8 Missing Piece surface.

These models describe sensitivity, uncertainty impact, and evidence-ranking
records.  They intentionally carry presentation-ready metadata only; they do
not calculate sensitivity, uncertainty, or information gain.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from python.hearttwin.safety import DISCLAIMER

SensitivityMethod = Literal["local", "finite_difference", "other"]
DifferenceScheme = Literal["central", "forward", "backward", "unavailable"]
SensitivityTargetKind = Literal["baseline_output", "shadow_effect"]
ImpactMethod = Literal["uncertainty-impact-heuristic-v1"]
EvidenceRankingMethod = Literal["evidence-priority-score-v1"]
EvidenceStrength = Literal["direct", "strong", "moderate", "weak"]
ProvenanceSource = Literal["deterministic_model", "ensemble", "shadow_trial", "derived"]


def _finite(value: float, field_name: str) -> float:
    """Reject NaN and infinity, which otherwise pass through Pydantic floats."""

    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _text(value: str, field_name: str) -> str:
    """Require meaningful identifiers and descriptions, not whitespace."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


class _Contract(BaseModel):
    """Shared strictness for every public M8 contract."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SensitivityProvenance(_Contract):
    """Lineage for one sensitivity record.

    IDs are optional because a local deterministic analysis may be run before
    an ensemble or Shadow Trial is persisted.  When present, they identify the
    exact upstream artifact rather than duplicating its values.
    """

    source: ProvenanceSource = "deterministic_model"
    analysis_id: str | None = None
    ensemble_id: str | None = None
    shadow_trial_id: str | None = None
    sample_count: int | None = Field(default=None, ge=1)
    seed: int | None = None
    model_version: str = Field(default="m8-tier1-sensitivity-v1", min_length=1)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("analysis_id", "ensemble_id", "shadow_trial_id", "model_version")
    @classmethod
    def meaningful_text(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return None
        field_name = getattr(info, "field_name", "value")
        return _text(value, field_name)

    @field_validator("assumptions")
    @classmethod
    def meaningful_assumptions(cls, values: list[str]) -> list[str]:
        cleaned = [_text(value, "assumption") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("assumptions must be unique")
        return cleaned


class ParameterSensitivity(_Contract):
    """Sensitivity of one output metric to one model parameter."""

    parameter_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    method: SensitivityMethod
    sensitivity: float | None
    baseline_value: float | None
    perturbation: float | None = None
    normalized_sensitivity: float | None = None
    difference_scheme: DifferenceScheme | None = None
    available: bool = True
    unavailable_reason: str | None = None
    target_kind: SensitivityTargetKind = "baseline_output"
    parameter_unit: str | None = None
    metric_unit: str | None = None
    perturbation_mode: str = "fractional"
    perturbation_fraction: float | None = None
    max_range_fraction: float | None = None
    parameter_scale: float | None = None
    output_floor: float | None = None
    contributing_sample_count: int | None = Field(default=None, ge=1)
    normalized_q25: float | None = None
    normalized_q75: float | None = None
    provenance: SensitivityProvenance

    @field_validator("parameter_id", "metric_id")
    @classmethod
    def meaningful_identifiers(cls, value: str, info: object) -> str:
        return _text(value, getattr(info, "field_name", "identifier"))

    @field_validator(
        "sensitivity",
        "baseline_value",
        "perturbation",
        "normalized_sensitivity",
        "perturbation_fraction",
        "max_range_fraction",
        "parameter_scale",
        "output_floor",
        "normalized_q25",
        "normalized_q75",
    )
    @classmethod
    def finite_values(cls, value: float | None, info: object) -> float | None:
        if value is None:
            return None
        return _finite(value, getattr(info, "field_name", "value"))

    @model_validator(mode="after")
    def validate_perturbation(self) -> ParameterSensitivity:
        if self.available and self.sensitivity is None:
            raise ValueError("available sensitivity requires a numeric sensitivity")
        if self.available and self.baseline_value is None:
            raise ValueError("available sensitivity requires a numeric baseline_value")
        if self.available and self.method == "finite_difference" and self.perturbation is None:
            raise ValueError("finite_difference sensitivity requires perturbation")
        if not self.available and (self.sensitivity is not None or self.baseline_value is not None or self.perturbation is not None):
            raise ValueError("unavailable sensitivity cannot contain numeric response values")
        if not self.available and not self.unavailable_reason:
            raise ValueError("unavailable sensitivity requires unavailable_reason")
        if self.perturbation == 0.0:
            raise ValueError("perturbation must not be zero")
        if not self.available and self.difference_scheme not in {None, "unavailable"}:
            raise ValueError("unavailable sensitivity must use an unavailable difference scheme")
        return self


class ParameterUncertaintyImpact(_Contract):
    """Transparent Tier-1 impact heuristic for one parameter and metric.

    ``impact_score`` is deliberately not named information gain.  The contract
    permits any deterministic scoring method, while the component magnitudes
    make its inputs inspectable by callers and reviewers.
    """

    parameter_id: str = Field(min_length=1)
    metric_id: str = Field(min_length=1)
    uncertainty_magnitude: float = Field(ge=0.0)
    sensitivity_magnitude: float = Field(ge=0.0)
    impact_score: float = Field(ge=0.0)
    normalized_impact: float | None = Field(default=None, ge=0.0, le=1.0)
    method: ImpactMethod = "uncertainty-impact-heuristic-v1"

    @field_validator("parameter_id", "metric_id")
    @classmethod
    def meaningful_text(cls, value: str, info: object) -> str:
        return _text(value, getattr(info, "field_name", "value"))

    @field_validator(
        "uncertainty_magnitude",
        "sensitivity_magnitude",
        "impact_score",
        "normalized_impact",
    )
    @classmethod
    def finite_values(cls, value: float | None, info: object) -> float | None:
        if value is None:
            return None
        return _finite(value, getattr(info, "field_name", "value"))


class EvidenceConstraint(_Contract):
    """One explicit evidence-to-parameter constraint mapping."""

    evidence_type: str = Field(min_length=1)
    constrained_parameters: list[str] = Field(min_length=1)
    strength: EvidenceStrength
    rationale: str = Field(min_length=1)
    source: str = Field(min_length=1)

    @field_validator("evidence_type", "rationale", "source")
    @classmethod
    def meaningful_text(cls, value: str, info: object) -> str:
        return _text(value, getattr(info, "field_name", "value"))

    @field_validator("constrained_parameters")
    @classmethod
    def unique_parameters(cls, values: list[str]) -> list[str]:
        cleaned = [_text(value, "constrained_parameter") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("constrained_parameters must be unique")
        return cleaned


class EvidenceValueProvenance(_Contract):
    """Lineage and assumptions for a target-specific evidence estimate."""

    source: ProvenanceSource = "derived"
    evidence_map_version: str = Field(default="m8-evidence-map-v1", min_length=1)
    analysis_id: str | None = None
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("evidence_map_version", "analysis_id")
    @classmethod
    def meaningful_text(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return None
        return _text(value, getattr(info, "field_name", "value"))

    @field_validator("assumptions")
    @classmethod
    def meaningful_assumptions(cls, values: list[str]) -> list[str]:
        cleaned = [_text(value, "assumption") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("assumptions must be unique")
        return cleaned


class EvidenceValueEstimate(_Contract):
    """One target-specific, deterministic evidence-ranking item."""

    evidence_type: str = Field(min_length=1)
    target_metric: str = Field(min_length=1)
    constrained_parameters: list[str] = Field(min_length=1)
    estimated_reduction: float | None = Field(default=None, ge=0.0, le=1.0)
    ranking_score: float = Field(ge=0.0)
    method: EvidenceRankingMethod = "evidence-priority-score-v1"
    assumptions: list[str] = Field(min_length=1)
    provenance: EvidenceValueProvenance

    @field_validator("evidence_type", "target_metric")
    @classmethod
    def meaningful_text(cls, value: str, info: object) -> str:
        return _text(value, getattr(info, "field_name", "value"))

    @field_validator("constrained_parameters")
    @classmethod
    def unique_parameters(cls, values: list[str]) -> list[str]:
        cleaned = [_text(value, "constrained_parameter") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("constrained_parameters must be unique")
        return cleaned

    @field_validator("assumptions")
    @classmethod
    def meaningful_assumptions(cls, values: list[str]) -> list[str]:
        cleaned = [_text(value, "assumption") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("assumptions must be unique")
        return cleaned

    @field_validator("estimated_reduction", "ranking_score")
    @classmethod
    def finite_values(cls, value: float | None, info: object) -> float | None:
        if value is None:
            return None
        return _finite(value, getattr(info, "field_name", "value"))


class MissingPieceProvenance(_Contract):
    """Lineage for a complete Missing Piece analysis response."""

    source: ProvenanceSource = "derived"
    analysis_id: str = Field(min_length=1)
    ensemble_id: str | None = None
    shadow_trial_id: str | None = None
    sensitivity_method: str = Field(min_length=1)
    ranking_method: str = Field(min_length=1)
    model_version: str = Field(default="m8-missing-piece-v1", min_length=1)
    assumptions: list[str] = Field(min_length=1)

    @field_validator(
        "analysis_id",
        "ensemble_id",
        "shadow_trial_id",
        "sensitivity_method",
        "ranking_method",
        "model_version",
    )
    @classmethod
    def meaningful_text(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return None
        return _text(value, getattr(info, "field_name", "value"))

    @field_validator("assumptions")
    @classmethod
    def meaningful_assumptions(cls, values: list[str]) -> list[str]:
        cleaned = [_text(value, "assumption") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("assumptions must be unique")
        return cleaned


class MissingPieceResult(_Contract):
    """Complete response for why a target output remains uncertain."""

    target_metric: str = Field(min_length=1)
    sensitivities: list[ParameterSensitivity] = Field(default_factory=list)
    dominant_uncertainty_drivers: list[ParameterUncertaintyImpact] = Field(default_factory=list)
    evidence_ranking: list[EvidenceValueEstimate] = Field(default_factory=list)
    evidence_constraints: list[EvidenceConstraint] = Field(default_factory=list)
    completeness: dict[str, object] = Field(default_factory=dict)
    sensitivity_availability: dict[str, object] = Field(default_factory=dict)
    limitations: list[str] = Field(min_length=1)
    provenance: MissingPieceProvenance
    safety_disclaimer: str = DISCLAIMER

    @field_validator("target_metric")
    @classmethod
    def meaningful_target(cls, value: str) -> str:
        return _text(value, "target_metric")

    @field_validator("limitations")
    @classmethod
    def meaningful_limitations(cls, values: list[str]) -> list[str]:
        cleaned = [_text(value, "limitation") for value in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("limitations must be unique")
        return cleaned

    @field_validator("safety_disclaimer")
    @classmethod
    def canonical_disclaimer(cls, value: str) -> str:
        if value != DISCLAIMER:
            raise ValueError("Missing Piece safety disclaimer must use the canonical disclaimer")
        return value

    @model_validator(mode="after")
    def validate_unique_ranked_records(self) -> MissingPieceResult:
        sensitivity_keys = [(item.parameter_id, item.metric_id) for item in self.sensitivities]
        if len(sensitivity_keys) != len(set(sensitivity_keys)):
            raise ValueError("sensitivities must be unique by parameter and metric")
        driver_keys = [
            (item.parameter_id, item.metric_id) for item in self.dominant_uncertainty_drivers
        ]
        if len(driver_keys) != len(set(driver_keys)):
            raise ValueError("dominant uncertainty drivers must be unique by parameter and metric")
        evidence_types = [item.evidence_type for item in self.evidence_ranking]
        if len(evidence_types) != len(set(evidence_types)):
            raise ValueError("evidence ranking must contain one entry per evidence type")
        if any(item.target_metric != self.target_metric for item in self.evidence_ranking):
            raise ValueError("evidence ranking target_metric must match the response target")
        return self


# Descriptive aliases keep the public vocabulary usable by callers that refer
# to the records by their shorter M8 names.
SensitivityRecord = ParameterSensitivity
UncertaintyImpact = ParameterUncertaintyImpact
EvidenceMapping = EvidenceConstraint
TargetEvidenceRanking = EvidenceValueEstimate
MissingPieceResponse = MissingPieceResult


__all__ = [
    "DifferenceScheme",
    "EvidenceConstraint",
    "EvidenceMapping",
    "EvidenceRankingMethod",
    "EvidenceStrength",
    "EvidenceValueEstimate",
    "EvidenceValueProvenance",
    "ImpactMethod",
    "MissingPieceProvenance",
    "MissingPieceResponse",
    "MissingPieceResult",
    "ParameterSensitivity",
    "ParameterUncertaintyImpact",
    "ProvenanceSource",
    "SensitivityMethod",
    "SensitivityProvenance",
    "SensitivityRecord",
    "SensitivityTargetKind",
    "TargetEvidenceRanking",
    "UncertaintyImpact",
]
