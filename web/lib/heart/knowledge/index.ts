import type { AnatomyKnowledge } from "@/lib/heart/contracts";
import { HEART_COMPONENTS, HeartComponentRegistry } from "@/lib/heart/registry";

const curated: Record<string, Omit<AnatomyKnowledge, "componentId">> = {
  "left-ventricle": { name: "Left ventricle", shortDescription: "The thick-walled chamber that sends oxygenated blood into systemic circulation.", primaryFunction: "Generates systemic pressure and forward stroke volume.", relatedStructures: ["mitral-valve", "aortic-valve", "aorta"], physiologyConcepts: ["contractility", "afterload", "stroke volume"] },
  "right-ventricle": { name: "Right ventricle", shortDescription: "The chamber that sends venous blood through the pulmonary circulation.", primaryFunction: "Generates pulmonary forward flow.", relatedStructures: ["tricuspid-valve", "pulmonary-valve", "pulmonary-artery"], physiologyConcepts: ["preload", "pulmonary flow"] },
  "left-atrium": { name: "Left atrium", shortDescription: "A receiving chamber for oxygenated blood returning from the lungs.", primaryFunction: "Transfers pulmonary venous return to the left ventricle.", relatedStructures: ["pulmonary-veins", "mitral-valve"], physiologyConcepts: ["filling", "preload"] },
  "right-atrium": { name: "Right atrium", shortDescription: "A receiving chamber for systemic venous return.", primaryFunction: "Transfers venous return to the right ventricle.", relatedStructures: ["superior-vena-cava", "inferior-vena-cava", "tricuspid-valve"], physiologyConcepts: ["venous return", "filling"] },
  "aortic-valve": { name: "Aortic valve", shortDescription: "A valve between the left ventricle and aorta.", primaryFunction: "Supports one-way ventricular ejection into the aorta.", relatedStructures: ["left-ventricle", "aorta"], physiologyConcepts: ["ejection", "pressure gradient"] },
  "mitral-valve": { name: "Mitral valve", shortDescription: "The valve between the left atrium and left ventricle.", primaryFunction: "Supports one-way ventricular filling.", relatedStructures: ["left-atrium", "left-ventricle"], physiologyConcepts: ["filling", "diastole"] },
  "tricuspid-valve": { name: "Tricuspid valve", shortDescription: "The valve between the right atrium and right ventricle.", primaryFunction: "Supports one-way right-sided filling.", relatedStructures: ["right-atrium", "right-ventricle"], physiologyConcepts: ["filling", "diastole"] },
  "pulmonary-valve": { name: "Pulmonary valve", shortDescription: "A valve between the right ventricle and pulmonary artery.", primaryFunction: "Supports one-way pulmonary ejection.", relatedStructures: ["right-ventricle", "pulmonary-artery"], physiologyConcepts: ["ejection", "pulmonary flow"] },
};

export function getAnatomyKnowledge(componentId: string): AnatomyKnowledge {
  const definition = HeartComponentRegistry.getComponent(componentId);
  if (!definition) return { componentId, name: "Unknown component", shortDescription: "This component is not present in the current semantic registry.", primaryFunction: "Unavailable", relatedStructures: [], physiologyConcepts: [] };
  const known = curated[componentId];
  if (known) return { componentId, ...known };
  return {
    componentId,
    name: definition.displayName,
    shortDescription: definition.anatomy.description,
    primaryFunction: definition.category === "functional" ? "Provides a synchronized visualization layer for the cardiac twin." : "Participates in coordinated cardiac structure and function.",
    relatedStructures: HEART_COMPONENTS.filter((entry) => entry.category === definition.category && entry.id !== componentId).slice(0, 3).map((entry) => entry.id),
    physiologyConcepts: definition.physiologyBindings.slice(0, 3),
  };
}
