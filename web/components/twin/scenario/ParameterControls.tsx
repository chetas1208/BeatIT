"use client";

import type { ScenarioParameterKey } from "@/lib/twin/scenario/propagation";
import {
  SCENARIO_PARAMETER_DEFINITIONS,
  SCENARIO_PARAMETER_KEYS,
  type ScenarioParameterValues,
} from "@/lib/twin/scenario/parameters";

export function ParameterControls({
  values,
  baseline,
  onChange,
  disabled = false,
}: {
  values: ScenarioParameterValues;
  baseline: ScenarioParameterValues | null;
  onChange: (key: ScenarioParameterKey, value: number) => string | null;
  disabled?: boolean;
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {SCENARIO_PARAMETER_KEYS.map((key) => {
        const definition = SCENARIO_PARAMETER_DEFINITIONS[key];
        const value = values[key];
        const base = baseline?.[key] ?? value;
        const delta = value - base;
        return (
          <label key={key} className="rounded border border-[var(--ht-line)] bg-surface-2 px-2.5 py-2">
            <span className="flex items-center justify-between gap-2 text-[0.68rem] font-medium text-ink-2">
              <span>{definition.label}</span>
              <span className="ht-mono text-muted">{value.toFixed(2)} {definition.unit}</span>
            </span>
            <input
              className="mt-1.5 w-full accent-accent-bright"
              type="range"
              min={definition.min}
              max={definition.max}
              step={definition.unit === "bpm" ? 1 : 0.01}
              value={value}
              disabled={disabled}
              aria-label={`${definition.label} scenario value`}
              aria-describedby={`scenario-${key}-description`}
              onChange={(event) => { onChange(key, Number(event.target.value)); }}
            />
            <span id={`scenario-${key}-description`} className="mt-1 flex justify-between text-[0.62rem] text-muted">
              <span>baseline {base.toFixed(2)}</span>
              <span className={delta === 0 ? "text-muted" : delta > 0 ? "text-warn" : "text-signal"}>
                Δ {delta >= 0 ? "+" : ""}{delta.toFixed(2)}
              </span>
            </span>
          </label>
        );
      })}
    </div>
  );
}
