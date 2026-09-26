"""The benchmark output schema is valid JSON Schema and the forced-tool schema
derived from it drops the harness-injected fields."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _bench_common import load_schema
from _model_arm import build_tool_schema

def test_output_schema_is_valid_draft7():
    from jsonschema import Draft7Validator
    Draft7Validator.check_schema(load_schema("benchmark_output"))

def test_tool_schema_excludes_injected_fields():
    ts = build_tool_schema()
    for k in ("case_id", "arm_id", "trial_id"):
        assert k not in ts.get("properties", {})
        assert k not in ts.get("required", [])
    assert "identified_conflicts" in ts["required"]

def _run():
    for k,v in list(globals().items()):
        if k.startswith("test_") and callable(v): v(); print("  ok ",k)
    print("output-schema tests passed")
if __name__ == "__main__": _run()
