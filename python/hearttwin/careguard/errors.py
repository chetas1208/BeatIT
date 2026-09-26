"""CareGuard exception hierarchy.

Distinct types let the API layer map failures to safe HTTP responses without
leaking internals, and let the orchestrator decide retry vs. abstain vs. block.
"""

from __future__ import annotations


class CareGuardError(Exception):
    """Base class for all CareGuard failures."""


class CareGuardDisabledError(CareGuardError):
    """Raised when a CareGuard code path runs while the feature flag is off."""


class SafetyBoundaryError(CareGuardError):
    """A request or output crossed the clinical safety boundary (block, don't retry)."""

    def __init__(self, message: str, reason: str = "") -> None:
        self.reason = reason
        super().__init__(message)


class FhirValidationError(CareGuardError):
    """The supplied FHIR Bundle failed structural validation."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        self.issues = issues or []
        super().__init__(message)


class DeidentificationError(CareGuardError):
    """Identifiable data would have reached a model that must not receive it."""


class EvidenceUnavailableError(CareGuardError):
    """A verifiable source passage could not be produced → agent must abstain."""


class ModelRefusalError(CareGuardError):
    """The model returned a refusal (e.g. Fable stop_reason='refusal' on HTTP 200)."""

    def __init__(self, message: str, model: str = "", stop_reason: str = "") -> None:
        self.model = model
        self.stop_reason = stop_reason
        super().__init__(message)


class StageExecutionError(CareGuardError):
    """A staged-orchestration stage failed after its bounded retry."""

    def __init__(self, message: str, stage_id: str = "") -> None:
        self.stage_id = stage_id
        super().__init__(message)


class RunNotFoundError(CareGuardError):
    """No run/case exists for the given id."""
