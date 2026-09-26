import type { ConversationContext } from "@/types/assistant";
import type { AssistantContext } from "@/lib/assistant/contextEvents";
import type { BeatITMode } from "@/lib/product/contracts";

export function buildAssistantRequestContext(args: {
  conversationId: string;
  audience: ConversationContext["audience"];
  caseId: string | null;
  uiContext: AssistantContext;
  productSpace: BeatITMode;
  ensembleId?: string | null;
  scenarioId?: string | null;
  shadowTrialId?: string | null;
  missingPieceId?: string | null;
  pairId?: string | null;
  snapshotId?: string | null;
}): ConversationContext {
  return {
    conversation_id: args.conversationId,
    audience: args.audience,
    patient_id: args.caseId,
    component_id: args.uiContext.component_id ?? null,
    snapshot_id: args.snapshotId ?? args.uiContext.snapshot_id ?? null,
    product_space: args.productSpace,
    scenario_id: args.scenarioId ?? args.uiContext.scenario_id ?? null,
    ensemble_id: args.ensembleId ?? null,
    shadow_trial_id: args.shadowTrialId ?? null,
    missing_piece_id: args.missingPieceId ?? null,
    pair_id: args.pairId ?? args.uiContext.pair_id ?? null,
    target_metric: args.uiContext.target_metric ?? null,
  };
}
