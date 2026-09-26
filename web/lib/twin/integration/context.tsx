"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useDualBeatStore } from "@/lib/store";
import { createReplayTimeline } from "@/lib/twin/replay";
import { useTwinPlayback } from "@/lib/twin/playback";
import type { TwinPlaybackController } from "@/lib/twin/playback";
import type {
  TwinSnapshot,
  TwinTimeline,
  TwinPlaybackState,
} from "@/lib/twin/time/contracts";
import type { CardiacTwinState, SimulationVisualization } from "@/types/heart";
import { pvContextForSnapshot, type TemporalPVContext } from "@/lib/twin/pv";
import type { ECGTimelinePoint } from "@/lib/twin/ecg";

export interface TemporalTwinContextValue {
  timeline: TwinTimeline | null;
  playback: TwinPlaybackState | null;
  selectedSnapshot: TwinSnapshot | null;
  selectedVisualization: SimulationVisualization | null;
  isLive: boolean;
  sourceLabel: "LIVE" | "REPLAY";
  controller: TwinPlaybackController | null;
  pv: TemporalPVContext;
  ecg: ECGTimelinePoint | null;
}

const TemporalTwinContext = createContext<TemporalTwinContextValue>({
  timeline: null,
  playback: null,
  selectedSnapshot: null,
  selectedVisualization: null,
  isLive: false,
  sourceLabel: "REPLAY",
  controller: null,
  pv: pvContextForSnapshot(null),
  ecg: null,
});

function snapshotAtCursor(timeline: TwinTimeline | null, cursorTime: string | undefined): TwinSnapshot | null {
  if (!timeline || !cursorTime) return null;
  const cursor = Date.parse(cursorTime);
  let selected: TwinSnapshot | null = null;
  for (const snapshot of timeline.snapshots) {
    if (Date.parse(snapshot.timestamp) <= cursor) selected = snapshot;
    else break;
  }
  return selected ?? timeline.snapshots[0] ?? null;
}

function numericValue(value: { value: number } | null | undefined): number | null {
  return typeof value?.value === "number" && Number.isFinite(value.value) ? value.value : null;
}

/**
 * Projects explicit historical measurements into the existing visualization
 * shell. Curves are held from the selected stored visualization; only scalar
 * readouts and labels change, so the client never invents a new PV waveform.
 */
function projectVisualizationForState(
  state: CardiacTwinState | null,
  visualization: SimulationVisualization | null | undefined,
): SimulationVisualization | null {
  if (!state || !visualization) return visualization ?? null;
  const ef = numericValue(state.measurements.ejection_fraction_pct);
  const heartRate = numericValue(state.measurements.heart_rate_bpm)
    ?? (numericValue(state.electrophysiology.rr_interval_ms)
      ? 60000 / numericValue(state.electrophysiology.rr_interval_ms)!
      : null);
  const rr = numericValue(state.electrophysiology.rr_interval_ms);
  return {
    ...visualization,
    summary: {
      ...visualization.summary,
      ...(ef == null ? {} : { ef_pct: ef, ejection_fraction_pct: ef }),
      ...(heartRate == null ? {} : { heart_rate_bpm: heartRate }),
      ...(rr == null ? {} : { rr_interval_ms: rr }),
    },
    cardiac_cycle: {
      ...visualization.cardiac_cycle,
      ...(heartRate == null ? {} : { heart_rate_bpm: heartRate }),
      ...(rr == null ? {} : { cycle_duration_ms: rr }),
    },
    pv_loop: {
      ...visualization.pv_loop,
      ...(ef == null ? {} : { ef_pct: ef }),
    },
    electrophysiology: {
      ...visualization.electrophysiology,
      ...(rr == null ? {} : { rr_interval_ms: rr }),
      rhythm_label: state.electrophysiology.rhythm_label ?? visualization.electrophysiology.rhythm_label,
    },
    simulation_note: `${visualization.simulation_note} · temporal projection; PV shape held from selected snapshot`,
  };
}

export function TemporalTwinProvider({ children }: { children: ReactNode }) {
  const state = useDualBeatStore((s) => s.state);
  const visualization = useDualBeatStore((s) => s.visualization);
  const timeline = useMemo(
    () => (state ? createReplayTimeline(state, visualization ?? undefined) : null),
    [state, visualization],
  );
  const { playback, controller } = useTwinPlayback(timeline);
  const selectedSnapshot = snapshotAtCursor(timeline, playback?.cursorTime);
  const selectedVisualization = projectVisualizationForState(
    selectedSnapshot?.state ?? state,
    selectedSnapshot?.visualization ?? visualization,
  );
  const isReplay = Boolean(timeline?.snapshots.some((snapshot) => snapshot.quality === "synthetic" || snapshot.provenance.some((item) => item.source === "synthetic_replay")));
  const isLive = !isReplay && (playback?.mode === "live" || (timeline != null && playback?.cursorTime === timeline.endTime));
  const selectedECG = useMemo(() => selectedSnapshot
    ? selectedSnapshot.state.electrophysiology.rr_interval_ms
      ? {
        timestamp: selectedSnapshot.timestamp,
        kind: selectedSnapshot.quality === "synthetic" ? "simulated" as const : "measured" as const,
        rhythmLabel: selectedSnapshot.state.electrophysiology.rhythm_label ?? null,
        rrIntervalMs: selectedSnapshot.state.electrophysiology.rr_interval_ms.value,
        qrsDurationMs: selectedSnapshot.state.electrophysiology.qrs_duration_ms?.value ?? null,
        qtcMs: selectedSnapshot.state.electrophysiology.qtc_ms?.value ?? null,
          provenance: selectedSnapshot.provenance,
        }
      : {
          timestamp: selectedSnapshot.timestamp,
          kind: "missing" as const,
          provenance: selectedSnapshot.provenance,
        }
    : null, [selectedSnapshot]);
  const value = useMemo<TemporalTwinContextValue>(() => ({
    timeline,
    playback,
    selectedSnapshot,
    selectedVisualization,
    isLive: Boolean(isLive),
    sourceLabel: isReplay ? "REPLAY" : isLive ? "LIVE" : "REPLAY",
    controller,
    pv: pvContextForSnapshot(selectedSnapshot),
    ecg: selectedECG,
  }), [timeline, playback, selectedSnapshot, selectedVisualization, isLive, isReplay, controller, selectedECG]);

  // Keep the controller available to the timeline UI without placing mutable
  // transport objects in React state. The provider surface is intentionally
  // small; consumers can use the hook below for controls.
  return <TemporalTwinContext.Provider value={value}>{children}</TemporalTwinContext.Provider>;
}

export function useTemporalTwin(): TemporalTwinContextValue {
  return useContext(TemporalTwinContext);
}

export function useTemporalTwinController() {
  return useTemporalTwin().controller;
}
