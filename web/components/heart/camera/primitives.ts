import type { CameraFocusTarget } from "@/lib/heart/contracts";

export type CameraVector = readonly [number, number, number];

export interface CameraPose {
  position: CameraVector;
  lookAt: CameraVector;
}

export interface CameraState {
  pose: CameraPose;
  focusedComponentId: string | null;
}

/** Matches the current heart scene framing without depending on patient data. */
export const DEFAULT_CAMERA_POSE: CameraPose = {
  position: [0.4, 0.25, 4.1],
  lookAt: [0, -0.05, 0],
};

function copyVector(vector: CameraVector): CameraVector {
  return [vector[0], vector[1], vector[2]];
}

function copyPose(pose: CameraPose): CameraPose {
  return {
    position: copyVector(pose.position),
    lookAt: copyVector(pose.lookAt),
  };
}

function clampUnit(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function safeDelta(delta: number): number {
  return Number.isFinite(delta) ? delta : 0;
}

export function createInitialCameraState(): CameraState {
  return {
    pose: copyPose(DEFAULT_CAMERA_POSE),
    focusedComponentId: null,
  };
}

/** Creates a focus pose from the shared semantic target contract. */
export function createFocusCameraPose(target: CameraFocusTarget): CameraPose {
  return {
    position: copyVector(target.position),
    lookAt: copyVector(target.lookAt),
  };
}

export function focusCamera(state: CameraState, target: CameraFocusTarget): CameraState {
  return {
    pose: createFocusCameraPose(target),
    focusedComponentId: target.componentId,
  };
}

export function resetCamera(): CameraState {
  return createInitialCameraState();
}

/**
 * Interpolates both camera vectors for a render-loop-friendly transition.
 * `progress` is clamped so callers can safely pass an accumulated value.
 */
export function interpolateCameraPose(from: CameraPose, to: CameraPose, progress: number): CameraPose {
  const t = clampUnit(progress);
  return {
    position: [
      from.position[0] + (to.position[0] - from.position[0]) * t,
      from.position[1] + (to.position[1] - from.position[1]) * t,
      from.position[2] + (to.position[2] - from.position[2]) * t,
    ],
    lookAt: [
      from.lookAt[0] + (to.lookAt[0] - from.lookAt[0]) * t,
      from.lookAt[1] + (to.lookAt[1] - from.lookAt[1]) * t,
      from.lookAt[2] + (to.lookAt[2] - from.lookAt[2]) * t,
    ],
  };
}

/** Advances a pose toward a destination by a normalized progress increment. */
export function advanceCameraPose(
  current: CameraPose,
  destination: CameraPose,
  progressDelta: number,
): CameraPose {
  return interpolateCameraPose(current, destination, safeDelta(progressDelta));
}

const COMPONENT_FOCUS: Record<string, CameraFocusTarget> = {
  "left-ventricle": { componentId: "left-ventricle", position: [0.2, 0.1, 3.25], lookAt: [-0.25, -0.25, 0], distance: 3.25 },
  "right-ventricle": { componentId: "right-ventricle", position: [-0.15, 0.1, 3.25], lookAt: [0.34, -0.2, 0], distance: 3.25 },
  "aortic-valve": { componentId: "aortic-valve", position: [0.1, 0.3, 3.35], lookAt: [0, 0.42, 0], distance: 3.35 },
  "mitral-valve": { componentId: "mitral-valve", position: [-0.1, 0.2, 3.35], lookAt: [-0.16, 0.18, 0], distance: 3.35 },
};

export function focusTargetForComponent(componentId: string): CameraFocusTarget {
  return COMPONENT_FOCUS[componentId] ?? { componentId, position: [0.4, 0.25, 3.65], lookAt: [0, 0, 0], distance: 3.65 };
}
