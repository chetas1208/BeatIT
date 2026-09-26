"""Local trace integration tests (W&B Weave removed)."""

from __future__ import annotations

import contextlib
import os

from python.hearttwin.tools.weave_trace import TraceSink, get_traces, weave_status


@contextlib.contextmanager
def env(**kv):
    old = {k: os.environ.get(k) for k in kv}
    try:
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_trace_status_local_by_default() -> None:
    with env(HEARTTWIN_TRACE_MODE="local"):
        status = weave_status()
        assert status["enabled"] is True
        assert status["status"] == "local"
        assert status["backend"] == "local"


def test_trace_disabled_when_mode_off() -> None:
    with env(HEARTTWIN_TRACE_MODE="off"):
        sink = TraceSink()
        assert sink.enabled() is False
        assert sink.start_run("case-off", "test", {}) is None


def test_trace_sink_never_throws() -> None:
    sink = TraceSink()
    run_id = sink.start_run("case-x", "extract", {"k": "v"})
    sink.log_agent_stage(run_id, {"stage": "s", "agent": "a", "status": "success"})
    sink.log_tool_call(run_id, "tool", {"in": 1}, {"out": 2})
    sink.log_eval_scores(run_id, {"overall_score": 0.9}, [])
    sink.finish_run(run_id, "success", {"done": True})
    sink.log_agent_stage(None, {"stage": "s"})
    sink.finish_run(None, "success", {})


def test_agent_stage_written_locally() -> None:
    sink = TraceSink()
    run_id = sink.start_run("case-local-1", "operate", {})
    sink.log_agent_stage(run_id, {"stage": "build", "agent": "state_builder_agent", "status": "success"})
    events = get_traces("case-local-1")
    assert any(e.get("kind") == "agent_stage" and e.get("agent") == "state_builder_agent" for e in events)
