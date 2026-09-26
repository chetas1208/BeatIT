# CareGuard — Alternative Generation Policy

Alternatives are a constrained evidence process, never from model memory
(`medications/alternative_engine.py`):

1. **Generic-equivalent** (Orange Book) — excluded when the active ingredient is the
   conflict source.
2. **Same guideline-supported class** (RxClass siblings + guideline passage) — each
   re-run through the full conflict engine; equal/stronger conflict → excluded.
3. **Cross-class guideline candidate** — only when a guideline passage explicitly names
   the class; re-checked; missing criteria shown.
4. **DDInter leads** — normalize → guideline relevance → official label → full
   re-check before display (never displayed as a raw lead).

Ranked by evidence completeness, conflict burden, freshness, and missing-fact count.
Labels: *lower documented conflict burden* / *requires more information* / *excluded due
to documented conflict* / *insufficient evidence*. Never *safest / best / optimal*.
When nothing qualifies, the no-alternative message is returned; the UI is never padded.
No dose is ever generated.
