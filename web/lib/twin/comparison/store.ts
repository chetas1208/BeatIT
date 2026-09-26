"use client";

import { create } from "zustand";
import type { SimulationVisualization } from "@/types/heart";
import type { ShadowTrialResponse } from "@/types/shadow-trial";
import { pairedHeartStateFromM6 } from "@/lib/twin/comparison/projection";
import type { ComparisonViewState, PairedHeartState } from "@/lib/twin/comparison/contracts";

interface ComparisonStore {
  trial: ShadowTrialResponse | null;
  paired: PairedHeartState | null;
  view: ComparisonViewState | null;
  open: (trial: ShadowTrialResponse, pairId: string, reference: SimulationVisualization) => void;
  selectPair: (pairId: string, reference: SimulationVisualization) => void;
  setClockMode: (mode: ComparisonViewState["clockMode"]) => void;
  setPlaying: (playing: boolean) => void;
  setPhase: (phase: number) => void;
  setSelectedComponent: (componentId: string | null) => void;
  setLinkedSelection: (linked: boolean) => void;
  setLinkedCamera: (linked: boolean) => void;
  setDifferenceOnly: (enabled: boolean) => void;
  close: () => void;
}

function initialView(pairId: string): ComparisonViewState {
  return { selectedPairId: pairId, selectedComponentId: null, linkedSelection: true, linkedCamera: true, differenceOnly: false, clockMode: "phase_locked", playing: true, normalizedPhase: 0 };
}

function buildPair(trial: ShadowTrialResponse, pairId: string, reference: SimulationVisualization): PairedHeartState | null {
  const pair = trial.paired_results.find((candidate) => candidate.sample_id === pairId);
  return pair ? pairedHeartStateFromM6(trial.id, pair, reference, trial.definition?.scenario ?? null) : null;
}

export const useComparisonStore = create<ComparisonStore>((set, get) => ({
  trial: null,
  paired: null,
  view: null,
  open: (trial, pairId, reference) => { const paired = buildPair(trial, pairId, reference); if (paired) set({ trial, paired, view: initialView(paired.pairId) }); },
  selectPair: (pairId, reference) => { const trial = get().trial; if (!trial) return; const paired = buildPair(trial, pairId, reference); if (paired) set((current) => ({ paired, view: { ...(current.view ?? initialView(pairId)), selectedPairId: pairId, selectedComponentId: null, normalizedPhase: 0 } })); },
  setClockMode: (clockMode) => set((current) => ({ view: current.view ? { ...current.view, clockMode, normalizedPhase: 0 } : null })),
  setPlaying: (playing) => set((current) => ({ view: current.view ? { ...current.view, playing } : null })),
  setPhase: (normalizedPhase) => set((current) => ({ view: current.view ? { ...current.view, normalizedPhase: ((normalizedPhase % 1) + 1) % 1 } : null })),
  setSelectedComponent: (selectedComponentId) => set((current) => ({ view: current.view ? { ...current.view, selectedComponentId } : null })),
  setLinkedSelection: (linkedSelection) => set((current) => ({ view: current.view ? { ...current.view, linkedSelection } : null })),
  setLinkedCamera: (linkedCamera) => set((current) => ({ view: current.view ? { ...current.view, linkedCamera } : null })),
  setDifferenceOnly: (differenceOnly) => set((current) => ({ view: current.view ? { ...current.view, differenceOnly } : null })),
  close: () => set({ trial: null, paired: null, view: null }),
}));
