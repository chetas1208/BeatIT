"""Agent 4 — Guideline Evidence.

Searches the approved local corpus first, retrieves exact passages with version/
date/section, checks freshness, and ABSTAINS when a passage cannot be verified.
Never grounds a recommendation on model memory.
"""

from __future__ import annotations

from datetime import date

from python.hearttwin.careguard.agents.base import StageTimer, make_stage_result
from python.hearttwin.careguard.constants import STAGE_GUIDELINE_EVIDENCE
from python.hearttwin.careguard.evidence import freshness, retriever
from python.hearttwin.careguard.schemas import CareGuardContext, CareGuardStageResult, PatientContext

# Fixed reference date for freshness (deterministic; passed explicitly, no live clock).
_REFERENCE_DATE = date(2026, 7, 18)


def _query_terms(pc: PatientContext, scope: str) -> set[str]:
    terms: set[str] = set()
    for f in pc.active_cardiac_problem + pc.active_non_cardiac_conditions:
        terms.update(str(f.display or "").lower().split())
    for m in pc.medications:
        terms.update(str(m.display or "").lower().split())
    terms.update((scope or "").lower().split())
    terms.update({"hfref", "potassium", "renal", "monitoring", "mra", "gdmt"})
    return {t.strip(",.;:()") for t in terms if len(t) > 2}


async def run(ctx: CareGuardContext) -> CareGuardStageResult:
    timer = StageTimer()
    pc_dict = ctx.prior_stage_outputs.get("patient_context")
    pc = PatientContext.model_validate(pc_dict) if pc_dict else PatientContext(case_id=ctx.case_id)
    scope = ctx.prior_stage_outputs.get("review_scope", ctx.clinical_question)

    citations, warnings = retriever.retrieve_guidelines(_query_terms(pc, scope))

    stale: list[str] = []
    fresh_cites = []
    for c in citations:
        fr = freshness.assess(c.model_dump(), today=_REFERENCE_DATE)
        if fr["stale"] or fr["undated"] or fr["missing_version"]:
            stale.append(f"{c.source_id}: {'; '.join(fr['reasons'])}")
        else:
            fresh_cites.append(c)

    if not fresh_cites:
        return make_stage_result(
            ctx=ctx, stage_id=STAGE_GUIDELINE_EVIDENCE, timer=timer, status="warning",
            structured_output={
                "citations": [],
                "abstained": True,
                "abstain_reason": "No fresh, verifiable guideline passage available.",
                "stale_or_unverifiable": stale,
            },
            warnings=warnings + (["stale/unverifiable sources excluded"] if stale else []),
            confidence=0.2,
        )

    tools = [{"tool": "search_local_guidelines", "matched": len(fresh_cites)}]
    return make_stage_result(
        ctx=ctx, stage_id=STAGE_GUIDELINE_EVIDENCE, timer=timer, status="completed",
        structured_output={
            "citations": [c.model_dump() for c in fresh_cites],
            "abstained": False,
            "stale_or_unverifiable": stale,
        },
        source_ids=[c.source_id for c in fresh_cites],
        tools_called=tools,
        warnings=warnings,
        confidence=0.85,
    )
