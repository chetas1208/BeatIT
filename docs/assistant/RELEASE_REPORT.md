# BEATIT UNIFIED ASSISTANT — RELEASE REPORT

**STATUS:** CONDITIONAL PASS (see certification)

**CHAT SURFACES BEFORE:** CopilotDock + CareGuardCopilot + flag-gated BeatIT Copilot  

**CHAT SURFACES AFTER (main console):** **1** (BeatIT Copilot, default ON)

**TESTS:** 1314 passed, 5 skipped, 6 xfailed (`pnpm test:py`)

**LAYA:** fallback-first; real server 65% vs fallback 81% on 160 fixtures  

**NVIDIA:** deep model viable with gates; fast Lightning not suitable as configured  

**KEY POOL:** 3 configured / healthy (values not printed)  

**FINAL:** SHIP for demo spine; DO NOT SHIP as full clinical copilot replacement without browser E2E + legacy retirement  

Detail: `docs/assistant/certification/FINAL_RELEASE_DECISION.md`
