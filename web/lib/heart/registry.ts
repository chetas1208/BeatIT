/** Semantic cardiac anatomy. Geometry and data bindings belong here, not in renderers. */

export type HeartComponentCategory =
  | "chamber"
  | "valve"
  | "vessel"
  | "coronary"
  | "myocardial_segment"
  | "electrical"
  | "functional";

export type CoronaryTerritory = "LAD" | "LCX" | "RCA";

export interface HeartComponentDefinition {
  id: string;
  category: HeartComponentCategory;
  displayName: string;
  anatomy: { description: string; parentId?: string };
  geometry: { meshNames?: readonly string[]; fallbackRegion?: string };
  physiologyBindings: readonly string[];
  evidenceBindings: readonly string[];
  findingBindings: readonly string[];
  ahaSegment?: number;
  coronaryTerritory?: CoronaryTerritory;
  supportsSelection: boolean;
  supportsHover: boolean;
  supportsFocus: boolean;
  supportsUncertainty: boolean;
  supportsDifferenceMode: boolean;
}

export interface HeartComponentVisualState {
  visible: boolean;
  hovered: boolean;
  selected: boolean;
  focused: boolean;
  opacity: number;
  emphasis: number;
  confidence?: number;
  findingSeverity?: number;
  differenceMagnitude?: number;
}

export const DEFAULT_HEART_COMPONENT_VISUAL_STATE: HeartComponentVisualState = {
  visible: true,
  hovered: false,
  selected: false,
  focused: false,
  opacity: 1,
  emphasis: 0,
};

const common = {
  supportsSelection: true,
  supportsHover: true,
  supportsFocus: true,
  supportsUncertainty: true,
  supportsDifferenceMode: true,
} as const;

interface ComponentOptions {
  parentId?: string;
  ahaSegment?: number;
  coronaryTerritory?: CoronaryTerritory;
  geometry?: HeartComponentDefinition["geometry"];
  evidenceBindings?: readonly string[];
  findingBindings?: readonly string[];
}

function component(
  id: string,
  category: HeartComponentCategory,
  displayName: string,
  description: string,
  bindings: string[],
  options: ComponentOptions = {},
): HeartComponentDefinition {
  return {
    id,
    category,
    displayName,
    anatomy: { description, ...(options.parentId ? { parentId: options.parentId } : {}) },
    geometry: options.geometry ?? { fallbackRegion: id },
    physiologyBindings: bindings,
    evidenceBindings: options.evidenceBindings ?? [],
    findingBindings: options.findingBindings ?? [],
    ahaSegment: options.ahaSegment,
    coronaryTerritory: options.coronaryTerritory,
    ...common,
  };
}

const chambers = [
  component("left-atrium", "chamber", "Left atrium", "Receives oxygenated blood from the pulmonary veins.", ["preload_index", "filling_pressure_index"]),
  component("right-atrium", "chamber", "Right atrium", "Receives systemic venous return.", ["preload_index", "filling_pressure_index"]),
  component("left-ventricle", "chamber", "Left ventricle", "Generates systemic ventricular pressure and forward flow.", ["contractility_index", "afterload_index", "stroke_volume_ml"]),
  component("right-ventricle", "chamber", "Right ventricle", "Generates pulmonary ventricular pressure and flow.", ["preload_index", "afterload_index", "cardiac_output_l_min"]),
];

const valves = [
  component("mitral-valve", "valve", "Mitral valve", "Controls flow from the left atrium to the left ventricle.", ["ventricular_filling"]),
  component("tricuspid-valve", "valve", "Tricuspid valve", "Controls flow from the right atrium to the right ventricle.", ["ventricular_filling"]),
  component("aortic-valve", "valve", "Aortic valve", "Controls left-ventricular ejection into the aorta.", ["ventricular_ejection"]),
  component("pulmonary-valve", "valve", "Pulmonary valve", "Controls right-ventricular ejection into the pulmonary artery.", ["ventricular_ejection"]),
];

const vessels = [
  ["aorta", "Aorta", "Carries oxygenated blood from the left ventricle to systemic circulation."],
  ["pulmonary-artery", "Pulmonary artery", "Carries deoxygenated blood from the right ventricle to the lungs."],
  ["pulmonary-veins", "Pulmonary veins", "Return oxygenated blood from the lungs to the left atrium."],
  ["superior-vena-cava", "Superior vena cava", "Returns blood from the upper body to the right atrium."],
  ["inferior-vena-cava", "Inferior vena cava", "Returns blood from the lower body to the right atrium."],
].map(([id, name, description]) => component(id, "vessel", name, description, ["cardiac_output_l_min"]));

const coronaries = [
  ["lad", "LAD", "Left anterior descending coronary artery", "LAD"],
  ["lcx", "LCX", "Left circumflex coronary artery", "LCX"],
  ["rca", "RCA", "Right coronary artery", "RCA"],
].map(([id, name, description, territory]) => component(id, "coronary", name, description, ["oxygen_delivery_index", "myocardial_oxygen_demand_index"], { coronaryTerritory: territory as CoronaryTerritory }));

// Keep this aligned with the repository's deterministic finding layer:
// `cardiac_findings.py` localizes anteroseptal/anterior/apical regions to LAD,
// inferoseptal/inferior regions to RCA, and posterior/lateral regions to LCx.
// Segment 17 remains LAD here because that is the explicit apical territory
// used by that layer; this is a project mapping, not a universal clinical rule.
const ahaTerritories: CoronaryTerritory[] = [
  "LAD", "LAD", "RCA", "RCA", "LCX", "LCX", "LAD", "LAD", "RCA",
  "RCA", "LCX", "LCX", "LAD", "LAD", "RCA", "LCX", "LAD",
];
const myocardium = Array.from({ length: 17 }, (_, index) => {
  const segment = index + 1;
  return component(`aha-${String(segment).padStart(2, "0")}`, "myocardial_segment", `AHA segment ${String(segment).padStart(2, "0")}`, `Stable AHA-17 myocardial segment ${String(segment).padStart(2, "0")}.`, ["scar_fraction", "contractility_index", "inflammation_index"], {
    ahaSegment: segment,
    coronaryTerritory: ahaTerritories[index],
    findingBindings: [`aha-${String(segment).padStart(2, "0")}`],
  });
});

const electrical = [
  component("sa-node", "electrical", "SA node", "Primary cardiac pacemaker region.", ["rhythm_label", "rr_interval_ms"]),
  component("av-node", "electrical", "AV node", "Regulates atrioventricular conduction.", ["conduction_delay_score", "qrs_duration_ms"]),
  component("bundle-of-his", "electrical", "Bundle of His", "Carries conduction from the AV node into the ventricles.", ["qrs_duration_ms"]),
  component("left-bundle-branch", "electrical", "Left bundle branch", "Conducts activation through the left ventricle.", ["qrs_duration_ms"]),
  component("right-bundle-branch", "electrical", "Right bundle branch", "Conducts activation through the right ventricle.", ["qrs_duration_ms"]),
  component("purkinje-network", "electrical", "Purkinje network", "Distributes ventricular activation.", ["qrs_duration_ms", "qtc_ms"]),
];

const functional = [
  component("electrical-propagation", "functional", "Electrical propagation", "Visualization layer for activation timing.", ["rr_interval_ms", "qrs_duration_ms"]),
  component("blood-flow", "functional", "Blood flow", "Visualization layer for flow direction and intensity.", ["cardiac_output_l_min", "pv_loop_area_index"]),
  component("contraction", "functional", "Contraction", "Visualization layer for phase-aware myocardial motion.", ["contractility_index", "ejection_fraction_pct"]),
  component("pathology-overlay", "functional", "Pathology overlay", "Data-bound finding and tissue-state overlay.", ["scar_fraction", "inflammation_index"]),
  component("difference-overlay", "functional", "Difference overlay", "Reserved for future bounded baseline/scenario comparison.", []),
  component("uncertainty-overlay", "functional", "Uncertainty overlay", "Reserved for future uncertainty visualization.", []),
];

export const HEART_COMPONENTS: readonly HeartComponentDefinition[] = [
  ...chambers,
  ...valves,
  ...vessels,
  ...coronaries,
  ...myocardium,
  ...electrical,
  ...functional,
];

const byId = new Map(HEART_COMPONENTS.map((entry) => [entry.id, entry]));

function normalizeCoronaryTerritory(value: string | null | undefined): CoronaryTerritory | undefined {
  switch (value?.trim().toUpperCase()) {
    case "LAD":
      return "LAD";
    case "LCX":
      return "LCX";
    case "RCA":
      return "RCA";
    default:
      return undefined;
  }
}

export const HeartComponentRegistry = {
  getComponent(id: string) { return byId.get(id); },
  getComponentsByCategory(category: HeartComponentCategory) { return HEART_COMPONENTS.filter((entry) => entry.category === category); },
  getComponentsForFinding(finding: { id?: string; aha_segments?: number[]; territory?: string | null }) {
    const territory = normalizeCoronaryTerritory(finding.territory);
    return HEART_COMPONENTS.filter((entry) => (
      (finding.id !== undefined && entry.findingBindings.includes(finding.id))
      || (finding.aha_segments?.includes(entry.ahaSegment ?? -1) ?? false)
      || (territory !== undefined && entry.coronaryTerritory === territory)
    ));
  },
  getComponentsForAhaSegment(segment: number) { return HEART_COMPONENTS.filter((entry) => entry.ahaSegment === segment); },
  getComponentsForCoronaryTerritory(territory: CoronaryTerritory) { return HEART_COMPONENTS.filter((entry) => entry.coronaryTerritory === territory); },
};
