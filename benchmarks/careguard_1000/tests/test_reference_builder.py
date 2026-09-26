"""Reference builder produces source-derived labels with counts + assertions."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _bench_common import CASES_DIR, REFERENCE_DIR
from _case_facts import load_case_facts, compute_allergy_conflicts

def test_allergy_matcher_conservative_and_correct():
    # case-000001 allergies are not in its active med list -> no conflict
    f = load_case_facts(CASES_DIR / "case-000001")
    assert compute_allergy_conflicts(f) == []

def test_reference_labels_present_and_shaped():
    p = REFERENCE_DIR / "reference_labels.ndjson"
    assert p.exists()
    n = 0
    for line in p.read_text().splitlines():
        if not line.strip(): continue
        r = json.loads(line); n += 1
        assert r["label_tier"] == "silver"
        assert "assertions" in r and "counts" in r
    assert n > 0

def _run():
    for k,v in list(globals().items()):
        if k.startswith("test_") and callable(v): v(); print("  ok ",k)
    print("reference-builder tests passed")
if __name__ == "__main__": _run()
