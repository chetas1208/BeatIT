"""Anti-circularity / no-data-leakage guards (CLAIMS_POLICY enforcement).

Verifies the reference set is source-derived (not model/system output) and that
the evidence packet carries no answer label.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
from _bench_common import CASES_DIR, REFERENCE_DIR  # noqa: E402
from _case_facts import load_case_facts  # noqa: E402
from _packets import build_evidence_packet  # noqa: E402

_ANSWER_PHRASES = [
    "expected answer", "the correct alternative", "careguard previously",
    "careguard determined", "ground truth", "the right answer is",
]


def test_reference_declares_no_model_or_system_source():
    p = REFERENCE_DIR / "reference_labels.ndjson"
    assert p.exists(), "reference not built"
    first = json.loads(p.read_text().splitlines()[0])
    prov = first.get("provenance", {})
    assert prov.get("no_model_used") is True
    assert prov.get("no_system_output_used") is True
    assert first.get("label_tier") == "silver"


def test_reference_sources_are_case_files_only():
    first = json.loads(
        (REFERENCE_DIR / "reference_labels.ndjson").read_text().splitlines()[0])
    for src in first["provenance"]["derived_from"]:
        # every source is a per-case data file, never a model/careguard output
        assert any(src.startswith(pfx) for pfx in
                   ("medication-evidence/", "ehr/", "clinical/",
                    "quality.json", "provenance.json")), src


def test_evidence_packet_has_no_answer_label():
    # sample a handful of cases
    cids = sorted(d.name for d in CASES_DIR.iterdir()
                  if d.is_dir() and d.name.startswith("case-"))[:5]
    for cid in cids:
        facts = load_case_facts(CASES_DIR / cid)
        ep = build_evidence_packet(facts)
        blob = json.dumps(ep).lower()
        for phrase in _ANSWER_PHRASES:
            assert phrase not in blob, f"{cid}: leaked '{phrase}'"
        # the packet must not contain the reference expectation keys
        assert "expected_contraindication_signals" not in blob
        assert "expected_allergy_conflicts" not in blob


def _run():
    fns = [v for k, v in globals().items()
           if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} leakage tests passed")


if __name__ == "__main__":
    _run()
