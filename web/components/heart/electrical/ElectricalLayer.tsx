"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import {
  AdditiveBlending,
  Color,
  Mesh,
  MeshBasicMaterial,
  SphereGeometry,
} from "three";
import { electricalVisualState, ELECTRICAL_PATH, ELECTRICAL_PATH_RIGHT, electricalNodePosition } from "./model";
import type { ElectricalComponentId, ElectricalLayerProps } from "./types";

const SIGNAL = new Color("#6de7ee");
const SIGNAL_DIM = new Color("#287d92");

function ConductionPath({ path, opacity }: { path: readonly ElectricalComponentId[]; opacity: number }) {
  const points = useMemo(() => path.map((id) => electricalNodePosition(id)), [path]);
  return <Line points={points} color={SIGNAL_DIM} transparent opacity={opacity} depthWrite={false} />;
}

function ElectricalNodeMesh({ id, clock, animate, radius, opacity }: { id: ElectricalComponentId; clock: ElectricalLayerProps["clock"]; animate: boolean; radius: number; opacity: number }) {
  const mesh = useRef<Mesh>(null);
  const geometry = useMemo(() => new SphereGeometry(radius, 12, 8), [radius]);
  const material = useMemo(() => new MeshBasicMaterial({ color: SIGNAL, transparent: true, opacity, blending: AdditiveBlending, depthWrite: false }), [opacity]);

  useEffect(() => () => { geometry.dispose(); material.dispose(); }, [geometry, material]);

  useFrame((_, delta) => {
    const active = animate && electricalVisualState(clock.getState()).activeNodeId === id;
    const target = active ? 1.35 : 1;
    const next = mesh.current?.scale.x;
    if (mesh.current && next !== undefined) {
      const amount = 1 - Math.exp(-10 * Math.min(delta, 0.05));
      mesh.current.scale.setScalar(next + (target - next) * amount);
    }
  });

  return <mesh ref={mesh} position={electricalNodePosition(id)} geometry={geometry} material={material} userData={{ heartComponentId: id }} />;
}

export function ElectricalLayer({ clock, animate = true, visible = true, opacity = 0.72, nodeRadius = 0.035 }: ElectricalLayerProps) {
  const state = clock.getState();
  const visual = electricalVisualState(state, visible);
  const nodes = useMemo(() => visual.nodes, [visual.nodes]);
  const layerOpacity = visible ? Math.max(0, Math.min(1, opacity)) : 0;

  if (!visible) return null;

  return (
    <group name="electrical-layer" visible={visual.visible} userData={{ heartComponentId: "electrical-propagation", visualizationOnly: true }}>
      <ConductionPath path={ELECTRICAL_PATH} opacity={layerOpacity * 0.62} />
      <ConductionPath path={ELECTRICAL_PATH_RIGHT} opacity={layerOpacity * 0.62} />
      {nodes.map((node) => (
        <ElectricalNodeMesh
          key={node.id}
          id={node.id}
          clock={clock}
          animate={animate}
          radius={nodeRadius}
          opacity={layerOpacity}
        />
      ))}
    </group>
  );
}
