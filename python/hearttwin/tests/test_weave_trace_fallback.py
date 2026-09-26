"""Local trace storage tests (no W&B Weave)."""

from __future__ import annotations

from python.hearttwin.tools.weave_trace import get_trace_sink, get_traces, trace_dir


def test_local_trace_records_pipeline_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BEATIT_TRACE_DIR", str(tmp_path / "traces"))
    sink = get_trace_sink()
    run_id = sink.start_run("case-fallback", "test", {"patient_name": "Jane Doe"})
    sink.log_agent_stage(run_id, {"stage": "extract_evidence", "status": "success"})
    sink.log_tool_call(run_id, "compute_map", {"systolic": 120}, {"map": 93.3})
    sink.log_eval_scores(run_id, {"overall_score": 0.9}, [])
    sink.finish_run(run_id, "success", {"done": True})

    traces = get_traces("case-fallback")
    assert traces
    info = sink.trace_info(run_id)
    assert info["status"] == "local"
    assert info["backend"] == "local"
    assert (tmp_path / "traces" / "case-fallback" / f"{run_id}.json").is_file()


def test_weave_trace_redacts_obvious_pii(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("BEATIT_TRACE_DIR", str(tmp_path / "traces"))
    sink = get_trace_sink()
    run_id = sink.start_run(
        "case-redact",
        "test",
        {"email": "person@example.com", "files": [{"filename": "report.pdf", "bytes": b"secret"}]},
    )
    sink.finish_run(run_id, "success", {})
    text = str(get_traces("case-redact"))
    assert "person@example.com" not in text
    assert "secret" not in text


def test_trace_dir_default_expandable() -> None:
    path = trace_dir()
    assert path.name == "traces"
