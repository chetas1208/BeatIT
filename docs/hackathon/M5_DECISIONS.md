# M5 Decisions

- Preserve the M4 deterministic engine and sample only uncertain inputs.
- Use explicit distributions with provenance instead of a generic “AI
  confidence” value.
- Reject invalid samples and retain their reasons.
- Record seed, origin snapshot, engine version, distribution version, and prior
  version for reproducibility.
- State independence assumptions explicitly until validated correlations exist.
- Use “5th–95th percentile of accepted deterministic simulations” rather than
  unsupported credible-interval language.
- Representative controls select the lowest accepted, highest accepted, and
  sample closest to the reported median; they are not themselves percentile
  bounds.
- Keep synthetic replay visibly synthetic and never treat it as patient evidence.
