#!/usr/bin/env python3
"""Stage 07 — normalize unique medication strings via RxNorm + enrich with
openFDA drug-label evidence. Every unique string is normalized once and cached
(cache/medications/, cache/labels/), so re-runs are offline-fast and idempotent.

Evidence is STORED, never interpreted. This stage never calls a drug safe/unsafe
and never makes a patient-specific recommendation (that is the runtime medication
engine's job). Respects a polite rate limit.
"""
from __future__ import annotations

import hashlib
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

ASM = C.STAGING / "eicu" / "assembled"
OUT = C.STAGING / "medication-normalization"
MED_CACHE = C.CACHE / "medications"
LABEL_CACHE = C.CACHE / "labels"


def _key(s: str) -> str:
    return hashlib.sha1(s.lower().strip().encode()).hexdigest()[:16]


def clean_name(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"\b\d+(\.\d+)?\s?(mg|mcg|g|ml|unit|units|meq|%|mg/ml|mcg/ml)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(tablet|capsule|injection|inj|soln|solution|iv|po|oral|vial|syringe|"
               r"premix|bag|drip|infusion|er|xr|sr)\b", " ", s, flags=re.I)
    s = re.sub(r"[^a-zA-Z0-9\-/ ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class Client:
    def __init__(self, cfg, log):
        import requests
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "careguard-data/1.0"})
        api = cfg["apis"]
        self.rx = api["rxnorm_base"]
        self.fda = api["openfda_base"]
        self.sleep = api["rate_limit_sleep_seconds"]
        self.timeout = api["request_timeout_seconds"]
        self.log = log
        self.calls = 0
        self.label_calls = 0

    def get(self, url, params=None):
        for attempt in range(3):
            try:
                r = self.s.get(url, params=params, timeout=self.timeout)
                self.calls += 1
                time.sleep(self.sleep)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 404:
                    return None
                if r.status_code == 429:
                    time.sleep(2 ** attempt + 1)
                    continue
                return None
            except Exception as e:
                self.log.debug("http error %s: %s", url, e)
                time.sleep(1 + attempt)
        return None


def rxnorm_normalize(cli: Client, cleaned: str) -> dict:
    out = {"rxcui": None, "normalized_name": None, "tty": None, "ingredients": [],
           "confidence": 0.0, "unresolved": True, "ambiguity": None}
    if not cleaned:
        return out
    # exact first
    j = cli.get(f"{cli.rx}/rxcui.json", {"name": cleaned, "search": 1})
    rxcui = None
    if j and j.get("idGroup", {}).get("rxnormId"):
        rxcui = j["idGroup"]["rxnormId"][0]
        out["confidence"] = 1.0
    else:
        j = cli.get(f"{cli.rx}/approximateTerm.json", {"term": cleaned, "maxEntries": 1})
        cand = (j or {}).get("approximateGroup", {}).get("candidate", [])
        if cand:
            rxcui = cand[0].get("rxcui")
            try:
                out["confidence"] = round(float(cand[0].get("score", 0)) / 100.0, 3)
            except (TypeError, ValueError):
                out["confidence"] = 0.5
    if not rxcui:
        return out
    out["rxcui"] = rxcui
    out["unresolved"] = False
    props = cli.get(f"{cli.rx}/rxcui/{rxcui}/properties.json")
    if props and props.get("properties"):
        p = props["properties"]
        out["normalized_name"] = p.get("name")
        out["tty"] = p.get("tty")
    rel = cli.get(f"{cli.rx}/rxcui/{rxcui}/related.json", {"tty": "IN"})
    for grp in (rel or {}).get("relatedGroup", {}).get("conceptGroup", []) or []:
        for cp in grp.get("conceptProperties", []) or []:
            out["ingredients"].append({"rxcui": cp.get("rxcui"), "name": cp.get("name")})
    return out


def openfda_label(cli: Client, rxcui: str, name: str | None = None) -> dict | None:
    if not rxcui:
        return None
    cache = LABEL_CACHE / f"{rxcui}.json"
    if cache.exists():
        return C.read_json(cache)
    # Product labels index by generic/substance name, not ingredient rxcui, so
    # search by the normalized ingredient name; fall back to the product rxcui.
    res = None
    if name:
        term = name.split()[0].lower() if name else ""
        j = cli.get(f"{cli.fda}/drug/label.json",
                    {"search": f'openfda.generic_name:"{term}"', "limit": 1})
        res = (j or {}).get("results")
    if not res:
        j = cli.get(f"{cli.fda}/drug/label.json",
                    {"search": f"openfda.rxcui:{rxcui}", "limit": 1})
        res = (j or {}).get("results")
    if not res:
        C.write_json(cache, {"rxcui": rxcui, "found": False})
        return {"rxcui": rxcui, "found": False}
    r = res[0]
    def _first(k):
        v = r.get(k)
        return (v[0][:1200] if isinstance(v, list) and v else None)
    label = {
        "rxcui": rxcui, "found": True,
        "label_id": r.get("id"),
        "set_id": (r.get("openfda", {}) or {}).get("spl_set_id", [None])[0],
        "effective_time": r.get("effective_time"),
        "boxed_warning": _first("boxed_warning"),
        "contraindications": _first("contraindications"),
        "warnings_and_precautions": _first("warnings_and_cautions") or _first("warnings"),
        "drug_interactions": _first("drug_interactions"),
        "renal_note": _first("use_in_specific_populations"),
        "pregnancy": _first("pregnancy"),
        "source": "openFDA drug/label",
    }
    C.write_json(cache, label)
    return label


def main() -> None:
    C.ensure_dirs()
    OUT.mkdir(parents=True, exist_ok=True)
    MED_CACHE.mkdir(parents=True, exist_ok=True)
    LABEL_CACHE.mkdir(parents=True, exist_ok=True)
    log = C.get_logger("07_normalize_medications")
    cfg = C.load_config()
    log.info("=== Stage 07: medication normalization ===")

    # collect unique medication strings
    uniq = {}
    for jf in sorted(ASM.glob("*.json")):
        rec = C.read_json(jf)
        for m in rec.get("medications", []):
            t = (m.get("text") or "").strip()
            if t:
                uniq.setdefault(t.lower(), t)
    log.info("unique medication strings: %d", len(uniq))

    cap = cfg["apis"].get("max_unique_normalizations", 4000)
    max_labels = cfg["apis"].get("max_openfda_labels", 500)
    offline = "--offline" in sys.argv
    cli = None if offline else Client(cfg, log)

    normalized = {}
    n_new = 0
    for i, (low, orig) in enumerate(sorted(uniq.items())):
        cache = MED_CACHE / f"{_key(low)}.json"
        if cache.exists():
            normalized[low] = C.read_json(cache)
            continue
        if offline or n_new >= cap:
            normalized[low] = {"original_text": orig, "cleaned": clean_name(orig),
                               "rxcui": None, "unresolved": True, "confidence": 0.0,
                               "ingredients": [], "label": None, "skipped": True}
            continue
        cleaned = clean_name(orig)
        norm = rxnorm_normalize(cli, cleaned)
        # openFDA has a ~1000/day unauthenticated cap; bound distinct label lookups.
        # Cached rxcuis are free; only NEW rxcui lookups count against the budget.
        rxcui = norm.get("rxcui")
        label = None
        if rxcui:
            if (LABEL_CACHE / f"{rxcui}.json").exists() or cli.label_calls < max_labels:
                if not (LABEL_CACHE / f"{rxcui}.json").exists():
                    cli.label_calls += 1
                label = openfda_label(cli, rxcui, norm.get("normalized_name") or cleaned)
        rec = {"original_text": orig, "cleaned": cleaned, **norm, "label": label,
               "normalization_method": "rxnorm_exact" if norm["confidence"] == 1.0
               else "rxnorm_approximate", "normalized_at": C.now_iso()}
        C.write_json(cache, rec)
        normalized[low] = rec
        n_new += 1
        if n_new % 25 == 0:
            log.info("normalized %d new (%d api calls)", n_new, cli.calls if cli else 0)

    resolved = sum(1 for r in normalized.values() if not r.get("unresolved"))
    with_label = sum(1 for r in normalized.values() if (r.get("label") or {}).get("found"))
    C.write_json(OUT / "normalized.json", normalized)
    C.write_json(OUT / "normalization_summary.json", {
        "generated_at": C.now_iso(), "unique_strings": len(uniq),
        "resolved": resolved, "unresolved": len(uniq) - resolved,
        "resolution_rate": round(resolved / max(len(uniq), 1), 4),
        "with_label_evidence": with_label,
        "api_calls": cli.calls if cli else 0, "offline": offline,
    })
    log.info("=== Stage 07 complete: %d/%d resolved, %d with label ===",
             resolved, len(uniq), with_label)
    print(f"med_resolved={resolved}/{len(uniq)} labels={with_label}")


if __name__ == "__main__":
    main()
