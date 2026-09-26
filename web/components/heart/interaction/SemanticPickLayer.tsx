import { useMemo } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { HEART_COMPONENTS, type HeartComponentDefinition } from "@/lib/heart/registry";

const POSITIONS: Record<string, readonly [number, number, number]> = {
  "left-ventricle": [-0.25, -0.25, 0.65], "right-ventricle": [0.34, -0.2, 0.6], "left-atrium": [-0.35, 0.48, 0.55], "right-atrium": [0.35, 0.48, 0.5],
  "mitral-valve": [-0.16, 0.18, 0.8], "tricuspid-valve": [0.16, 0.18, 0.8], "aortic-valve": [0, 0.42, 0.8], "pulmonary-valve": [0.28, 0.42, 0.72],
  aorta: [0, 0.78, 0.35], "pulmonary-artery": [0.3, 0.7, 0.35], "pulmonary-veins": [-0.55, 0.5, 0.25], "superior-vena-cava": [0.55, 0.76, 0.15], "inferior-vena-cava": [0.55, -0.7, 0.15],
  lad: [0.05, -0.25, 0.92], lcx: [-0.58, 0.04, 0.35], rca: [0.53, -0.05, 0.4], "sa-node": [0.38, 0.55, 0.85], "av-node": [0.05, 0.2, 0.86], "bundle-of-his": [0, -0.05, 0.86], "left-bundle-branch": [-0.2, -0.25, 0.84], "right-bundle-branch": [0.2, -0.25, 0.84], "purkinje-network": [0, -0.45, 0.84],
};

function positionFor(component: HeartComponentDefinition, index: number): readonly [number, number, number] {
  if (POSITIONS[component.id]) return POSITIONS[component.id];
  const segment = component.ahaSegment ?? index + 1;
  const angle = (segment / 17) * Math.PI * 2;
  return [Math.cos(angle) * 0.62, -0.2 + Math.sin(angle) * 0.42, 0.78];
}

export function SemanticPickLayer({ selectedId, hoveredId, onHover, onSelect }: { selectedId: string | null; hoveredId: string | null; onHover: (id: string | null) => void; onSelect: (id: string) => void }) {
  const entries = useMemo(() => HEART_COMPONENTS.filter((entry) => entry.category !== "functional"), []);
  return <group name="semantic-pick-layer">{entries.map((entry, index) => { const position = positionFor(entry, index); const active = selectedId === entry.id || hoveredId === entry.id; const onPointerOver = (event: ThreeEvent<PointerEvent>) => { event.stopPropagation(); onHover(entry.id); }; const onClick = (event: ThreeEvent<MouseEvent>) => { event.stopPropagation(); onSelect(entry.id); }; return <mesh key={entry.id} position={position} scale={active ? 1.25 : 1} onPointerOver={onPointerOver} onPointerOut={() => onHover(null)} onClick={onClick} userData={{ heartComponentId: entry.id }}><sphereGeometry args={[0.075, 8, 8]} /><meshBasicMaterial transparent opacity={active ? 0.12 : 0} depthWrite={false} color={active ? "#25b8c8" : "#ffffff"} /></mesh>; })}</group>;
}
