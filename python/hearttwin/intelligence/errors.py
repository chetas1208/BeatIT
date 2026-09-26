"""Provider-neutral intelligence errors.

These errors are intentionally safe to surface in logs and API responses: they
contain exception types and operation names, never credentials or request
headers.
"""

from __future__ import annotations


class IntelligenceError(RuntimeError):
    """Base class for model-runtime failures."""


class ProviderConfigurationError(IntelligenceError):
    """The selected provider is not configured safely."""


class ProviderUnavailable(IntelligenceError):
    """The selected provider could not complete an operation."""


class ProviderResponseError(IntelligenceError):
    """A provider returned an invalid or unusable response."""
