import type { CardiacFinding, CardiacFindings, CardiacTwinState } from "@/types/heart";
import type { HeartComponentCategory, HeartComponentDefinition } from "@/lib/heart/registry";

export type HeartInteractionMode = "none" | "hover" | "selected" | "focused";

export interface HeartSelectionState {
  selectedId: string | null;
  hoveredId: string | null;
  focusedId: string | null;
  mode: HeartInteractionMode;
}

export interface AnatomyKnowledge {
  componentId: string;
  name: string;
  shortDescription: string;
  primaryFunction: string;
  relatedStructures: readonly string[];
  physiologyConcepts: readonly string[];
}

export type EvidenceKind = "directly_observed" | "extracted" | "derived" | "default_model_prior" | "simulated" | "unavailable";

export interface ComponentEvidence {
  id: string;
  label: string;
  kind: EvidenceKind;
  source?: string;
  method?: string;
  timestamp?: string;
  confidence?: number;
  derivation?: string;
}

export interface PatientComponentState {
  componentId: string;
  available: boolean;
  statusLabel: "observed" | "derived" | "prior" | "simulated" | "insufficient_evidence";
  metrics: readonly { label: string; value: string; sourceKind: EvidenceKind }[];
  findings: readonly CardiacFinding[];
  evidence: readonly ComponentEvidence[];
  limitations: readonly string[];
  relatedComponentIds: readonly string[];
}

export interface ComponentReport {
  component: HeartComponentDefinition;
  knowledge: AnatomyKnowledge;
  patientState: PatientComponentState;
  sections: readonly {
    id: "structure" | "function" | "electrical" | "hemodynamics" | "regional_findings" | "evidence" | "limitations";
    title: string;
    lines: readonly string[];
  }[];
  safetyNotice: string;
}

export interface CameraFocusTarget {
  componentId: string;
  position: readonly [number, number, number];
  lookAt: readonly [number, number, number];
  distance: number;
}

export interface PatientBindingInput {
  state: CardiacTwinState | null | undefined;
  findings: CardiacFindings | null | undefined;
}

export type ComponentCategoryFilter = HeartComponentCategory | "all";
