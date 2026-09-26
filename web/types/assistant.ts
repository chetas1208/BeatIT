/*
 * Types mirroring python/hearttwin/assistant/schemas.py (Wave 2/3 of the
 * BeatIT unified-assistant campaign). Keep field names and literal values
 * exact matches of the Python source — this is the one contract the new
 * chat UI is built against, not a guess.
 *
 * Python's `datetime` fields serialize to ISO 8601 strings over JSON, so
 * they are typed `string` here, matching the convention already used for
 * timestamps elsewhere in web/types (see CaseRecord.created_at in api.ts).
 */

export type ExecutionClass =
  | "direct_state_read"
  | "evidence_retrieval"
  | "deterministic_computation"
  | "simulation"
  | "artifact_generation"
  | "generative_explanation"
  | "complex_synthesis"
  | "clarification_required"
  | "insufficient_evidence"
  | "human_decision_required"
  | "unsupported"

export type CanonicalProvenanceKind =
  | "observed"
  | "derived"
  | "simulated"
  | "model_prior"
  | "external_reference"
  | "user_asserted"

export interface ProvenanceRef {
  kind: CanonicalProvenanceKind
  source_id?: string | null
  description?: string | null
  confidence?: number | null
}

export interface ConversationContext {
  conversation_id: string
  audience: "general" | "physician"
  patient_id?: string | null
  snapshot_id?: string | null
  component_id?: string | null
  product_space?: string | null
  scenario_id?: string | null
  ensemble_id?: string | null
  shadow_trial_id?: string | null
  pair_id?: string | null
  target_metric?: string | null
  synthetic_status?: string | null
}

export interface AssistantMessage {
  role: "user" | "assistant" | "system"
  content: string
  created_at: string
  tool_result_refs: string[]
}

export type ToolSafetyLevel = "T0" | "T1" | "T2" | "T3"

export interface ToolResult {
  tool_name: string
  execution_class: ExecutionClass
  canonical_payload: Record<string, unknown>
  provenance: ProvenanceRef[]
  safety_level: ToolSafetyLevel
}

export type AssistantArtifactType =
  | "cardiac_component_report"
  | "timeline_summary"
  | "evidence_table"
  | "pv_comparison"
  | "shadow_trial_summary"
  | "uncertainty_analysis"
  | "physician_brief"

export interface AssistantArtifact {
  id: string
  type: AssistantArtifactType
  title: string
  conversation_id: string
  patient_id?: string | null
  snapshot_id?: string | null
  source_tool_ids: string[]
  provenance: ProvenanceRef[]
  payload: Record<string, unknown>
  created_at: string
  version: number
}

export interface AssistantTraceMeta {
  request_id: string
  tools_invoked: string[]
  model_used?: string | null
  latency_ms?: number | null
}

export interface AssistantRequest {
  conversation_id: string
  message: string
  context: ConversationContext
}

export interface AssistantResponse {
  message: string
  artifacts: AssistantArtifact[]
  safety_disclaimer: string
  execution_class: ExecutionClass
  trace: AssistantTraceMeta
}
