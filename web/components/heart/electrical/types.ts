import type { CardiacClock, CardiacClockState } from "@/lib/heart/clock";

export type ElectricalComponentId =
  | "sa-node"
  | "av-node"
  | "bundle-of-his"
  | "left-bundle-branch"
  | "right-bundle-branch"
  | "purkinje-network";

export interface ElectricalNode {
  id: ElectricalComponentId;
  position: readonly [number, number, number];
  activationPhase: number;
}

export interface ElectricalVisualState {
  nodes: readonly ElectricalNode[];
  phase: number;
  cardiacPhase: CardiacClockState["phase"];
  activeNodeId: ElectricalComponentId;
  pulseProgress: number;
  visible: boolean;
}

export interface ElectricalLayerProps {
  clock: CardiacClock;
  animate?: boolean;
  visible?: boolean;
  opacity?: number;
  nodeRadius?: number;
}
