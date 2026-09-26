# Known Limitations

- Educational simulation only; no diagnosis, treatment, emergency guidance,
  FDA validation, clinical validation, or regulatory claim.
- M5.5, M6, M7, and M9 retain explicitly documented browser, persistence,
  security, and contribution/validation limitations.
- The local language model is optional. If unavailable, deterministic tools and
  safe clarification/fallback paths remain authoritative.
- VISTA-3D is optional and lazy; the procedural semantic heart does not depend
  on an imaging checkpoint.
- Local file/SQLite stores are not a multi-user authenticated production data
  service. Do not load identifiable patient data without adding access control,
  restricted CORS, retention, and an approved deployment design.
- Browser sign-off is unavailable in the current environment because Chromium
  lacks `libasound.so.2` and Firefox is not installed for Playwright.
