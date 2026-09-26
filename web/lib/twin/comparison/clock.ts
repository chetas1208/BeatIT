import type { ComparisonClockMode } from "@/lib/twin/comparison/contracts";

export type { ComparisonClockMode } from "@/lib/twin/comparison/contracts";

export interface ComparisonClockHeartRates {
  readonly baselineHeartRateBpm: number;
  readonly scenarioHeartRateBpm: number;
}

export interface ComparisonClockState extends ComparisonClockHeartRates {
  readonly mode: ComparisonClockMode;
  readonly playing: boolean;
  /** The central scrub position, always normalized to [0, 1). */
  readonly normalizedPhase: number;
  readonly baselinePhase: number;
  readonly scenarioPhase: number;
  readonly playbackSpeed: number;
}

export interface CreateComparisonClockOptions {
  readonly mode?: ComparisonClockMode;
  readonly playing?: boolean;
  readonly normalizedPhase?: number;
  readonly playbackSpeed?: number;
}

export interface ComparisonClockRateInput {
  readonly baselineHeartRateBpm: number;
  readonly scenarioHeartRateBpm: number;
}

export interface ComparisonClockStepOptions {
  /** Elapsed wall-clock time in milliseconds. */
  readonly elapsedMs: number;
}

const DEFAULT_PLAYBACK_SPEED = 1;
const MIN_HEART_RATE_BPM = 1;

function assertFiniteNumber(value: number, name: string): void {
  if (!Number.isFinite(value)) throw new RangeError(`${name} must be finite`);
}

function assertHeartRate(value: number, name: string): void {
  assertFiniteNumber(value, name);
  if (value < MIN_HEART_RATE_BPM) {
    throw new RangeError(`${name} must be at least ${MIN_HEART_RATE_BPM} bpm`);
  }
}

function assertMode(mode: ComparisonClockMode): void {
  if (mode !== "phase_locked" && mode !== "physiologic_rate") {
    throw new RangeError(`Unsupported comparison clock mode: ${String(mode)}`);
  }
}

function assertPlaybackSpeed(value: number): void {
  assertFiniteNumber(value, "Comparison clock playback speed");
  if (value <= 0) throw new RangeError("Comparison clock playback speed must be positive");
}

function assertElapsedMs(value: number): void {
  assertFiniteNumber(value, "Comparison clock elapsed time");
  if (value < 0) throw new RangeError("Comparison clock elapsed time must be non-negative");
}

/** Normalize a phase without mutating or retaining the caller's value. */
export function normalizeComparisonPhase(phase: number): number {
  assertFiniteNumber(phase, "Comparison clock phase");
  return ((phase % 1) + 1) % 1;
}

function cyclePhaseDelta(elapsedMs: number, heartRateBpm: number, playbackSpeed: number): number {
  return (elapsedMs * heartRateBpm * playbackSpeed) / 60000;
}

function validatedRates(rates: ComparisonClockHeartRates): ComparisonClockHeartRates {
  assertHeartRate(rates.baselineHeartRateBpm, "Baseline heart rate");
  assertHeartRate(rates.scenarioHeartRateBpm, "Scenario heart rate");
  return {
    baselineHeartRateBpm: rates.baselineHeartRateBpm,
    scenarioHeartRateBpm: rates.scenarioHeartRateBpm,
  };
}

/**
 * Create the single source of timing truth for a paired comparison.
 *
 * Heart rates are retained as display/timing inputs only. No canonical twin
 * state is changed, and the returned state is safe to use as an immutable
 * reducer value.
 */
export function createComparisonClock(
  rates: ComparisonClockHeartRates,
  options: CreateComparisonClockOptions = {},
): ComparisonClockState {
  const validated = validatedRates(rates);
  const mode = options.mode ?? "phase_locked";
  const playbackSpeed = options.playbackSpeed ?? DEFAULT_PLAYBACK_SPEED;
  const normalizedPhase = normalizeComparisonPhase(options.normalizedPhase ?? 0);

  assertMode(mode);
  assertPlaybackSpeed(playbackSpeed);

  return {
    ...validated,
    mode,
    playing: options.playing ?? false,
    normalizedPhase,
    baselinePhase: normalizedPhase,
    scenarioPhase: normalizedPhase,
    playbackSpeed,
  };
}

export function playComparisonClock(state: ComparisonClockState): ComparisonClockState {
  return { ...state, playing: true };
}

export function pauseComparisonClock(state: ComparisonClockState): ComparisonClockState {
  return { ...state, playing: false };
}

/** Reset to the start of the cycle and leave the clock paused. */
export function resetComparisonClock(state: ComparisonClockState): ComparisonClockState {
  return {
    ...state,
    playing: false,
    normalizedPhase: 0,
    baselinePhase: 0,
    scenarioPhase: 0,
  };
}

/**
 * Seek is a visual re-sync operation. Both sides begin at the requested
 * phase; physiologic-rate mode will intentionally drift again on the next
 * advance when their modeled rates differ.
 */
export function seekComparisonClock(
  state: ComparisonClockState,
  normalizedPhase: number,
): ComparisonClockState {
  const phase = normalizeComparisonPhase(normalizedPhase);
  return {
    ...state,
    normalizedPhase: phase,
    baselinePhase: phase,
    scenarioPhase: phase,
  };
}

export function setComparisonClockMode(
  state: ComparisonClockState,
  mode: ComparisonClockMode,
): ComparisonClockState {
  assertMode(mode);
  if (mode === state.mode) return { ...state };

  const phase = mode === "phase_locked" ? state.baselinePhase : state.normalizedPhase;
  return {
    ...state,
    mode,
    normalizedPhase: phase,
    baselinePhase: phase,
    scenarioPhase: phase,
  };
}

export function setComparisonClockPlaybackSpeed(
  state: ComparisonClockState,
  playbackSpeed: number,
): ComparisonClockState {
  assertPlaybackSpeed(playbackSpeed);
  return { ...state, playbackSpeed };
}

export function setComparisonClockHeartRates(
  state: ComparisonClockState,
  rates: ComparisonClockHeartRates,
): ComparisonClockState {
  return { ...state, ...validatedRates(rates) };
}

/** Align both side cursors without changing either side's heart rate. */
export function resyncComparisonClock(state: ComparisonClockState): ComparisonClockState {
  return seekComparisonClock(state, state.baselinePhase);
}

/**
 * Advance the clock by an explicit wall-clock delta.
 *
 * In phase-locked mode the baseline rate is the shared visual clock source;
 * both rendered hearts receive that same normalized phase while their HR
 * labels remain unchanged. In physiologic-rate mode each side advances by
 * BPM / 60, so unequal rates naturally produce phase drift.
 */
export function advanceComparisonClock(
  state: ComparisonClockState,
  { elapsedMs }: ComparisonClockStepOptions,
): ComparisonClockState {
  assertElapsedMs(elapsedMs);
  if (!state.playing || elapsedMs === 0) return { ...state };

  if (state.mode === "phase_locked") {
    const phase = normalizeComparisonPhase(
      state.normalizedPhase + cyclePhaseDelta(elapsedMs, state.baselineHeartRateBpm, state.playbackSpeed),
    );
    return {
      ...state,
      normalizedPhase: phase,
      baselinePhase: phase,
      scenarioPhase: phase,
    };
  }

  const baselinePhase = normalizeComparisonPhase(
    state.baselinePhase + cyclePhaseDelta(elapsedMs, state.baselineHeartRateBpm, state.playbackSpeed),
  );
  const scenarioPhase = normalizeComparisonPhase(
    state.scenarioPhase + cyclePhaseDelta(elapsedMs, state.scenarioHeartRateBpm, state.playbackSpeed),
  );

  return {
    ...state,
    normalizedPhase: baselinePhase,
    baselinePhase,
    scenarioPhase,
  };
}

/** Return a fresh phase snapshot for renderers and chart cursors. */
export function getComparisonClockPhases(state: ComparisonClockState): {
  readonly normalizedPhase: number;
  readonly baselinePhase: number;
  readonly scenarioPhase: number;
} {
  return {
    normalizedPhase: state.normalizedPhase,
    baselinePhase: state.baselinePhase,
    scenarioPhase: state.scenarioPhase,
  };
}
