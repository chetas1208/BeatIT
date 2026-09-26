# Artifact Results (Certification Wave C2)

## Schema

Single contract: `AssistantArtifact` in `assistant/schemas.py` (7 types).

## UI

- `ArtifactCard`, `PhysicianBriefView`, `ArtifactDetailPanel` — **PHYSICIAN_BRIEF** has detail view; other types use placeholder chips in chat (Wave 4 honest limitation).

## Integrity

- Artifacts produced by orchestrator carry `source_tool_ids` when wired.
- Chat must not embed unvalidated HTML; chips link to typed payloads only.

## Coverage

Provenance on artifacts: partial — mapping layer covers backend vocabularies; not all product surfaces emit artifacts yet.
