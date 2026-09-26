# BeatIT Healthcare Demo

## Preflight

```bash
./scripts/demo-preflight.sh
./scripts/seed-demo.sh
```

Use the synthetic demo fixture. If an optional expensive path is unavailable,
say **PRECOMPUTED DEMO RESULT** before showing it.

## Demo premise

“A cardiologist opens BeatIT before a recovery conversation because the
patient's evidence, physiological assumptions, and possible recovery scenarios
are otherwise difficult to connect and explain.”

## Run of show

**CASE — establish the user and evidence.** Open the labeled synthetic or
de-identified case. Show the supplied measurements and their source/provenance.
Say: “This is where the cardiologist starts before a supervised recovery
conversation.”

**BASELINE — establish trust.** Generate the baseline and identify one measured
value, one derived value, and one prior-filled or unavailable value. State that
the same inputs produce the same baseline.

**QUESTION — establish relevance.** Ask one educational physiology question the
cardiologist could need to explain. Do not ask for diagnosis, treatment, or a
patient outcome prediction.

**SCENARIO — demonstrate the capability.** Change one bounded parameter. Show
its baseline value, scenario value, units, allowed range, and assumptions before
running the deterministic simulation.

**COMPARE — show the result.** Compare baseline and simulated trajectory
visually. Explain which deterministic relationship drove one visible difference.
Call it a hypothetical simulated change, not a predicted benefit or harm.

**LIMITS — show what cannot be concluded.** Ask “Why is this uncertain?” Show
missing evidence, accepted-input spread where available, and model limitations.
Do not describe simulation spread as patient probability or a confidence
interval.

**SUMMARY — complete the workflow.** Show or export the summary with provenance,
scenario assumptions, unavailable sections, limitations, and the persistent
safety boundary.

**CLOSE.** “BeatIT does not ask an LLM to predict what happens to a patient's
heart. It lets a cardiologist operate a deterministic cardiovascular model and
shows both what the bounded simulation says and what the evidence cannot
support.”

## Recovery line

If a model or internet provider fails: “The optional intelligence layer is
offline; the deterministic heart and its audited outputs continue to run.”
