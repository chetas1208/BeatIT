"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { useTemporalTwin } from "@/lib/twin/integration/context";
import {
  baselineScenarioParameters,
  propagateScenario,
  type ScenarioParameterKey,
  type ScenarioInput,
} from "@/lib/twin/scenario/propagation";
import {
  SCENARIO_PARAMETER_DEFINITIONS,
  validateScenarioParameter,
  type ScenarioParameterValues,
} from "@/lib/twin/scenario/parameters";
import {
  createScenarioHistory,
  pushScenario,
  redoScenario,
  resetScenario,
  undoScenario,
  type ScenarioHistory,
} from "@/lib/twin/scenario/history";
import type { ScenarioResult } from "@/lib/twin/scenario/types";
import { generateBackendEnsemble } from "@/lib/twin/ensemble/backend";
import type { EnsembleConfig, TwinEnsemble, TwinSample } from "@/lib/twin/ensemble/contracts";

function inputsFrom(values: ScenarioParameterValues): ScenarioInput[] {
  return Object.entries(values).map(([parameter, value]) => ({
    parameter: parameter as ScenarioParameterKey,
    value,
  }));
}

function valuesFromResult(result: ScenarioResult | null, fallback: ScenarioParameterValues | null): ScenarioParameterValues | null {
  if (!result) return fallback;
  const next = { ...(fallback ?? {}) } as Partial<ScenarioParameterValues>;
  for (const parameter of result.definition.parameters) {
    if (parameter.parameter in next) next[parameter.parameter as ScenarioParameterKey] = parameter.value;
  }
  return Object.keys(next).length === 5 ? next as ScenarioParameterValues : fallback;
}

function useScenarioController() {
  const { selectedSnapshot } = useTemporalTwin();
  const baseline = useMemo(
    () => selectedSnapshot ? baselineScenarioParameters(selectedSnapshot) : null,
    [selectedSnapshot],
  );
  const snapshotId = selectedSnapshot?.id ?? null;
  const [session, setSession] = useState<{
    snapshotId: string | null;
    parameters: ScenarioParameterValues | null;
    history: ScenarioHistory;
  }>(() => ({ snapshotId: null, parameters: null, history: createScenarioHistory() }));
  const [ensembleSession, setEnsembleSession] = useState<{
    snapshotId: string | null;
    ensemble: TwinEnsemble | null;
    selectedSampleId: string | null;
  }>(() => ({ snapshotId: null, ensemble: null, selectedSampleId: null }));
  const ensembleRevision = useRef(0);
  const current = session.snapshotId === snapshotId
    ? session
    : { snapshotId, parameters: baseline, history: createScenarioHistory() };
  const parameters = current.parameters;
  const history = current.history;

  const compute = useCallback((nextValues: ScenarioParameterValues): ScenarioResult | null => {
    if (!selectedSnapshot) return null;
    return propagateScenario(selectedSnapshot, inputsFrom(nextValues), `scenario-${selectedSnapshot.id}`).result;
  }, [selectedSnapshot]);

  const experiment = useCallback(() => {
    if (!parameters) return null;
    const result = compute(parameters);
    if (result) {
      ensembleRevision.current += 1;
      setSession((previous) => ({ snapshotId, parameters, history: pushScenario(previous.snapshotId === snapshotId ? previous.history : createScenarioHistory(), result) }));
      setEnsembleSession({ snapshotId, ensemble: null, selectedSampleId: null });
    }
    return result;
  }, [compute, parameters, snapshotId]);

  const changeParameter = useCallback((key: ScenarioParameterKey, value: number) => {
    const error = validateScenarioParameter(key, value);
    if (error) return error;
    const currentHistory = session.snapshotId === snapshotId ? session.history : createScenarioHistory();
    const currentParameters = session.snapshotId === snapshotId ? session.parameters : baseline;
    if (!currentParameters) return null;
    const next = { ...currentParameters, [key]: value };
    const result = currentHistory.present ? compute(next) : null;
    if (result) {
      ensembleRevision.current += 1;
      setEnsembleSession({ snapshotId, ensemble: null, selectedSampleId: null });
      setSession({ snapshotId, parameters: next, history: pushScenario(currentHistory, result) });
    } else {
      setSession({ snapshotId, parameters: next, history: currentHistory });
    }
    return null;
  }, [baseline, compute, session, snapshotId]);

  const reset = useCallback(() => {
    ensembleRevision.current += 1;
    setSession({ snapshotId, parameters: baseline, history: resetScenario() });
    setEnsembleSession({ snapshotId, ensemble: null, selectedSampleId: null });
  }, [baseline, snapshotId]);

  const ensemble = ensembleSession.snapshotId === snapshotId ? ensembleSession.ensemble : null;
  const selectedEnsembleSample = ensemble?.samples.find((sample) => sample.id === ensembleSession.selectedSampleId && sample.valid)
    ?? null;
  const generateEnsemble = useCallback(async (overrides: Partial<EnsembleConfig> = {}) => {
    if (!selectedSnapshot) return null;
    const revision = ++ensembleRevision.current;
    const requestedSnapshotId = snapshotId;
    let next: TwinEnsemble;
    try {
      next = await generateBackendEnsemble(
        selectedSnapshot,
        overrides.requestedSampleCount ?? 100,
        overrides.seed ?? 1208,
      );
    } catch (error) {
      if (revision === ensembleRevision.current) setEnsembleSession({ snapshotId, ensemble: null, selectedSampleId: null });
      throw error;
    }
    if (revision !== ensembleRevision.current || requestedSnapshotId !== snapshotId) return null;
    setEnsembleSession({ snapshotId, ensemble: next, selectedSampleId: null });
    return next;
  }, [selectedSnapshot, snapshotId]);
  const selectEnsembleSample = useCallback((sample: TwinSample | null) => {
    setEnsembleSession((previous) => ({
      ...previous,
      snapshotId,
      selectedSampleId: sample?.valid ? sample.id : null,
    }));
  }, [snapshotId]);

  return {
    selectedSnapshot,
    baseline,
    parameters,
    result: history.present,
    history,
    parameterDefinitions: SCENARIO_PARAMETER_DEFINITIONS,
    experiment,
    setParameter: changeParameter,
    undo: () => {
      ensembleRevision.current += 1;
      setEnsembleSession({ snapshotId, ensemble: null, selectedSampleId: null });
      const nextHistory = undoScenario(history);
      setSession({ snapshotId, parameters: valuesFromResult(nextHistory.present, baseline), history: nextHistory });
    },
    redo: () => {
      ensembleRevision.current += 1;
      setEnsembleSession({ snapshotId, ensemble: null, selectedSampleId: null });
      const nextHistory = redoScenario(history);
      setSession({ snapshotId, parameters: valuesFromResult(nextHistory.present, baseline), history: nextHistory });
    },
    reset,
    ensemble,
    selectedEnsembleSample,
    generateEnsemble,
    selectEnsembleSample,
    isAvailable: Boolean(selectedSnapshot && parameters),
  };
}

type ScenarioController = ReturnType<typeof useScenarioController>;
const ScenarioContext = createContext<ScenarioController | null>(null);

export function ScenarioProvider({ children }: { children: ReactNode }) {
  const controller = useScenarioController();
  return <ScenarioContext.Provider value={controller}>{children}</ScenarioContext.Provider>;
}

export function useScenario(): ScenarioController {
  const context = useContext(ScenarioContext);
  if (!context) throw new Error("useScenario must be used inside ScenarioProvider");
  return context;
}
