"""CareGuard Redis key builders — the ONLY place key strings are constructed.

Every key is namespaced under the configured prefix (default ``careguard``) so
it can never collide with or overwrite an existing DualBeat key.
"""

from __future__ import annotations

from python.hearttwin.careguard import feature_flags as flags


def _p() -> str:
    return flags.redis_prefix()


# --- per-case artifacts -----------------------------------------------------
def case_fhir(case_id: str) -> str: return f"{_p()}:case:{case_id}:fhir"
def case_context(case_id: str) -> str: return f"{_p()}:case:{case_id}:context"
def case_multimorbidity(case_id: str) -> str: return f"{_p()}:case:{case_id}:multimorbidity"
def case_guidelines(case_id: str) -> str: return f"{_p()}:case:{case_id}:guidelines"
def case_drug_labels(case_id: str) -> str: return f"{_p()}:case:{case_id}:drug-labels"
def case_contraindications(case_id: str) -> str: return f"{_p()}:case:{case_id}:contraindications"
def case_candidates(case_id: str) -> str: return f"{_p()}:case:{case_id}:candidates"
def case_simulation(case_id: str) -> str: return f"{_p()}:case:{case_id}:simulation"
def case_critic(case_id: str) -> str: return f"{_p()}:case:{case_id}:critic"
def case_medication_safety(case_id: str) -> str: return f"{_p()}:case:{case_id}:medication-safety"
def case_medication_reconciliation(case_id: str) -> str: return f"{_p()}:case:{case_id}:medication-reconciliation"
def case_morbidity(case_id: str) -> str: return f"{_p()}:case:{case_id}:morbidity-context"
def case_medication_conflicts(case_id: str) -> str: return f"{_p()}:case:{case_id}:medication-conflicts"
def case_medication_alternatives(case_id: str) -> str: return f"{_p()}:case:{case_id}:medication-alternatives"
def case_feedback(case_id: str) -> str: return f"{_p()}:case:{case_id}:feedback"
def case_audit(case_id: str) -> str: return f"{_p()}:case:{case_id}:audit"
def case_record(case_id: str) -> str: return f"{_p()}:case:{case_id}:record"
def case_latest_run(case_id: str) -> str: return f"{_p()}:case:{case_id}:latest-run"


# --- per-run staged workflow ------------------------------------------------
def run_state(run_id: str) -> str: return f"{_p()}:run:{run_id}:state"
def run_lock(run_id: str) -> str: return f"{_p()}:run:{run_id}:lock"
def run_stages(run_id: str) -> str: return f"{_p()}:run:{run_id}:stages"


# --- shared caches ----------------------------------------------------------
def guideline_chunk(source_id: str, version: str, chunk_id: str) -> str:
    return f"{_p()}:guideline:{source_id}:{version}:{chunk_id}"


def drug_label(rxcui: str, label_version: str) -> str:
    return f"{_p()}:drug-label:{rxcui}:{label_version}"


def stage_result(case_id: str, stage_id: str) -> str:
    return f"{_p()}:case:{case_id}:stage:{stage_id}"
