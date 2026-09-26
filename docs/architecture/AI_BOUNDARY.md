# Deterministic and AI authority boundary

## Governing rule

The deterministic BeatIT engine establishes cardiac numbers. External models
may extract, route, segment, critique, or explain within their bounded
contracts; they are not the numerical authority for physiology.

| Function | Authority | Failure behavior |
| --- | --- | --- |
| Cardiac state and source status | BeatIT schemas/state builder | Missing information remains explicit |
| ECG features and QTc derivation | Deterministic Python tools | Returns bounded errors or unavailable fields |
| EF, SV, CO, MAP and hemodynamics | Deterministic Python tools | No LLM substitution |
| Recovery scenarios | Deterministic bounded simulator | Invalid/boundary inputs are rejected |
| Plausible-twin sampling | Seeded BeatIT ensemble engine | Reproducible for identical request/seed |
| Shadow Trial pairing and effects | BeatIT Shadow Trial engine | Same-sample pairing is preserved |
| Missing Piece sensitivity/evidence value | BeatIT analysis modules | Describes uncertainty; does not prescribe |
| Medical-image segmentation | Optional VISTA-3D service | Explicit disabled/unavailable result; procedural visualization remains |
| Assistant routing | Optional Laya, otherwise deterministic fallback | Laya cannot decide diagnosis, treatment, emergency handling, or canonical values |
| Explanation/report prose | Optional Bedrock/OpenAI-compatible provider | Deterministic fallback; computed facts remain unchanged |
| Safety boundaries | Deterministic request/output validators | Unsafe requests are blocked, not delegated to a model |

## Bedrock truth

The repository implements Bedrock-backed OpenAI-compatible provider paths.
During the AWS campaign, model/profile discovery and one minimal
`nvidia.nemotron-nano-12b-v2` inference succeeded in `us-east-1`.

That test proves credentials and model runtime access at that time. It does not
prove:

- AWS hosting;
- a persistent Bedrock configuration;
- public Copilot availability;
- full assistant E2E behavior from a deployed frontend;
- clinical validity.

AWS hosting failed and no hosted backend exists.

## Laya truth

`python/hearttwin/assistant/laya_adapter.py` exposes named, bounded software
routing decisions. It explicitly excludes diagnosis, treatment, medication,
emergency triage, and medical safety decisions. The audited source states that
Laya is not reachable in this environment; failures use labeled deterministic
heuristics.

## VISTA truth

VISTA-3D is an optional segmentation authority for supported CT masks, not a
physiology calculator. BeatIT deterministically analyzes returned masks. The
adapter records known label limitations, including the single heart label used
for chamber proxies.

The local VISTA runtime is not bridged publicly. The active temporary
Cloudflare Quick Tunnel terminates at the BeatIT backend only; it does not
expose the unauthenticated VISTA API.

## Information allowed into model prompts

The assistant should use only the minimum case context and already-computed
tool results needed to answer. It must preserve:

- source and provenance identifiers;
- observed/derived/inferred/prior/simulated distinctions;
- assumptions and uncertainty;
- the canonical safety disclaimer and use boundary.

Raw patient uploads, secrets, authentication headers, and local paths are not
model context.

## Non-claims

Neither deterministic simulation nor AI output is presented as diagnosis,
treatment selection, emergency guidance, a validated patient outcome forecast,
or a substitute for clinician judgment.
