# CareGuard CDS Hooks

Discovery at `GET /api/v1/careguard/cds-services`. Services: **patient-view**,
**order-select**, **order-sign**. CareGuard returns **cards only** — never an
automatically executable order, never a `create` systemAction.

- **patient-view** — medication reconciliation, multimorbidity review, missing-data
  cards (non-interruptive unless a confirmed high-severity issue exists).
- **order-select** — on selecting a proposed medication: conflicts + evidence-linked
  candidate alternatives; the order is never modified.
- **order-sign** — interruptive card only for a documented contraindication, documented
  serious allergy, duplicate ingredient, or configured high-severity label conflict;
  includes exact evidence, a review link, and an override-reason requirement.

Every card: `summary` (≤140 chars), `detail`, `indicator` (info/warning/critical),
`source.label`, evidence/review link, and `overrideReasons` where applicable. Cards are
validated against the CDS Hooks card shape (`cds_hooks/cards.py::validate_card`), which
also rejects any auto-executable order.
