"""Versioned, deterministic evidence taxonomy for the M8 research surface.

The taxonomy describes which *model proxies* an evidence type can constrain.
It is an educational mapping for the deterministic simulation, not a claim
about a person's measurements or care. The public ``evidence_constraints``
function retains the contract consumed by the M8 engine and ranking code.
"""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import EvidenceConstraint, EvidenceStrength

EVIDENCE_MAP_VERSION = "m8-evidence-map-v1"
EVIDENCE_TAXONOMY_VERSION = "m8-evidence-taxonomy-v1"
EDUCATIONAL_SCOPE = "Educational simulation proxy mapping only."


@dataclass(frozen=True)
class EvidenceTypeDefinition:
    """Immutable metadata for one supported evidence category.

    The tuple order is the canonical display and ranking tie-break order. A
    definition deliberately contains only model-proxy metadata; it does not
    interpret an uploaded or observed measurement.
    """

    evidence_type: str
    label: str
    constrained_parameters: tuple[str, ...]
    strength: EvidenceStrength
    rationale: str

    @property
    def source(self) -> str:
        return f"{EVIDENCE_TAXONOMY_VERSION}; {EDUCATIONAL_SCOPE}"

EVIDENCE_TAXONOMY: tuple[EvidenceTypeDefinition, ...] = (
    EvidenceTypeDefinition(
        evidence_type="echocardiographic_measurement",
        label="Echocardiographic measurement",
        constrained_parameters=("preload_index", "contractility_index"),
        strength="strong",
        rationale="Maps a structural or hemodynamic observation to the declared preload and contractility proxies.",
    ),
    EvidenceTypeDefinition(
        evidence_type="blood_pressure_series",
        label="Blood-pressure series",
        constrained_parameters=("afterload_index", "systemic_vascular_resistance_index"),
        strength="moderate",
        rationale="Maps repeated pressure observations to the declared pressure-related model proxies.",
    ),
    EvidenceTypeDefinition(
        evidence_type="repeat_ecg",
        label="Repeat ECG",
        constrained_parameters=("heart_rate_bpm",),
        strength="moderate",
        rationale="Maps a repeat rate or electrical observation only to the declared heart-rate proxy.",
    ),
)


def _constraint(definition: EvidenceTypeDefinition) -> EvidenceConstraint:
    """Convert immutable taxonomy metadata to the engine's public contract."""

    return EvidenceConstraint(
        evidence_type=definition.evidence_type,
        constrained_parameters=list(definition.constrained_parameters),
        strength=definition.strength,
        rationale=definition.rationale,
        source=definition.source,
    )


# Backwards-compatible contract constant. Callers should use
# ``evidence_constraints`` when they need records they can safely mutate.
DEFAULT_EVIDENCE_CONSTRAINTS: tuple[EvidenceConstraint, ...] = tuple(
    _constraint(definition) for definition in EVIDENCE_TAXONOMY
)


def evidence_taxonomy() -> tuple[EvidenceTypeDefinition, ...]:
    """Return the canonical immutable taxonomy in deterministic order."""

    return EVIDENCE_TAXONOMY


def evidence_constraints() -> tuple[EvidenceConstraint, ...]:
    """Return independent validated mapping records in canonical order."""

    return tuple(item.model_copy(deep=True) for item in DEFAULT_EVIDENCE_CONSTRAINTS)


__all__ = [
    "DEFAULT_EVIDENCE_CONSTRAINTS",
    "EDUCATIONAL_SCOPE",
    "EVIDENCE_MAP_VERSION",
    "EVIDENCE_TAXONOMY",
    "EVIDENCE_TAXONOMY_VERSION",
    "EvidenceTypeDefinition",
    "evidence_constraints",
    "evidence_taxonomy",
]
