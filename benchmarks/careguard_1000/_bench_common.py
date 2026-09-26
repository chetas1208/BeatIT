"""Shared helpers for the CareGuard 1,000-case benchmark.

Deliberately dependency-light: pathlib, json, os, and a tiny .env loader so
every runner/analysis script resolves the same paths, config, and API key.

Nothing here calls a model or grades an output. It is pure plumbing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent.parent
DATA_ROOT = Path(
    os.environ.get("BENCHMARK_DATA_ROOT", str(REPO_ROOT / "data"))
)
CASES_DIR = DATA_ROOT / "cases"

CONFIG_DIR = BENCH_DIR / "config"
SCHEMA_DIR = BENCH_DIR / "schemas"
PROMPT_DIR = BENCH_DIR / "prompts"
RESULTS_DIR = BENCH_DIR / "results"
REFERENCE_DIR = BENCH_DIR / "reference"

for _d in (
    RESULTS_DIR / "raw",
    RESULTS_DIR / "normalized",
    RESULTS_DIR / "graded",
    RESULTS_DIR / "aggregate",
    RESULTS_DIR / "statistics",
    RESULTS_DIR / "failures",
    RESULTS_DIR / "examples",
    RESULTS_DIR / "charts",
    RESULTS_DIR / "reports",
):
    _d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# .env loader (no python-dotenv dependency)
# --------------------------------------------------------------------------
def load_env(env_path: Path | None = None) -> dict[str, str]:
    """Parse KEY=VALUE lines from the repo .env into os.environ if unset.

    Returns the parsed dict. Existing os.environ values win (so a shell export
    overrides the file), matching the standard dotenv precedence.
    """
    env_path = env_path or (REPO_ROOT / ".env")
    parsed: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip('"').strip("'")
            parsed[key] = val
            os.environ.setdefault(key, val)
    return parsed


def get_api_key() -> str:
    load_env()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not found in environment or repo .env"
        )
    return key


# --------------------------------------------------------------------------
# Config / schema loaders
# --------------------------------------------------------------------------
def _read_yaml(path: Path) -> Any:
    """Minimal YAML reader that avoids a PyYAML dependency.

    The benchmark config files are intentionally written in a restricted YAML
    subset (mappings, lists, scalars, comments) so this loader is sufficient.
    Falls back to PyYAML if available for anything richer.
    """
    try:
        import yaml  # type: ignore

        return yaml.safe_load(path.read_text())
    except Exception:
        pass
    return _tiny_yaml(path.read_text())


def _coerce_scalar(tok: str) -> Any:
    t = tok.strip()
    if t == "" or t in ("~", "null", "None"):
        return None
    if t in ("true", "True", "yes"):
        return True
    if t in ("false", "False", "no"):
        return False
    if (t.startswith('"') and t.endswith('"')) or (
        t.startswith("'") and t.endswith("'")
    ):
        return t[1:-1]
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    return t


def _tiny_yaml(text: str) -> Any:
    """Parse the restricted YAML subset used by this benchmark's configs.

    Supports nested mappings by indentation, inline lists ``[a, b]``, block
    lists (``- item``), and ``key: value`` scalars. Not a general YAML parser.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    def parent_for(indent: int) -> Any:
        while stack and stack[-1][0] >= indent:
            stack.pop()
        return stack[-1][1]

    lines = [ln.rstrip() for ln in text.splitlines()]
    for raw in lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        content = raw.strip()
        container = parent_for(indent)

        if content.startswith("- "):
            item = content[2:].strip()
            if not isinstance(container, list):
                # replace last mapping value slot with a list
                pass
            if ":" in item and not item.startswith(("[", "{", '"', "'")):
                k, v = item.split(":", 1)
                obj: dict[str, Any] = {k.strip(): _parse_value(v.strip())}
                container.append(obj)
                stack.append((indent, obj))
            else:
                container.append(_coerce_scalar(item))
            continue

        if ":" in content:
            k, v = content.split(":", 1)
            k, v = k.strip(), v.strip()
            if v == "":
                # Could be a nested map or a block list; default to map,
                # switch to list lazily when a '- ' child appears.
                new_map: dict[str, Any] = {}
                new_list: list[Any] = []
                # Peek is complex; store a hybrid: use list only if children
                # are '- ' items. We create a map and convert if needed.
                container[k] = new_map
                stack.append((indent, new_map))
                # Register a possible list sibling.
                _LIST_CANDIDATES[id(new_map)] = (container, k, new_list)
            else:
                container[k] = _parse_value(v)
    return _resolve_list_candidates(root)


_LIST_CANDIDATES: dict[int, tuple[Any, str, list]] = {}


def _resolve_list_candidates(node: Any) -> Any:
    return node


def _parse_value(v: str) -> Any:
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(x) for x in _split_top(inner)]
    return _coerce_scalar(v)


def _split_top(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def load_config(name: str) -> dict[str, Any]:
    """Load a config YAML by base name (without extension) from config/."""
    for ext in (".yaml", ".yml"):
        p = CONFIG_DIR / f"{name}{ext}"
        if p.exists():
            return _read_yaml(p) or {}
    raise FileNotFoundError(f"config {name} not found in {CONFIG_DIR}")


def load_schema(name: str) -> dict[str, Any]:
    p = SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(p.read_text())


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text()


# --------------------------------------------------------------------------
# JSONL / NDJSON helpers
# --------------------------------------------------------------------------
def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")


# --------------------------------------------------------------------------
# Pricing (USD per 1M tokens). Standard Messages API rates.
# Sonnet 4.5 and Sonnet 4.6 share the same listed standard price.
# --------------------------------------------------------------------------
PRICING = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0,
                                   "cache_write": 3.75, "cache_read": 0.30},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0,
                          "cache_write": 3.75, "cache_read": 0.30},
}


def cost_usd(model: str, usage: dict[str, int], batch: bool = False) -> float:
    """Compute request cost in USD from a usage dict.

    usage keys: input_tokens, output_tokens, cache_creation_input_tokens,
    cache_read_input_tokens (any may be absent). Batch API is half price.
    """
    p = PRICING.get(model)
    if not p:
        return 0.0
    it = usage.get("input_tokens", 0) or 0
    ot = usage.get("output_tokens", 0) or 0
    cw = usage.get("cache_creation_input_tokens", 0) or 0
    cr = usage.get("cache_read_input_tokens", 0) or 0
    total = (
        it * p["input"]
        + ot * p["output"]
        + cw * p["cache_write"]
        + cr * p["cache_read"]
    ) / 1_000_000.0
    return total * (0.5 if batch else 1.0)
