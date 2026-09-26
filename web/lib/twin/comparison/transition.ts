/**
 * Pure state model for the visual transition between a single heart and the
 * paired comparison view.
 *
 * Progress is normalized: 0 is the single-heart layout and 1 is the split
 * layout. Keeping progress as the source of truth makes a transition
 * interruptible without rebuilding either rendered heart or its state.
 */

export type ComparisonPresentation = "single" | "split";

export interface ComparisonTransitionState {
  /** Current visual position: 0 = single, 1 = split. */
  readonly progress: number;
  /** Presentation the transition is currently moving toward. */
  readonly target: ComparisonPresentation;
  /** Duration used to travel from one endpoint to the other. */
  readonly durationMs: number;
  /** Whether an animated transition is still in progress. */
  readonly active: boolean;
  /** Whether transitions should resolve immediately. */
  readonly reducedMotion: boolean;
}

export interface CreateComparisonTransitionOptions {
  readonly initialPresentation?: ComparisonPresentation;
  readonly durationMs?: number;
  readonly reducedMotion?: boolean;
}

export interface RequestComparisonTransitionOptions {
  readonly reducedMotion?: boolean;
  readonly durationMs?: number;
}

const DEFAULT_DURATION_MS = 360;

function assertFiniteNumber(value: number, name: string): void {
  if (!Number.isFinite(value)) throw new RangeError(`${name} must be finite`);
}

function assertNonNegative(value: number, name: string): void {
  assertFiniteNumber(value, name);
  if (value < 0) throw new RangeError(`${name} must be non-negative`);
}

function assertPresentation(value: ComparisonPresentation, name: string): void {
  if (value !== "single" && value !== "split") {
    throw new RangeError(`Unsupported ${name}: ${String(value)}`);
  }
}

function endpointFor(presentation: ComparisonPresentation): number {
  return presentation === "split" ? 1 : 0;
}

function presentationFor(progress: number): ComparisonPresentation {
  return progress >= 0.5 ? "split" : "single";
}

function clampProgress(progress: number): number {
  assertFiniteNumber(progress, "Comparison transition progress");
  return Math.min(1, Math.max(0, progress));
}

function validatedDuration(durationMs: number): number {
  assertNonNegative(durationMs, "Comparison transition duration");
  return durationMs;
}

function settle(
  progress: number,
  target: ComparisonPresentation,
  durationMs: number,
  reducedMotion: boolean,
): ComparisonTransitionState {
  const endpoint = endpointFor(target);
  return {
    progress: endpoint,
    target,
    durationMs,
    active: false,
    reducedMotion,
  };
}

/** Create an initially settled one-heart or split comparison presentation. */
export function createComparisonTransition(
  options: CreateComparisonTransitionOptions = {},
): ComparisonTransitionState {
  const initialPresentation = options.initialPresentation ?? "single";
  const reducedMotion = options.reducedMotion ?? false;
  const requestedDuration = validatedDuration(options.durationMs ?? DEFAULT_DURATION_MS);
  const durationMs = reducedMotion ? 0 : requestedDuration;

  assertPresentation(initialPresentation, "comparison presentation");
  return settle(
    endpointFor(initialPresentation),
    initialPresentation,
    durationMs,
    reducedMotion,
  );
}

/**
 * Request a new endpoint without resetting the current visual progress.
 *
 * If a split is interrupted while opening and the user requests the single
 * view, the reversal starts at that exact progress. This is the key property
 * that keeps the transition smooth and avoids remounting/resetting the heart.
 */
export function requestComparisonTransition(
  state: ComparisonTransitionState,
  target: ComparisonPresentation,
  options: RequestComparisonTransitionOptions = {},
): ComparisonTransitionState {
  assertPresentation(target, "comparison transition target");

  const reducedMotion = options.reducedMotion ?? state.reducedMotion;
  const requestedDuration = validatedDuration(options.durationMs ?? state.durationMs);
  const durationMs = reducedMotion ? 0 : requestedDuration;
  const progress = clampProgress(state.progress);
  const endpoint = endpointFor(target);

  if (reducedMotion || durationMs === 0 || progress === endpoint) {
    return settle(progress, target, durationMs, reducedMotion);
  }

  return {
    progress,
    target,
    durationMs,
    active: true,
    reducedMotion,
  };
}

/** Advance an active transition by an explicit elapsed wall-clock duration. */
export function advanceComparisonTransition(
  state: ComparisonTransitionState,
  elapsedMs: number,
): ComparisonTransitionState {
  assertNonNegative(elapsedMs, "Comparison transition elapsed time");
  if (!state.active || elapsedMs === 0) return { ...state };

  const endpoint = endpointFor(state.target);
  const distance = endpoint - state.progress;
  const direction = Math.sign(distance);
  const step = state.durationMs === 0 ? 1 : elapsedMs / state.durationMs;
  const nextProgress = clampProgress(state.progress + direction * step);

  if (nextProgress === endpoint) {
    return settle(nextProgress, state.target, state.durationMs, state.reducedMotion);
  }

  return {
    ...state,
    progress: nextProgress,
  };
}

/** Return the settled presentation represented by the current progress. */
export function currentComparisonPresentation(
  state: ComparisonTransitionState,
): ComparisonPresentation {
  return presentationFor(clampProgress(state.progress));
}

/** Return a fresh copy with the current transition halted at its current frame. */
export function pauseComparisonTransition(
  state: ComparisonTransitionState,
): ComparisonTransitionState {
  return { ...state, active: false };
}
