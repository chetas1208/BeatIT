import { getAnatomyKnowledge } from "@/lib/heart/knowledge";
import { getPatientComponentState } from "@/lib/heart/patient";
import { buildComponentReport } from "@/lib/heart/report";
import type {
  AnatomyKnowledge,
  ComponentReport,
  PatientBindingInput,
  PatientComponentState,
} from "@/lib/heart/contracts";

export interface ComponentInspectorModel {
  report: ComponentReport;
  knowledge: AnatomyKnowledge;
  patientState: PatientComponentState;
}

export function buildComponentInspectorModel(
  componentId: string,
  input: PatientBindingInput,
): ComponentInspectorModel | null {
  const report = buildComponentReport(componentId, input);
  const patientState = getPatientComponentState(componentId, input);

  if (!report || !patientState) return null;

  return {
    report,
    knowledge: getAnatomyKnowledge(componentId),
    patientState,
  };
}
