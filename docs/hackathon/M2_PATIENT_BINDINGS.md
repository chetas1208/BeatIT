# M2 patient bindings

`web/lib/heart/patient/adapter.ts` maps a supplied `CardiacTwinState` and optional `CardiacFindings` into `PatientComponentState`. It reads only registered fields and source-map entries. Values are omitted when absent; no component receives a fabricated default merely because it exists in the registry.

Evidence kinds remain distinct: directly observed, extracted, derived, default model prior, simulated, and unavailable. Global values such as cardiac output and oxygen-delivery indices are labeled as global model outputs when shown on component reports. The global systolic finding is attached to the left ventricle, not falsely localized to every AHA segment.
