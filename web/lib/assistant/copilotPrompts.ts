/** Starter prompts for the native BeatIT Copilot panel (no third-party runtime). */

export const BEATIT_COPILOT_STARTER_PROMPTS = [
  {
    title: "Explain ejection fraction",
    message: "What is the ejection fraction for the current case, and how is it derived?",
  },
  {
    title: "Ensemble uncertainty",
    message: "What are the modeling assumptions for this ensemble?",
  },
  {
    title: "Shadow trial",
    message: "Run a shadow trial on this ensemble and summarize the counterfactual.",
  },
  {
    title: "Recovery simulation",
    message: "Run recovery simulation for this case and describe the bounded scenarios.",
  },
] as const;
