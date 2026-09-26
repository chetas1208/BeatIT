/**
 * Source-honest signal context for the M7 paired view.
 *
 * This module only carries supplied signal samples and provenance. It never
 * reconstructs a waveform from heart rate, RR, rhythm labels, or any other
 * scalar cardiac value.
 */

export type ComparisonSignalSource = "observed" | "extracted" | "simulated" | "missing";

export type ComparisonSignalAvailability = "available" | "missing";

export interface SignalContextInput {
  readonly source?: ComparisonSignalSource;
  readonly waveform?: readonly number[] | null;
  readonly sampleRateHz?: number | null;
  readonly lead?: string | null;
  readonly unit?: string | null;
  readonly sourceId?: string | null;
  readonly method?: string | null;
  readonly confidence?: number | null;
  readonly reason?: string | null;
}

export interface ComparisonSignalContext {
  readonly availability: ComparisonSignalAvailability;
  readonly source: ComparisonSignalSource;
  /** Null is intentional: missing signals are not replaced with a trace. */
  readonly waveform: readonly number[] | null;
  readonly sampleRateHz: number | null;
  readonly lead: string | null;
  readonly unit: string | null;
  readonly sourceId: string | null;
  readonly method: string | null;
  readonly confidence: number | null;
  readonly label: string;
  readonly reason: string | null;
}

export type PairedSignalCoverage =
  | "both"
  | "baseline_only"
  | "scenario_only"
  | "neither";

export interface PairedSignalContext {
  readonly baseline: ComparisonSignalContext;
  readonly scenario: ComparisonSignalContext;
  /** Coverage only; this does not authorize waveform subtraction or a delta. */
  readonly coverage: PairedSignalCoverage;
}

const SOURCE_LABELS: Readonly<Record<ComparisonSignalSource, string>> = {
  observed: "ECG · observed",
  extracted: "ECG · extracted",
  simulated: "ECG · simulated",
  missing: "ECG unavailable",
};

const MISSING_REASON = "No supported numeric waveform was supplied.";

function finiteNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function optionalText(value: string | null | undefined): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

function copyWaveform(value: readonly number[] | null | undefined): readonly number[] | null {
  if (value == null) return null;
  if (!Array.isArray(value) || value.length === 0 || !value.every(Number.isFinite)) return null;
  return Object.freeze([...value]);
}

function missingContext(reason: string | null = null): ComparisonSignalContext {
  return Object.freeze({
    availability: "missing",
    source: "missing",
    waveform: null,
    sampleRateHz: null,
    lead: null,
    unit: null,
    sourceId: null,
    method: null,
    confidence: null,
    label: SOURCE_LABELS.missing,
    reason: reason ?? MISSING_REASON,
  });
}

/**
 * Copy one explicitly sourced signal into an immutable comparison context.
 * A missing source or invalid/empty samples remain missing instead of being
 * inferred from scalar timing fields.
 */
export function createComparisonSignalContext(
  input: SignalContextInput = {},
): ComparisonSignalContext {
  const source = input.source;
  const waveform = copyWaveform(input.waveform);

  if (source === "missing" && input.waveform != null) {
    throw new RangeError("A missing signal context cannot contain waveform samples");
  }

  if (source === undefined || source === "missing") {
    return missingContext(optionalText(input.reason));
  }

  if (waveform === null) {
    return missingContext(
      optionalText(input.reason) ??
        `Signal source is ${source}, but no valid numeric waveform was supplied.`,
    );
  }

  return Object.freeze({
    availability: "available",
    source,
    waveform,
    sampleRateHz: finiteNumber(input.sampleRateHz) !== null && input.sampleRateHz! > 0
      ? input.sampleRateHz!
      : null,
    lead: optionalText(input.lead),
    unit: optionalText(input.unit),
    sourceId: optionalText(input.sourceId),
    method: optionalText(input.method),
    confidence: finiteNumber(input.confidence) !== null && input.confidence! >= 0 && input.confidence! <= 1
      ? input.confidence!
      : null,
    label: SOURCE_LABELS[source],
    reason: optionalText(input.reason),
  });
}

function pairedCoverage(
  baseline: ComparisonSignalContext,
  scenario: ComparisonSignalContext,
): PairedSignalCoverage {
  const baselineAvailable = baseline.availability === "available";
  const scenarioAvailable = scenario.availability === "available";
  if (baselineAvailable && scenarioAvailable) return "both";
  if (baselineAvailable) return "baseline_only";
  if (scenarioAvailable) return "scenario_only";
  return "neither";
}

/** Build an isolated baseline/scenario signal context without aligning or fabricating samples. */
export function createPairedSignalContext(input: {
  readonly baseline?: SignalContextInput;
  readonly scenario?: SignalContextInput;
} = {}): PairedSignalContext {
  const baseline = createComparisonSignalContext(input.baseline);
  const scenario = createComparisonSignalContext(input.scenario);
  return Object.freeze({
    baseline,
    scenario,
    coverage: pairedCoverage(baseline, scenario),
  });
}

export function hasComparisonSignal(context: ComparisonSignalContext): boolean {
  return context.availability === "available" && context.waveform !== null;
}
