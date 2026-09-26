import { HeartComponentRegistry } from "@/lib/heart/registry";
import type { CardiacClockState } from "@/lib/heart/clock";
import type { ElectricalComponentId, ElectricalNode, ElectricalVisualState } from "./types";

const ELECTRICAL_NODE_IDS: readonly ElectricalComponentId[] = [
  "sa-node",
  "av-node",
  "bundle-of-his",
  "left-bundle-branch",
  "right-bundle-branch",
  "purkinje-network",
];

const NODE_POSITIONS: Record<ElectricalComponentId, readonly [number, number, number]> = {
  "sa-node": [0.38, 0.55, 0.88],
  "av-node": [0.05, 0.2, 0.9],
  "bundle-of-his": [0, -0.05, 0.9],
  "left-bundle-branch": [-0.2, -0.25, 0.88],
  "right-bundle-branch": [0.2, -0.25, 0.88],
  "purkinje-network": [0, -0.45, 0.88],
};

const ACTIVATION_PHASES: Record<ElectricalComponentId, number> = {
  "sa-node": 0.02,
  "av-node": 0.18,
  "bundle-of-his": 0.25,
  "left-bundle-branch": 0.34,
  "right-bundle-branch": 0.34,
  "purkinje-network": 0.46,
};

export const ELECTRICAL_NODES: readonly ElectricalNode[] = ELECTRICAL_NODE_IDS.map((id) => {
  const component = HeartComponentRegistry.getComponent(id);
  if (!component || component.category !== "electrical") {
    throw new Error(`Electrical registry component is missing: ${id}`);
  }
  return { id, position: NODE_POSITIONS[id], activationPhase: ACTIVATION_PHASES[id] };
});

export const ELECTRICAL_PATH: readonly ElectricalComponentId[] = [
  "sa-node",
  "av-node",
  "bundle-of-his",
  "left-bundle-branch",
  "purkinje-network",
];

export const ELECTRICAL_PATH_RIGHT: readonly ElectricalComponentId[] = [
  "bundle-of-his",
  "right-bundle-branch",
  "purkinje-network",
];

function wrapPhase(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return ((value % 1) + 1) % 1;
}

function nodeForPhase(phase: number): ElectricalComponentId {
  const normalized = wrapPhase(phase);
  let active = ELECTRICAL_NODES[0];
  for (const node of ELECTRICAL_NODES) {
    if (node.activationPhase <= normalized) active = node;
  }
  return active.id;
}

export function electricalVisualState(
  clockState: CardiacClockState,
  visible = true,
): ElectricalVisualState {
  const phase = wrapPhase(clockState.normalizedPhase);
  return {
    nodes: ELECTRICAL_NODES,
    phase,
    cardiacPhase: clockState.phase,
    activeNodeId: nodeForPhase(phase),
    pulseProgress: phase,
    visible,
  };
}

export function electricalNodePosition(id: ElectricalComponentId): readonly [number, number, number] {
  return NODE_POSITIONS[id];
}

export function electricalComponentName(id: ElectricalComponentId): string {
  return HeartComponentRegistry.getComponent(id)?.displayName ?? id;
}
