# CareGuard — Anthropic Integration

CareGuard uses the official Anthropic SDK **alongside** DualBeat's OpenAI/Weave (never
replacing them). Claude structures evidence and writes prose; it never computes a
number or a clinical fact.

## Model routing (`anthropic/model_router.py`, `config.py`)
| Role | Default |
|---|---|
| fast (intake, scenarios) | `claude-haiku-4-5-20251001` |
| extraction/FHIR/multimorbidity/guidelines | `claude-sonnet-5` |
| medication-safety / plan-composer / critic | `claude-fable-5` |
| fallback | `claude-sonnet-5` |

Per current-model guidance: **no** temperature/top_p/top_k for Sonnet/Fable; only final
structured output + tool-call metadata are stored (no raw chain-of-thought).

## Structured output (`anthropic/structured_output.py`)
Every model output entering state is produced via a forced `emit_structured_output`
tool whose `input_schema` **is** the JSON Schema, then validated against a Pydantic
model. Malformed output is rejected — prose is never parsed into clinical state.

## Fable refusal handling (`anthropic/refusal_handler.py`, `client.py`)
Fable may return `stop_reason="refusal"` on HTTP 200. CareGuard: detects it → records
redacted refusal metadata (never content) → retries on `CAREGUARD_MODEL_FALLBACK`
(Sonnet) → on double failure returns a safe abstention with the message *"The model
could not complete this review. No clinical candidate was generated."* An empty result
is never stored as success; a replacement is never fabricated; deterministic evidence
already collected is preserved.

## Deidentification boundary (`security.py`)
Before any deidentify-only model (Fable), `deidentify_for_model` strips identifiers and
`assert_no_identifiers` verifies none survive (raises `DeidentificationError` otherwise).
Fable receives only a deidentified structured clinical-evidence object — never the raw
FHIR bundle, raw notes, or images.

## Approved tools only (`anthropic/tool_runner.py`)
Claude may request only the CareGuard tool allow-list (get_fhir_resource,
search_local_guidelines, normalize_medication_rxnorm, retrieve_dailymed_label,
run_hearttwin_scenario, write_audit_event, …). It cannot browse the web, run shell,
query unapproved sources, write the DB, mutate DualBeat state, prescribe, or dose.

## Offline mode
With no `ANTHROPIC_API_KEY`, `client.is_available()` is False and every agent uses its
deterministic path — the whole pipeline runs and is fully tested without a key.
