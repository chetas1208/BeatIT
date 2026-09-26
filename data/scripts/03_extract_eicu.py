#!/usr/bin/env python3
"""Stage 03 — decompress the eICU demo SQLite and extract relevant tables to
staging parquet (read-only; the original DB is never mutated).

Robust to table/column name casing: everything is resolved case-insensitively
from sqlite_master + PRAGMA table_info, so the script works whether the demo
build uses `vitalPeriodic` or `vitalperiodic`.
"""
from __future__ import annotations

import gzip
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

GZ = C.RAW_EICU / "eicu_v2_0_1.sqlite3.gz"
DB = C.RAW_EICU / "eicu_v2_0_1.sqlite3"
STAGE = C.STAGING / "eicu"

# Logical table -> columns we care about (None = all). Big tables get a column
# subset so the parquet stays small; keys resolved case-insensitively.
WANTED = {
    "patient": None,
    "diagnosis": None,
    "pasthistory": None,
    "admissiondx": None,
    "medication": None,
    "admissiondrug": None,
    "infusiondrug": ["patientunitstayid", "infusionoffset", "drugname", "drugrate",
                     "infusionrate", "drugamount", "volumeoffluid"],
    "allergy": None,
    "lab": ["patientunitstayid", "labresultoffset", "labname", "labresult",
            "labresulttext", "labmeasurenamesystem", "labtypeid"],
    "vitalperiodic": ["patientunitstayid", "observationoffset", "temperature", "sao2",
                      "heartrate", "respiration", "systemicsystolic", "systemicdiastolic",
                      "systemicmean"],
    "vitalaperiodic": ["patientunitstayid", "observationoffset", "noninvasivesystolic",
                       "noninvasivediastolic", "noninvasivemean"],
    "treatment": None,
    "note": ["patientunitstayid", "noteoffset", "notetype", "notepath", "notevalue"],
    "careplangeneral": None,
    "careplangoal": None,
    "physicalexam": ["patientunitstayid", "physicalexamoffset", "physicalexampath",
                     "physicalexamvalue", "physicalexamtext"],
    "respiratorycare": None,
    "respiratorycharting": ["patientunitstayid", "respchartoffset", "respchartvaluelabel",
                            "respchartvalue"],
    "nurseassessment": None,
    "nursecare": None,
}


def decompress(log) -> None:
    if DB.exists() and DB.stat().st_size > 1_000_000:
        # quick integrity check
        try:
            con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
            con.execute("SELECT 1 FROM sqlite_master LIMIT 1")
            con.close()
            log.info("sqlite already present & readable: %s", DB.name)
            return
        except sqlite3.DatabaseError:
            log.warning("existing sqlite unreadable; re-decompressing")
    if not GZ.exists():
        sys.exit(f"FATAL: {GZ} not found — run 01_download_sources first")
    tmp = DB.with_suffix(".sqlite3.partial")
    log.info("decompressing %s -> %s", GZ.name, DB.name)
    with gzip.open(GZ, "rb") as fi, open(tmp, "wb") as fo:
        shutil.copyfileobj(fi, fo, length=1 << 20)
    tmp.replace(DB)
    log.info("decompressed to %.1f MB", DB.stat().st_size / 1e6)


def resolve_tables(con) -> dict[str, str]:
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0].lower(): r[0] for r in rows}


def resolve_columns(con, actual: str) -> dict[str, str]:
    rows = con.execute(f'PRAGMA table_info("{actual}")').fetchall()
    return {r[1].lower(): r[1] for r in rows}


def export_table(con, logical, cols, tablemap, log) -> dict:
    import pandas as pd

    actual = tablemap.get(logical)
    dest = STAGE / f"{logical}.parquet"
    if not actual:
        log.warning("table not present in DB: %s", logical)
        return {"table": logical, "present": False, "rows": 0}
    colmap = resolve_columns(con, actual)
    if cols:
        sel = [colmap[c] for c in cols if c in colmap]
        missing = [c for c in cols if c not in colmap]
        if missing:
            log.warning("%s: columns absent %s", logical, missing)
    else:
        sel = list(colmap.values())
    collist = ", ".join(f'"{c}"' for c in sel)
    query = f'SELECT {collist} FROM "{actual}"'

    # Read fully; store every column as nullable string to avoid cross-row type
    # inference conflicts (downstream stages coerce numerics explicitly).
    df = pd.read_sql_query(query, con)
    df.columns = [c.lower() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].astype("string")
    df.to_parquet(dest, index=False)
    log.info("exported %-20s %8d rows -> %s", logical, len(df), dest.name)
    return {"table": logical, "actual_name": actual, "present": True,
            "rows": int(len(df)), "columns": [c.lower() for c in sel]}


def main() -> None:
    C.ensure_dirs()
    STAGE.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("03_extract_eicu")
    log.info("=== Stage 03: extract eICU ===")
    decompress(log)

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        tablemap = resolve_tables(con)
        log.info("DB has %d tables", len(tablemap))
        inventory = []
        for logical, cols in WANTED.items():
            inventory.append(export_table(con, logical, cols, tablemap, log))
        # distinct stays
        pt = tablemap.get("patient")
        n_stays = con.execute(f'SELECT COUNT(DISTINCT patientunitstayid) FROM "{pt}"').fetchone()[0]
    finally:
        con.close()

    C.write_json(STAGE / "inventory.json", {
        "generated_at": C.now_iso(),
        "distinct_patientunitstayid": n_stays,
        "tables": inventory,
    })
    log.info("=== Stage 03 complete: %d distinct stays ===", n_stays)
    print(f"distinct_stays={n_stays}")


if __name__ == "__main__":
    main()
