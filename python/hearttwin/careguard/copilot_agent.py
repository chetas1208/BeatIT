"""CareGuard Copilot — the lower-right analysis agent.

Answers ANALYSIS questions about the current case, grounded strictly in the
case's CareGuard artifacts (patient context, conflicts, evidence, cross-organ
matrix, candidates, critic, care-evaluation). Uses Anthropic when available
(deidentified payload) and falls back to a deterministic analysis otherwise.

Safety: it analyzes and explains; it never diagnoses, doses, prescribes, or tells
a patient what to take. Direct-to-consumer self-treatment questions are reframed.
Every answer carries the clinician-review disclaimer.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from python.hearttwin.careguard.memory import keys, redis_store
from python.hearttwin.careguard.security import deidentify_for_model

DISCLAIMER = "Clinical decision support draft. Clinician review required."

_BLOCK = ("what should i take", "what do i take", "should i stop", "prescribe me",
          "what dose", "how many mg", "diagnose me", "am i going to")


class CopilotAnswer(BaseModel):
    answer: str
    grounded_on: list[str]
    model_used: str | None = None
    used_anthropic: bool = False
    safety_disclaimer: str = DISCLAIMER


async def _load_artifacts(case_id: str) -> dict[str, Any]:
    async def g(k):
        return await redis_store.get_json(k)
    return {
        "patient_context": await g(keys.case_context(case_id)),
        "citations": await g(keys.case_guidelines(case_id)),
        "conflicts": await g(keys.case_contraindications(case_id)),
        "candidates": await g(keys.case_candidates(case_id)),
        "cross_organ_matrix": await g(keys.case_multimorbidity(case_id)),
        "critic": await g(keys.case_critic(case_id)),
        "medication_safety": await g(keys.case_medication_safety(case_id)),
        "simulation": await g(keys.case_simulation(case_id)),
    }


def _grounded_list(art: dict[str, Any]) -> list[str]:
    present = []
    if art.get("patient_context"):
        present.append("patient context")
    if art.get("citations"):
        present.append(f"{len(art['citations'])} guideline citations")
    ms = art.get("medication_safety") or {}
    if ms.get("conflicts"):
        present.append(f"{len(ms['conflicts'])} medication conflicts")
    if ms.get("alternative_candidates"):
        present.append(f"{len(ms['alternative_candidates'])} alternatives")
    if art.get("critic"):
        present.append("clinical critic")
    if art.get("simulation"):
        present.append("DualBeat scenario")
    return present


async def answer(case_id: str, question: str) -> CopilotAnswer:
    art = await _load_artifacts(case_id)
    grounded = _grounded_list(art)

    if any(b in (question or "").lower() for b in _BLOCK):
        return CopilotAnswer(
            answer="I analyze this case's evidence for a clinician — I can't tell a patient what to take, "
                   "a dose, or a diagnosis. Ask me to explain a flagged conflict, the evidence behind a "
                   "candidate, the missing labs, or the cross-organ considerations.",
            grounded_on=grounded,
        )
    if not grounded:
        return CopilotAnswer(
            answer="No CareGuard analysis is loaded for this case yet. Import a bundle and run the review, "
                   "then ask me about the conflicts, evidence, alternatives, or critic findings.",
            grounded_on=[],
        )

    from python.hearttwin.careguard.anthropic import client

    if client.is_available():
        res = _ask_anthropic(question, art)
        if res is not None:
            return res
    return _deterministic_answer(question, art, grounded)


def _ask_anthropic(question: str, art: dict[str, Any]) -> CopilotAnswer | None:
    from python.hearttwin.careguard.anthropic import client

    class _A(BaseModel):
        answer: str

    schema = {"type": "object", "properties": {"answer": {"type": "string"}},
              "required": ["answer"], "additionalProperties": False}
    ms = art.get("medication_safety") or {}
    payload = deidentify_for_model({
        "question": question,
        "patient_context": art.get("patient_context"),
        "conflicts": ms.get("conflicts") or art.get("conflicts"),
        "alternatives": ms.get("alternative_candidates"),
        "citations": art.get("citations"),
        "cross_organ_matrix": art.get("cross_organ_matrix"),
        "critic": art.get("critic"),
        "simulation": art.get("simulation"),
    })
    res = client.generate_structured(
        stage_id="clinical_critic",
        system=("You are the CareGuard analysis copilot. Answer ONLY from the supplied case artifacts; "
                "if the answer is not in them, say so. Give an analysis-based answer that cites the "
                "relevant evidence/conflict/critic finding. Never diagnose, never give a dose, never tell "
                "a patient what to take. Be concise and specific."),
        payload=payload, schema=schema, model_cls=_A,
    )
    if res.ok and res.obj:
        return CopilotAnswer(answer=f"{res.obj['answer']}\n\n{DISCLAIMER}",
                             grounded_on=_grounded_list(art), model_used=res.model_used, used_anthropic=True)
    return None


def _deterministic_answer(question: str, art: dict[str, Any], grounded: list[str]) -> CopilotAnswer:
    q = (question or "").lower()
    ms = art.get("medication_safety") or {}
    conflicts = ms.get("conflicts") or art.get("conflicts") or []
    parts: list[str] = []

    if any(w in q for w in ("conflict", "contraindicat", "risk", "why", "block")):
        hi = [c for c in conflicts if c.get("severity") in ("high_concern", "blocked_for_draft", "high", "blocked")]
        if hi:
            parts.append("Flagged conflicts: " + "; ".join(
                f"{c.get('headline') or c.get('conflict_type')} ({c.get('severity')})" for c in hi[:4]))
    if any(w in q for w in ("alternative", "instead", "option", "candidate")):
        alts = ms.get("alternative_candidates") or []
        cands = [a for a in alts if a.get("display_status") == "candidate_for_clinician_review"]
        excl = [a for a in alts if a.get("display_status") == "excluded_due_to_conflict"]
        if cands:
            parts.append("Lower-conflict candidates: " + ", ".join(a["medication_identity"]["original_text"] for a in cands))
        if excl:
            parts.append("Excluded (documented conflict): " + ", ".join(a["medication_identity"]["original_text"] for a in excl))
    if any(w in q for w in ("missing", "lab", "potassium", "evidence")):
        miss = (art.get("patient_context") or {}).get("missing_critical_evidence") or []
        if miss:
            parts.append("Missing evidence: " + "; ".join(miss))
    if any(w in q for w in ("guideline", "evidence", "source", "cite")):
        cites = art.get("citations") or []
        if cites:
            parts.append("Evidence: " + "; ".join(f"{c.get('organization')} {c.get('version')} ({c.get('section')})" for c in cites[:3]))
    if any(w in q for w in ("critic", "safe", "display", "block")):
        crit = art.get("critic") or {}
        parts.append(f"Critic: {'cleared for review' if crit.get('safe_to_display') else 'blocked'} "
                     f"(overall {round((crit.get('scorecard', {}).get('overall_safety', 0))*100)}%).")

    if not parts:
        parts.append("This case's analysis covers: " + ", ".join(grounded) +
                     ". Ask about conflicts, alternatives, missing evidence, guideline evidence, or the critic.")
    return CopilotAnswer(answer=" ".join(parts) + f"\n\n{DISCLAIMER}", grounded_on=grounded, used_anthropic=False)
