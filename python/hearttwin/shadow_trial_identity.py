"""Stable identity helpers for paired Shadow Trial samples."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


class PairIdentityError(ValueError):
    """Base error for invalid deterministic pair identity."""


class MissingSampleIDError(PairIdentityError):
    pass


class DuplicateSampleIDError(PairIdentityError):
    pass


class MissingPairError(PairIdentityError):
    pass


class UnexpectedPairError(PairIdentityError):
    pass


class PairNotFoundError(PairIdentityError):
    pass


@dataclass(frozen=True)
class PairIdentity:
    sample_id: str
    baseline_twin_id: str
    scenario_twin_id: str


def scenario_sample_id(trial_id: str, baseline_sample_id: str | None = None) -> str:
    """Return a stable scenario ID.

    The one-argument form is retained for the compact ``scenario-sample-X``
    identity used by focused tests; the two-argument form namespaces IDs by
    Shadow Trial so persisted results from different trials cannot collide.
    """
    if not isinstance(trial_id, str) or not trial_id.strip() or (
        baseline_sample_id is not None and (not isinstance(baseline_sample_id, str) or not baseline_sample_id.strip())
    ):
        raise MissingSampleIDError("trial and baseline sample IDs must be non-empty")
    if baseline_sample_id is None:
        return f"scenario-{trial_id}"
    return f"{trial_id}-scenario-{baseline_sample_id}"


def make_pair_identity(sample_id: str, trial_id: str | None = None) -> PairIdentity:
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise MissingSampleIDError("baseline sample ID must be non-empty")
    return PairIdentity(
        sample_id=sample_id,
        baseline_twin_id=sample_id,
        scenario_twin_id=scenario_sample_id(trial_id, sample_id) if trial_id else scenario_sample_id(sample_id),
    )


def build_pair_index(
    baseline_ids: Iterable[str],
    scenario_ids: Iterable[str] | None = None,
    trial_id: str | None = None,
) -> dict[str, PairIdentity]:
    baseline = list(baseline_ids)
    if any(not isinstance(value, str) or not value.strip() for value in baseline):
        raise MissingSampleIDError("baseline sample IDs must be non-empty")
    if len(set(baseline)) != len(baseline):
        duplicate = next(value for value in baseline if baseline.count(value) > 1)
        raise DuplicateSampleIDError(duplicate)
    expected = {scenario_sample_id(value) for value in baseline} if trial_id is None else {scenario_sample_id(trial_id, value) for value in baseline}
    if scenario_ids is None:
        return {sample_id: make_pair_identity(sample_id, trial_id) for sample_id in baseline}
    actual = list(scenario_ids)
    if len(set(actual)) != len(actual):
        duplicate = next(value for value in actual if actual.count(value) > 1)
        raise DuplicateSampleIDError(duplicate)
    if not expected.issubset(actual):
        missing = next(iter(expected - set(actual)))
        raise MissingPairError(missing)
    if set(actual) != expected:
        unexpected = next(iter(set(actual) - expected))
        raise UnexpectedPairError(unexpected)
    return {
        sample_id: make_pair_identity(sample_id, trial_id)
        for sample_id in baseline
    }


def lookup_pair(pair_index: Mapping[str, PairIdentity], sample_id: str) -> PairIdentity:
    try:
        return pair_index[sample_id]
    except KeyError as exc:
        raise PairNotFoundError(sample_id) from exc


def index_baseline_samples(samples: Iterable[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    indexed: dict[str, Mapping[str, object]] = {}
    for sample in samples:
        sample_id = sample.get("id")
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise ValueError("every baseline sample must have a non-empty id")
        if sample_id in indexed:
            raise ValueError(f"duplicate baseline sample id: {sample_id}")
        indexed[sample_id] = sample
    return indexed
