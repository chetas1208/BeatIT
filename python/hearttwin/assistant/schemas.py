"""Schemas for the unified BeatIT conversation assistant (Wave 2).

These types implement the ConversationContext / artifact / execution-class
contracts from docs/assistant/GLOBAL_ARCHITECTURE.md. They are additive: no
existing schema in python/hearttwin/schemas.py is modified or replaced.

Provenance: the 4 existing vocabularies (backend ValueSource, frontend
EvidenceKind, timeline TwinEventSource, causal CausalSourceKind) are NOT
unified here — see CanonicalProvenanceKind below and
docs/assistant/wave2/conversation-api.md for the mapping-layer plan.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from python.hearttwin.safety import DISCLAIMER


# ---------------------------------------------------------------------------
# Execution classes (GLOBAL_ARCHITECTURE.md "EXECUTION CLASSES", verbatim list)
# ---------------------------------------------------------------------------


class ExecutionClass(str, Enum):
    DIRECT_STATE_READ = "direct_state_read"
    EVIDENCE_RETRIEVAL = "evidence_retrieval"
    DETERMINISTIC_COMPUTATION = "deterministic_computation"
    SIMULATION = "simulation"
    ARTIFACT_GENERATION = "artifact_generation"
    GENERATIVE_EXPLANATION = "generative_explanation"
    COMPLEX_SYNTHESIS = "complex_synthesis"
    CLARIFICATION_REQUIRED = "clarification_required"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    HUMAN_DECISION_REQUIRED = "human_decision_required"
    UNSUPPORTED = "unsupported"


# ---------------------------------------------------------------------------
# Canonical provenance vocabulary
#
# Wave 1 found 4 incompatible provenance vocabularies already in the
# codebase. Per WAVE_1_HANDOFF.md this schema defines ONE new minimal
# canonical enum rather than attempting to unify the existing 4 — that
# unification (a mapping layer translating ValueSource/EvidenceKind/
# TwinEventSource/CausalSourceKind into this enum) is explicitly deferred to
# a future wave. This enum is intentionally small: it only needs to answer
# the guardrail-layer question that matters for a chat response — was this
# number observed, computed, simulated, assumed, referenced, or merely
# stated in conversation.
# ---------------------------------------------------------------------------


class CanonicalProvenanceKind(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    SIMULATED = "simulated"
    MODEL_PRIOR = "model_prior"
    EXTERNAL_REFERENCE = "external_reference"
    USER_ASSERTED = "user_asserted"


class ProvenanceRef(BaseModel):
    """One provenance pointer attached to a tool result or artifact.

    Deliberately thin — it points at canonical data, it never carries a
    second copy of the value itself (values live in canonical_payload /
    payload).
    """

    kind: CanonicalProvenanceKind
    source_id: Optional[str] = None
    description: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Conversation context (GLOBAL_ARCHITECTURE.md "CONTEXT ARCHITECTURE")
# ---------------------------------------------------------------------------


class ConversationContext(BaseModel):
    conversation_id: str
    audience: Literal["general", "physician"]
    patient_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    component_id: Optional[str] = None
    product_space: Optional[str] = None
    scenario_id: Optional[str] = None
    ensemble_id: Optional[str] = None
    shadow_trial_id: Optional[str] = None
    pair_id: Optional[str] = None
    target_metric: Optional[str] = None
    synthetic_status: Optional[str] = None


# ---------------------------------------------------------------------------
# Conversation turn
# ---------------------------------------------------------------------------


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # References only (tool_result ids / tool names), not embedded ToolResult
    # objects — keeps chat turns light per the "chat text vs artifacts are
    # separate" rule; full payloads live in ToolResult/AssistantArtifact.
    tool_result_refs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool call result (control plane <-> data/computation plane boundary)
# ---------------------------------------------------------------------------


class ToolResult(BaseModel):
    tool_name: str
    execution_class: ExecutionClass
    canonical_payload: dict[str, Any] = Field(default_factory=dict)
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    # Mirrors GLOBAL_ARCHITECTURE.md "Tool safety levels" (T0-T3).
    safety_level: Literal["T0", "T1", "T2", "T3"]


# ---------------------------------------------------------------------------
# Artifacts (GLOBAL_ARCHITECTURE.md "ARTIFACT ARCHITECTURE")
# ---------------------------------------------------------------------------


class AssistantArtifactType(str, Enum):
    CARDIAC_COMPONENT_REPORT = "cardiac_component_report"
    TIMELINE_SUMMARY = "timeline_summary"
    EVIDENCE_TABLE = "evidence_table"
    PV_COMPARISON = "pv_comparison"
    SHADOW_TRIAL_SUMMARY = "shadow_trial_summary"
    UNCERTAINTY_ANALYSIS = "uncertainty_analysis"
    PHYSICIAN_BRIEF = "physician_brief"


class AssistantArtifact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: AssistantArtifactType
    title: str
    conversation_id: str
    patient_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    source_tool_ids: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


# ---------------------------------------------------------------------------
# Trace metadata stub (GLOBAL_ARCHITECTURE.md "OBSERVABILITY")
#
# Minimal now; the real pipeline (Laya decision, model selection, per-tool
# latencies) fills this in once it exists. Kept as its own model so
# AssistantResponse doesn't need to change shape when that lands.
# ---------------------------------------------------------------------------


class AssistantTraceMeta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    tools_invoked: list[str] = Field(default_factory=list)
    model_used: Optional[str] = None
    latency_ms: Optional[float] = None


# ---------------------------------------------------------------------------
# Request / response envelope
# ---------------------------------------------------------------------------


class AssistantRequest(BaseModel):
    conversation_id: str
    message: str
    context: ConversationContext

    @model_validator(mode="after")
    def _context_conversation_id_matches(self) -> "AssistantRequest":
        # conversation_id is duplicated on the envelope (transport identity)
        # and inside context (canonical context identity) — GLOBAL_ARCHITECTURE
        # forbids a second source of truth, so reject divergence rather than
        # silently preferring one.
        if self.context.conversation_id != self.conversation_id:
            raise ValueError("context.conversation_id must match conversation_id")
        return self


class AssistantResponse(BaseModel):
    message: str
    artifacts: list[AssistantArtifact] = Field(default_factory=list)
    safety_disclaimer: str = DISCLAIMER
    execution_class: ExecutionClass
    trace: AssistantTraceMeta = Field(default_factory=AssistantTraceMeta)
