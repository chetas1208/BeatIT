/** Pure camera state for the two independently rendered comparison hearts. */

export type ComparisonCameraInstance = "baseline" | "counterfactual";
export type ComparisonCameraMode = "linked" | "independent";

/** Semantic registry IDs (for example, `left-ventricle`), never mesh IDs. */
export type SemanticComponentId = string;
export type CameraVector = readonly [number, number, number];

export interface CameraOrientation {
  /** Horizontal orbit angle in degrees. */
  readonly azimuthDeg: number;
  /** Vertical orbit angle in degrees. */
  readonly elevationDeg: number;
  /** Roll is kept at zero by default to preserve anatomical orientation. */
  readonly rollDeg: number;
}

export interface ComparisonCameraPose {
  readonly target: CameraVector;
  readonly distance: number;
  readonly orientation: CameraOrientation;
}

export interface CameraFocusTarget {
  readonly componentId: SemanticComponentId;
  readonly target: CameraVector;
  readonly distance?: number;
}

export interface ComparisonCameraPane {
  readonly pose: ComparisonCameraPose;
  readonly focusedComponentId: SemanticComponentId | null;
}

export interface ComparisonCameraState {
  readonly mode: ComparisonCameraMode;
  readonly baseline: ComparisonCameraPane;
  readonly counterfactual: ComparisonCameraPane;
}

export interface CreateComparisonCameraOptions {
  readonly mode?: ComparisonCameraMode;
  readonly pose?: ComparisonCameraPose;
}

const DEFAULT_DISTANCE = 4.1;
const DEFAULT_ORIENTATION: CameraOrientation = {
  azimuthDeg: 0,
  elevationDeg: 0,
  rollDeg: 0,
};

export const DEFAULT_COMPARISON_CAMERA_POSE: ComparisonCameraPose = {
  target: [0, -0.05, 0],
  distance: DEFAULT_DISTANCE,
  orientation: DEFAULT_ORIENTATION,
};

function assertFinite(value: number, name: string): void {
  if (!Number.isFinite(value)) throw new RangeError(`${name} must be finite`);
}

function assertVector(vector: CameraVector, name: string): void {
  if (vector.length !== 3) throw new RangeError(`${name} must have three coordinates`);
  vector.forEach((value, index) => assertFinite(value, `${name}[${index}]`));
}

function assertMode(mode: ComparisonCameraMode): void {
  if (mode !== "linked" && mode !== "independent") {
    throw new RangeError(`Unsupported comparison camera mode: ${String(mode)}`);
  }
}

function assertInstance(instance: ComparisonCameraInstance): void {
  if (instance !== "baseline" && instance !== "counterfactual") {
    throw new RangeError(`Unsupported comparison camera instance: ${String(instance)}`);
  }
}

function assertComponentId(componentId: SemanticComponentId): void {
  if (typeof componentId !== "string" || componentId.trim().length === 0) {
    throw new RangeError("A non-empty semantic component ID is required");
  }
}

function normalizeAngle(degrees: number): number {
  return ((degrees + 180) % 360 + 360) % 360 - 180;
}

function copyVector(vector: CameraVector): CameraVector {
  return [vector[0], vector[1], vector[2]];
}

function copyOrientation(orientation: CameraOrientation): CameraOrientation {
  return {
    azimuthDeg: normalizeAngle(orientation.azimuthDeg),
    elevationDeg: orientation.elevationDeg,
    rollDeg: normalizeAngle(orientation.rollDeg),
  };
}

function copyPose(pose: ComparisonCameraPose): ComparisonCameraPose {
  assertVector(pose.target, "Camera target");
  assertFinite(pose.distance, "Camera distance");
  if (pose.distance <= 0) throw new RangeError("Camera distance must be positive");
  assertFinite(pose.orientation.azimuthDeg, "Camera azimuth");
  assertFinite(pose.orientation.elevationDeg, "Camera elevation");
  assertFinite(pose.orientation.rollDeg, "Camera roll");
  if (pose.orientation.elevationDeg < -90 || pose.orientation.elevationDeg > 90) {
    throw new RangeError("Camera elevation must be between -90 and 90 degrees");
  }

  return {
    target: copyVector(pose.target),
    distance: pose.distance,
    orientation: copyOrientation(pose.orientation),
  };
}

function copyPane(pane: ComparisonCameraPane): ComparisonCameraPane {
  if (pane.focusedComponentId !== null) assertComponentId(pane.focusedComponentId);
  return {
    pose: copyPose(pane.pose),
    focusedComponentId: pane.focusedComponentId,
  };
}

function pane(pose: ComparisonCameraPose, focusedComponentId: SemanticComponentId | null = null): ComparisonCameraPane {
  return copyPane({ pose, focusedComponentId });
}

function paneFor(state: ComparisonCameraState, instance: ComparisonCameraInstance): ComparisonCameraPane {
  assertInstance(instance);
  return state[instance];
}

/** Create two camera panes with the same deterministic anatomical orientation. */
export function createComparisonCameraState(
  options: CreateComparisonCameraOptions = {},
): ComparisonCameraState {
  const mode = options.mode ?? "linked";
  assertMode(mode);
  const pose = copyPose(options.pose ?? DEFAULT_COMPARISON_CAMERA_POSE);
  return {
    mode,
    baseline: pane(pose),
    counterfactual: pane(pose),
  };
}

/**
 * Switch linkage without changing the source camera's current pose.
 * Entering linked mode uses baseline as the canonical orientation source.
 */
export function setComparisonCameraMode(
  state: ComparisonCameraState,
  mode: ComparisonCameraMode,
): ComparisonCameraState {
  assertMode(mode);
  if (mode === "independent") {
    return {
      mode,
      baseline: copyPane(state.baseline),
      counterfactual: copyPane(state.counterfactual),
    };
  }

  const baseline = copyPane(state.baseline);
  return {
    mode,
    baseline,
    counterfactual: copyPane({
      pose: baseline.pose,
      focusedComponentId: baseline.focusedComponentId,
    }),
  };
}

/** Apply a camera orbit/target update to one pane, mirroring it when linked. */
export function setComparisonCameraPose(
  state: ComparisonCameraState,
  instance: ComparisonCameraInstance,
  pose: ComparisonCameraPose,
): ComparisonCameraState {
  const nextPose = copyPose(pose);
  if (state.mode === "linked") {
    return {
      mode: state.mode,
      baseline: pane(nextPose, state.baseline.focusedComponentId),
      counterfactual: pane(nextPose, state.counterfactual.focusedComponentId),
    };
  }

  assertInstance(instance);
  return {
    mode: state.mode,
    baseline: instance === "baseline" ? pane(nextPose, state.baseline.focusedComponentId) : copyPane(state.baseline),
    counterfactual: instance === "counterfactual" ? pane(nextPose, state.counterfactual.focusedComponentId) : copyPane(state.counterfactual),
  };
}

/**
 * Focus a semantic anatomy target. Linked focus deliberately applies to both
 * panes so corresponding anatomy stays comparable without coupling selections.
 */
export function focusComparisonCamera(
  state: ComparisonCameraState,
  instance: ComparisonCameraInstance,
  target: CameraFocusTarget,
): ComparisonCameraState {
  assertInstance(instance);
  assertComponentId(target.componentId);
  assertVector(target.target, "Camera focus target");
  if (target.distance !== undefined) {
    assertFinite(target.distance, "Camera focus distance");
    if (target.distance <= 0) throw new RangeError("Camera focus distance must be positive");
  }

  const update = (source: ComparisonCameraPane): ComparisonCameraPane => pane(
    {
      ...source.pose,
      target: copyVector(target.target),
      distance: target.distance ?? source.pose.distance,
    },
    target.componentId,
  );

  if (state.mode === "linked") {
    return {
      mode: state.mode,
      baseline: update(state.baseline),
      counterfactual: update(state.counterfactual),
    };
  }

  return {
    mode: state.mode,
    baseline: instance === "baseline" ? update(state.baseline) : copyPane(state.baseline),
    counterfactual: instance === "counterfactual" ? update(state.counterfactual) : copyPane(state.counterfactual),
  };
}

export function clearComparisonCameraFocus(
  state: ComparisonCameraState,
  instance: ComparisonCameraInstance,
): ComparisonCameraState {
  assertInstance(instance);
  if (state.mode === "linked") {
    return {
      mode: state.mode,
      baseline: pane(state.baseline.pose),
      counterfactual: pane(state.counterfactual.pose),
    };
  }
  return {
    mode: state.mode,
    baseline: instance === "baseline" ? pane(state.baseline.pose) : copyPane(state.baseline),
    counterfactual: instance === "counterfactual" ? pane(state.counterfactual.pose) : copyPane(state.counterfactual),
  };
}

/** Reset both views while retaining whether the user chose linked mode. */
export function resetComparisonCamera(state: ComparisonCameraState): ComparisonCameraState {
  const pose = copyPose(DEFAULT_COMPARISON_CAMERA_POSE);
  return {
    mode: state.mode,
    baseline: pane(pose),
    counterfactual: pane(pose),
  };
}

/** Return a defensive snapshot for a renderer without exposing mutable arrays. */
export function getComparisonCameraPane(
  state: ComparisonCameraState,
  instance: ComparisonCameraInstance,
): ComparisonCameraPane {
  return copyPane(paneFor(state, instance));
}
