# CareGuard — VISTA Integration

CareGuard reuses DualBeat's existing `vista3d_client` (env-gated:
`VISTA3D_ENABLED` + `VISTA3D_API_BASE`, path scheme `{origin}/x/{ENDPOINT_SECRET}/...`).
CareGuard adds only optional configuration (`CAREGUARD_VISTA_*`), never a replacement.

VISTA runs only when: the feature is enabled, a compatible CT/MRI reference exists, the
external endpoint is configured, the case is deidentified, and the user initiated image
processing. Output is marked *"Model-derived research segmentation requiring clinician
review."* VISTA failure never blocks non-imaging CareGuard functions. The model is never
deployed into the Vercel Python function — it stays an external tunneled service.
