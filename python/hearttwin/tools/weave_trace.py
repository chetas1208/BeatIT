"""Local agent trace storage (in-process + on-disk). No W&B / Weave."""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from python.hearttwin.safety import redact_pii
from python.hearttwin.tools.env_config import local_trace_enabled

_LOCAL_TRACES: dict[str, list[dict[str, Any]]] = {}
_LOCAL_RUNS: dict[str, dict[str, Any]] = {}
_TRACE_WARNINGS: list[str] = []

_PII_KEYS = {
    "patient_name",
    "name",
    "email",
    "phone",
    "address",
    "dob",
    "date_of_birth",
    "mrn",
    "medical_record_number",
    "ssn",
    "bytes",
    "content",
    "raw_text",
    "full_text",
    "patient_notes",
}


def trace_dir() -> Path:
    raw = os.environ.get("BEATIT_TRACE_DIR", "").strip()
    root = Path(raw).expanduser() if raw else Path.home() / ".local" / "share" / "beatit" / "traces"
    root.mkdir(parents=True, exist_ok=True)
    return root


class TraceSink:
    """Trace wrapper that never lets tracing errors affect the app."""

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def enabled(self) -> bool:
        return local_trace_enabled()

    def start_run(self, case_id: str, run_type: str, metadata: dict) -> str | None:
        if not self.enabled():
            return None
        try:
            run_id = str(uuid.uuid4())
            run = {
                "run_id": run_id,
                "case_id": case_id,
                "run_type": run_type,
                "status": "running",
                "metadata": _sanitize(metadata),
                "started_at": time.time(),
                "finished_at": None,
                "stages": [],
                "tool_calls": [],
                "eval_scores": None,
                "warnings": [],
                "trace": self.trace_info(run_id),
            }
            _LOCAL_RUNS[run_id] = run
            _LOCAL_TRACES.setdefault(case_id, []).append(
                {"kind": "run_start", "run_id": run_id, "run_type": run_type, "metadata": run["metadata"]}
            )
            return run_id
        except Exception as exc:
            self._warn(f"Trace start failed: {exc}")
            return None

    def log_agent_stage(self, run_id: str | None, stage: dict) -> None:
        if not self.enabled():
            return
        try:
            payload = {"kind": "agent_stage", **_sanitize(stage), "timestamp": time.time()}
            self._append(run_id, "stages", payload)
        except Exception as exc:
            self._warn(f"Agent trace failed: {exc}")

    def log_tool_call(
        self,
        run_id: str | None,
        tool_name: str,
        inputs: dict,
        outputs: dict,
        metrics: dict | None = None,
    ) -> None:
        if not self.enabled():
            return
        try:
            payload = {
                "kind": "tool_call",
                "tool_name": tool_name,
                "inputs": _sanitize(inputs),
                "outputs": _sanitize(outputs),
                "metrics": _sanitize(metrics or {}),
                "timestamp": time.time(),
            }
            self._append(run_id, "tool_calls", payload)
        except Exception as exc:
            self._warn(f"Tool trace failed: {exc}")

    def log_eval_scores(self, run_id: str | None, scores: dict, warnings: list[str]) -> None:
        if not self.enabled():
            return
        try:
            payload = {
                "kind": "eval_scores",
                "scores": _sanitize(scores),
                "warnings": _sanitize(warnings),
                "timestamp": time.time(),
            }
            if run_id and run_id in _LOCAL_RUNS:
                _LOCAL_RUNS[run_id]["eval_scores"] = payload
            self._append_case_event(run_id, payload)
        except Exception as exc:
            self._warn(f"Eval trace failed: {exc}")

    def finish_run(self, run_id: str | None, status: str, summary: dict) -> None:
        if not self.enabled():
            return
        try:
            payload = {
                "kind": "run_finish",
                "run_id": run_id,
                "status": status,
                "summary": _sanitize(summary),
                "timestamp": time.time(),
            }
            if run_id and run_id in _LOCAL_RUNS:
                _LOCAL_RUNS[run_id]["status"] = status
                _LOCAL_RUNS[run_id]["summary"] = payload["summary"]
                _LOCAL_RUNS[run_id]["finished_at"] = time.time()
                _LOCAL_RUNS[run_id]["warnings"] = self.trace_warnings()
                _LOCAL_RUNS[run_id]["trace"] = self.trace_info(run_id)
                _persist_run(run_id)
            self._append_case_event(run_id, payload)
        except Exception as exc:
            self._warn(f"Trace finish failed: {exc}")

    def trace_warnings(self) -> list[str]:
        return _dedupe([*self.warnings, *_TRACE_WARNINGS])

    def trace_info(self, run_id: str | None = None) -> dict[str, Any]:
        case_id = None
        storage_path = None
        if run_id and run_id in _LOCAL_RUNS:
            case_id = _LOCAL_RUNS[run_id].get("case_id")
            storage_path = _run_file_path(case_id or "unknown", run_id)
            if storage_path and not storage_path.exists():
                storage_path = None
        enabled = self.enabled()
        return {
            "backend": "local",
            "enabled": enabled,
            "status": "local" if enabled else "disabled",
            "project": "local-traces",
            "project_url": get_project_url(case_id),
            "run_id": run_id,
            "run_url": get_run_url(run_id, case_id),
            "storage_path": str(storage_path) if storage_path else None,
            "warnings": self.trace_warnings(),
        }

    def weave_warnings(self) -> list[str]:
        return self.trace_warnings()

    def weave_info(self, run_id: str | None = None) -> dict[str, Any]:
        """Backward-compatible alias for API responses still keyed as ``weave``."""
        return self.trace_info(run_id)

    def _append(self, run_id: str | None, key: str, payload: dict[str, Any]) -> None:
        if run_id and run_id in _LOCAL_RUNS:
            _LOCAL_RUNS[run_id].setdefault(key, []).append(payload)
        self._append_case_event(run_id, payload)

    def _append_case_event(self, run_id: str | None, payload: dict[str, Any]) -> None:
        case_id = _LOCAL_RUNS.get(run_id or "", {}).get("case_id")
        if case_id:
            _LOCAL_TRACES.setdefault(case_id, []).append(payload)

    def _warn(self, message: str) -> None:
        self.warnings.append(message)
        _TRACE_WARNINGS.append(message)


class TraceContext:
    """Backward-compatible per-agent trace recorder."""

    def __init__(self, case_id: str, agent_name: str) -> None:
        self.case_id = case_id
        self.agent_name = agent_name
        self.trace_id = str(uuid.uuid4())
        self.steps: list[dict[str, Any]] = []
        self._start_time = time.time()

    def record_tool(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        duration_ms: Optional[float] = None,
    ) -> None:
        self.steps.append(
            {
                "tool": tool_name,
                "inputs": _sanitize(inputs),
                "outputs": _sanitize(outputs),
                "duration_ms": duration_ms or 0.0,
                "timestamp": time.time(),
            }
        )

    def finish(self, status: str, outputs: dict[str, Any], score: float) -> dict[str, Any]:
        duration_ms = (time.time() - self._start_time) * 1000
        trace = {
            "trace_id": self.trace_id,
            "case_id": self.case_id,
            "agent": self.agent_name,
            "status": status,
            "duration_ms": round(duration_ms, 1),
            "steps": self.steps,
            "score": score,
            "outputs_summary": _sanitize(outputs),
        }
        _LOCAL_TRACES.setdefault(self.case_id, []).append(trace)
        return trace


def get_trace_sink() -> TraceSink:
    return TraceSink()


def _run_file_path(case_id: str, run_id: str) -> Path:
    return trace_dir() / case_id / f"{run_id}.json"


def _persist_run(run_id: str) -> None:
    run = _LOCAL_RUNS.get(run_id)
    if not run:
        return
    case_id = str(run.get("case_id") or "unknown")
    path = _run_file_path(case_id, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, indent=2, default=str), encoding="utf-8")


def _load_case_traces_from_disk(case_id: str) -> list[dict[str, Any]]:
    case_dir = trace_dir() / case_id
    if not case_dir.is_dir():
        return []
    events: list[dict[str, Any]] = []
    for path in sorted(case_dir.glob("*.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        run_id = run.get("run_id")
        events.append(
            {
                "kind": "run_start",
                "run_id": run_id,
                "run_type": run.get("run_type"),
                "metadata": run.get("metadata"),
            }
        )
        for stage in run.get("stages") or []:
            events.append({**stage, "run_id": run_id})
        for tool in run.get("tool_calls") or []:
            events.append({**tool, "run_id": run_id})
        if run.get("eval_scores"):
            events.append({**run["eval_scores"], "run_id": run_id})
        events.append(
            {
                "kind": "run_finish",
                "run_id": run_id,
                "status": run.get("status"),
                "summary": run.get("summary"),
            }
        )
        if run_id:
            _LOCAL_RUNS.setdefault(run_id, run)
    return events


def get_traces(case_id: str) -> list[dict[str, Any]]:
    if case_id not in _LOCAL_TRACES:
        _LOCAL_TRACES[case_id] = _load_case_traces_from_disk(case_id)
    return _LOCAL_TRACES.get(case_id, [])


def get_run(run_id: str | None) -> dict[str, Any] | None:
    if not run_id:
        return None
    if run_id in _LOCAL_RUNS:
        return _LOCAL_RUNS[run_id]
    for path in trace_dir().rglob(f"{run_id}.json"):
        try:
            run = json.loads(path.read_text(encoding="utf-8"))
            _LOCAL_RUNS[run_id] = run
            return run
        except (OSError, json.JSONDecodeError):
            continue
    return None


def get_latest_run(case_id: str) -> dict[str, Any] | None:
    runs = [r for r in _LOCAL_RUNS.values() if r.get("case_id") == case_id]
    if not runs:
        for path in sorted((trace_dir() / case_id).glob("*.json"), reverse=True) if (trace_dir() / case_id).is_dir() else []:
            try:
                run = json.loads(path.read_text(encoding="utf-8"))
                runs.append(run)
                _LOCAL_RUNS[run["run_id"]] = run
            except (OSError, json.JSONDecodeError, KeyError):
                continue
    if not runs:
        return None
    return sorted(runs, key=lambda r: r.get("started_at", 0), reverse=True)[0]


def get_project_url(case_id: str | None = None) -> str | None:
    explicit = os.environ.get("NEXT_PUBLIC_TRACE_VIEWER_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    base = os.environ.get("NEXT_PUBLIC_API_BASE", "http://localhost:8000/api/v1").rstrip("/")
    if case_id:
        return f"{base}/cases/{case_id}/trace"
    return f"{base}/health"


def get_run_url(run_id: str | None, case_id: str | None = None) -> str | None:
    if case_id:
        return get_project_url(case_id)
    if run_id:
        run = get_run(run_id)
        if run and run.get("case_id"):
            return get_project_url(str(run["case_id"]))
    return None


def trace_status(run_id: str | None = None) -> dict[str, Any]:
    return TraceSink().trace_info(run_id)


def weave_status(run_id: str | None = None) -> dict[str, Any]:
    return trace_status(run_id)


def _sanitize(obj: Any, max_list_len: int = 40, depth: int = 0) -> Any:
    if depth > 5:
        return "[truncated-depth]"
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            key_str = str(key)
            if key_str.lower() in _PII_KEYS:
                if key_str.lower() == "bytes":
                    out[key_str] = f"[redacted-bytes:{len(value) if hasattr(value, '__len__') else 'unknown'}]"
                else:
                    out[key_str] = "[redacted]"
                continue
            if key_str == "files" and isinstance(value, list):
                out[key_str] = [_file_metadata(item) for item in value]
                continue
            out[key_str] = _sanitize(value, max_list_len=max_list_len, depth=depth + 1)
        return out
    if isinstance(obj, list):
        trimmed = obj[:max_list_len]
        result = [_sanitize(v, max_list_len=max_list_len, depth=depth + 1) for v in trimmed]
        if len(obj) > max_list_len:
            result.append(f"... ({len(obj) - max_list_len} more)")
        return result
    if isinstance(obj, bytes):
        return f"[redacted-bytes:{len(obj)}]"
    if isinstance(obj, str):
        redacted = redact_pii(obj)
        redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[redacted-ssn]", redacted)
        if len(redacted) > 280:
            return redacted[:280] + "..."
        return redacted
    return obj


def _file_metadata(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"file": "[metadata-unavailable]"}
    return {
        "file_id": item.get("file_id"),
        "filename": item.get("filename"),
        "content_type": item.get("content_type"),
        "size_bytes": len(item.get("bytes", b"")) if item.get("bytes") is not None else item.get("size_bytes"),
    }


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def score_extraction_completeness(extracted: dict) -> float:
    from python.hearttwin.tools.scoring import score_extraction_completeness as score

    return score(extracted)


def score_hallucination_risk(agent_outputs: dict, state: dict) -> float:
    from python.hearttwin.tools.scoring import score_hallucination_risk as score

    return score(agent_outputs, state)


def score_physiological_plausibility(state: dict) -> float:
    from python.hearttwin.tools.scoring import score_physiological_plausibility as score

    return score(state)


def score_safety_compliance(outputs: dict) -> float:
    from python.hearttwin.tools.scoring import score_safety_compliance as score

    return score(outputs)


def score_visualization_readiness(state: dict) -> float:
    from python.hearttwin.tools.scoring import score_visualization_readiness as score

    return score(state)
