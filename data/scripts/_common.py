"""Shared helpers for the HeartTwin CareGuard data pipeline.

Every numbered stage script imports from here. Kept import-cheap: heavy libs
(pandas/pyarrow/wfdb/...) are imported lazily inside the functions that need them
so that `00_check_environment.py` can run under a bare interpreter.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Canonical paths (all derived from this file's location: data/scripts/_common.py)
# --------------------------------------------------------------------------- #
SCRIPTS_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPTS_DIR.parent                       # .../data
REPO_ROOT = DATA_DIR.parent                          # repo root

RAW = DATA_DIR / "raw"
STAGING = DATA_DIR / "staging"
CASES = DATA_DIR / "cases"
COHORT = DATA_DIR / "cohort"
ANALYSIS = DATA_DIR / "analysis"
CHARTS = ANALYSIS / "charts"
LOGS = DATA_DIR / "logs"
CACHE = DATA_DIR / "cache"
QUARANTINE = DATA_DIR / "quarantine"

RAW_EICU = RAW / "eicu-demo"
RAW_PTBXL = RAW / "ptb-xl"
RAW_MIMIC = RAW / "mimic-demo"
RAW_SYNTHEA = RAW / "synthea"

CONFIG_PATH = DATA_DIR / "pipeline_config.yaml"
SOURCE_MANIFEST = DATA_DIR / "source_manifest.json"

ALL_DIRS = [
    RAW, STAGING, CASES, COHORT, ANALYSIS, CHARTS, LOGS, CACHE, QUARANTINE,
    RAW_EICU, RAW_PTBXL, RAW_MIMIC, RAW_SYNTHEA,
    STAGING / "eicu", STAGING / "ptb-xl", STAGING / "medication-normalization",
    STAGING / "fhir", STAGING / "reports",
]

# FHIR code-system URIs — MUST match python/hearttwin/careguard/constants.py.
CODE_SYSTEMS = {
    "snomed": "http://snomed.info/sct",
    "loinc": "http://loinc.org",
    "rxnorm": "http://www.nlm.nih.gov/research/umls/rxnorm",
    "icd10": "http://hl7.org/fhir/sid/icd-10-cm",
    "ucum": "http://unitsofmeasure.org",
}
CAREGUARD_TAG_SYSTEM = "https://hearttwin.local/careguard"


def ensure_dirs() -> None:
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Time — a single UTC clock used everywhere for reproducible provenance stamps.
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# Logging — console + rotating-ish per-stage file.
# --------------------------------------------------------------------------- #
def get_logger(stage: str) -> logging.Logger:
    LOGS.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(stage)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    fh = logging.FileHandler(LOGS / f"{stage}.log")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.propagate = False
    return logger


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    import yaml  # lazy
    with open(CONFIG_PATH) as fh:
        return yaml.safe_load(fh)


def load_config_safe():
    """Like load_config but tolerates a missing PyYAML (used by stage 00 on the
    bare interpreter before the venv exists). Returns None if unavailable."""
    try:
        return load_config()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# JSON helpers
# --------------------------------------------------------------------------- #
def write_json(path: Path, obj, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=indent, default=str)
    os.replace(tmp, path)


def read_json(path: Path):
    with open(path) as fh:
        return json.load(fh)


def write_ndjson(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Checksums
# --------------------------------------------------------------------------- #
def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def parse_sha256sums(path: Path) -> dict[str, str]:
    """Parse a PhysioNet SHA256SUMS.txt into {relative_path: hexdigest}."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # format: "<hex>  <path>"  (two spaces)
            parts = line.split(None, 1)
            if len(parts) == 2:
                out[parts[1].strip()] = parts[0].strip().lower()
    return out


# --------------------------------------------------------------------------- #
# Robust HTTP download with resume + retries. Uses urllib (stdlib) so it works
# before third-party deps are installed.
# --------------------------------------------------------------------------- #
def download(url: str, dest: Path, *, logger: logging.Logger | None = None,
             retries: int = 4, timeout: int = 60, resume: bool = True,
             expect_min_bytes: int = 1) -> dict:
    """Download `url` to `dest` atomically via a .partial file with HTTP-range resume.

    Returns a manifest fragment. Raises on unrecoverable failure — never leaves a
    truncated file at the final path.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    if dest.exists() and dest.stat().st_size >= expect_min_bytes:
        if logger:
            logger.info("skip (exists): %s", dest.name)
        return {"url": url, "local_path": str(dest), "downloaded_at": now_iso(),
                "sha256": sha256_file(dest), "bytes": dest.stat().st_size,
                "http_status": 200, "resumed": False, "skipped": True}

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            existing = partial.stat().st_size if (resume and partial.exists()) else 0
            req = urllib.request.Request(url, headers={"User-Agent": "careguard-data/1.0"})
            if existing:
                req.add_header("Range", f"bytes={existing}-")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                mode = "ab" if (existing and status == 206) else "wb"
                if mode == "wb":
                    existing = 0
                with open(partial, mode) as fh:
                    while True:
                        block = resp.read(1 << 20)
                        if not block:
                            break
                        fh.write(block)
            size = partial.stat().st_size
            if size < expect_min_bytes:
                raise IOError(f"truncated download ({size} bytes) for {url}")
            os.replace(partial, dest)
            if logger:
                logger.info("downloaded %s (%d bytes, http %s, attempt %d)",
                            dest.name, size, status, attempt)
            return {"url": url, "local_path": str(dest), "downloaded_at": now_iso(),
                    "sha256": sha256_file(dest), "bytes": size,
                    "http_status": status, "resumed": bool(existing), "skipped": False}
        except (urllib.error.URLError, urllib.error.HTTPError, IOError, TimeoutError) as e:
            last_err = e
            if logger:
                logger.warning("attempt %d/%d failed for %s: %s", attempt, retries, url, e)
            time.sleep(min(2 ** attempt, 15))
    raise RuntimeError(f"failed to download {url} after {retries} attempts: {last_err}")


# --------------------------------------------------------------------------- #
# Provenance object builder — the single source of truth for the shape used
# across FHIR extensions, per-fact provenance, and case provenance.json.
# --------------------------------------------------------------------------- #
def make_provenance(*, source_dataset: str, source_table: str, source_row_id,
                    source_column: str, value=None, assertion_type: str = "recorded",
                    confidence: float = 1.0, mapping_rule_version: str = "careguard-data.v1",
                    normalization_method: str | None = None) -> dict:
    prov = {
        "source_dataset": source_dataset,
        "source_table": source_table,
        "source_row_id": str(source_row_id) if source_row_id is not None else None,
        "source_column": source_column,
        "assertion_type": assertion_type,          # recorded|derived_deterministically|missing
        "confidence": round(float(confidence), 3),
        "mapping_rule_version": mapping_rule_version,
        "conversion_timestamp": now_iso(),
    }
    if value is not None:
        prov["source_value"] = str(value)
    if normalization_method:
        prov["normalization_method"] = normalization_method
    return prov


# --------------------------------------------------------------------------- #
# Case id / path helpers
# --------------------------------------------------------------------------- #
def case_id(n: int) -> str:
    return f"case-{n:06d}"


def case_dir(n: int) -> Path:
    return CASES / case_id(n)


def free_gb(path: Path) -> float:
    st = os.statvfs(path)
    return (st.f_bavail * st.f_frsize) / (1024 ** 3)
