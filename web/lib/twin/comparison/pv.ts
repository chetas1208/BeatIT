import type { ComparisonClockState } from "@/lib/twin/comparison/clock";
import { normalizeComparisonPhase } from "@/lib/twin/comparison/clock";
import type { PVLoopData } from "@/types/heart";

export const PV_UNCERTAINTY_LIMITATION =
  "M6 provides scalar PV-linked effects only; the source PV shape is held and pointwise PV uncertainty is unavailable.";

export interface PVCursorProjection {
  readonly phase: number;
  readonly available: boolean;
  readonly cursorIndex: number | null;
  readonly volumeMl: number | null;
  readonly pressureMmhg: number | null;
}

export interface PVComparisonUncertaintyBoundary {
  readonly mode: "scalar_pv_linked";
  readonly pointwiseLoopAvailable: false;
  readonly heldShape: true;
  readonly limitation: typeof PV_UNCERTAINTY_LIMITATION;
}

export interface ComparisonPVProjection {
  readonly baseline: PVCursorProjection;
  readonly scenario: PVCursorProjection;
  readonly uncertainty: PVComparisonUncertaintyBoundary;
}

function unavailableCursor(phase: number): PVCursorProjection {
  return {
    phase,
    available: false,
    cursorIndex: null,
    volumeMl: null,
    pressureMmhg: null,
  };
}

function validLoop(loop: PVLoopData | null | undefined): loop is PVLoopData {
  if (
    !loop ||
    !Array.isArray(loop.volume_ml) ||
    !Array.isArray(loop.pressure_mmhg) ||
    loop.volume_ml.length < 2 ||
    loop.volume_ml.length !== loop.pressure_mmhg.length
  ) {
    return false;
  }

  return loop.volume_ml.every(Number.isFinite) && loop.pressure_mmhg.every(Number.isFinite);
}

/** Project one normalized cardiac-cycle phase onto an existing PV loop. */
export function projectPVCursor(
  loop: PVLoopData | null | undefined,
  phase: number,
): PVCursorProjection {
  const normalizedPhase = normalizeComparisonPhase(phase);
  if (!validLoop(loop)) return unavailableCursor(normalizedPhase);

  const cursorIndex = Math.min(
    loop.volume_ml.length - 1,
    Math.floor(normalizedPhase * loop.volume_ml.length),
  );

  return {
    phase: normalizedPhase,
    available: true,
    cursorIndex,
    volumeMl: loop.volume_ml[cursorIndex]!,
    pressureMmhg: loop.pressure_mmhg[cursorIndex]!,
  };
}

/** Project both comparison cursors without changing either source loop. */
export function projectComparisonPVCursors(
  clock: ComparisonClockState,
  baselineLoop: PVLoopData | null | undefined,
  scenarioLoop: PVLoopData | null | undefined,
): ComparisonPVProjection {
  return {
    baseline: projectPVCursor(baselineLoop, clock.baselinePhase),
    scenario: projectPVCursor(scenarioLoop, clock.scenarioPhase),
    uncertainty: {
      mode: "scalar_pv_linked",
      pointwiseLoopAvailable: false,
      heldShape: true,
      limitation: PV_UNCERTAINTY_LIMITATION,
    },
  };
}
