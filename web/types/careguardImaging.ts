// CT imaging + VISTA types (additive; mirrors the imaging linkage/VISTA contract).

export type LinkageStatus =
  | "same_subject_verified"
  | "imaging_native_same_subject"
  | "imaging_only"
  | "no_linked_ct"
  | "access_pending"
  | "invalid"
  | "prohibited_cross_dataset_match";

export interface CtImaging {
  status: LinkageStatus;
  source_dataset: string | null;
  source_subject_id: string | null;
  source_study_id: string | null;
  source_series_id: string | null;
  same_subject_as_clinical_record: boolean;
  linkage_evidence: unknown[];
  linkage_manifest_path: string | null;
  linkage_confidence: "verified" | "unavailable" | "prohibited";
  vista_eligible: boolean;
  reason: string;
}

export interface VistaStructureResult {
  structure_id: string;
  requested_label: string;
  endpoint_label: string;
  status: "segmented" | "not_found" | "unsupported" | "failed";
  volume_ml: number | null;
  voxel_count: number | null;
  confidence: number | null; // only if the endpoint returns a defined measure
  warnings: string[];
  label: string;
}

export interface EndpointCapabilities {
  service: string;
  version: string;
  supported_classes: string[];
  reachable: boolean;
  source: string;
  warnings: string[];
}

export const MODEL_DERIVED_LABEL =
  "Model-derived research segmentation requiring clinician review.";
export const IMAGING_ONLY_NOTICE =
  "This CT is an imaging benchmark record and is not linked to the current clinical case.";

// Human-facing copy per linkage state — the linkage state is NEVER hidden.
export const LINKAGE_BADGE: Record<
  LinkageStatus,
  { label: string; tone: "ok" | "info" | "warn" | "danger" }
> = {
  same_subject_verified: { label: "Verified same-subject CT", tone: "ok" },
  imaging_native_same_subject: { label: "Imaging-native linked case", tone: "ok" },
  imaging_only: { label: "Imaging-only benchmark case", tone: "info" },
  no_linked_ct: { label: "No linked CT available", tone: "warn" },
  access_pending: { label: "Access pending", tone: "warn" },
  invalid: { label: "Invalid imaging record", tone: "danger" },
  prohibited_cross_dataset_match: {
    label: "Invalid cross-dataset pairing removed",
    tone: "danger",
  },
};
