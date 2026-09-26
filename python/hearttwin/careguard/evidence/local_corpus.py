"""Load the approved local evidence corpus and compute per-passage hashes."""

from __future__ import annotations

import hashlib
import json
import pathlib
from functools import lru_cache
from typing import Any

# evidence/local_corpus.py → parents: [0]=evidence [1]=careguard [2]=hearttwin
# [3]=python [4]=repo root. Corpus lives at <repo>/fixtures/careguard/corpus/.
_CORPUS_PATH = (
    pathlib.Path(__file__).resolve().parents[4] / "fixtures" / "careguard" / "corpus" / "local_corpus.json"
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    if not _CORPUS_PATH.exists():
        return {"entries": [], "drug_labels": []}
    return json.loads(_CORPUS_PATH.read_text())


def guideline_entries() -> list[dict[str, Any]]:
    out = []
    for e in _load().get("entries", []):
        e = dict(e)
        e["sha256"] = _sha256(e.get("passage", ""))
        e["local_path"] = str(_CORPUS_PATH)
        out.append(e)
    return out


def drug_labels() -> list[dict[str, Any]]:
    out = []
    for lbl in _load().get("drug_labels", []):
        lbl = dict(lbl)
        blob = json.dumps(lbl.get("sections", {}), sort_keys=True)
        lbl["sha256"] = _sha256(blob)
        lbl["local_path"] = str(_CORPUS_PATH)
        out.append(lbl)
    return out


_MED_SOURCES_PATH = _CORPUS_PATH.parent / "medication_sources.json"


@lru_cache(maxsize=1)
def _load_med_sources() -> dict[str, Any]:
    if not _MED_SOURCES_PATH.exists():
        return {}
    return json.loads(_MED_SOURCES_PATH.read_text())


def med_sources() -> dict[str, Any]:
    return _load_med_sources()


def corpus_present() -> bool:
    return _CORPUS_PATH.exists()


def reset_cache() -> None:
    _load.cache_clear()
