"use client";

import type { ReactElement } from "react";

import type { ParameterSensitivity } from "@/types/missing-piece";

type Props = { rows: ParameterSensitivity[] };

function formatNumber(value: number | null | undefined): string {
  return value != null && Number.isFinite(value) ? value.toFixed(3) : "Unavailable";
}

function methodLabel(row: ParameterSensitivity): string {
  if (!row.available) return "Unavailable";
  if (row.method === "finite_difference" || row.method === "local") {
    const scheme = row.difference_scheme;
    return scheme && scheme !== "unavailable"
      ? `Local finite difference (${scheme})`
      : "Local finite difference";
  }
  return `Local response (${row.method})`;
}

function unavailableLabel(reason: string): ReactElement {
  return <span className="text-amber-200/80">Unavailable ({reason})</span>;
}

export function SensitivityTable({ rows }: Props) {
  return (
    <div className="overflow-x-auto rounded-lg border border-white/10">
      <table
        className="w-full min-w-[42rem] text-left text-xs"
        aria-describedby="sensitivity-table-description"
      >
        <caption className="sr-only">Local sensitivity of the selected modeled target to each parameter</caption>
        <thead className="bg-white/5 text-white/60">
          <tr>
            <th scope="col" className="px-3 py-2 font-medium">Parameter</th>
            <th scope="col" className="px-3 py-2 font-medium">Target</th>
            <th scope="col" className="px-3 py-2 font-medium">Local response</th>
            <th scope="col" className="px-3 py-2 font-medium">
              Relative local-response heuristic
            </th>
            <th scope="col" className="px-3 py-2 font-medium">Method</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-3 py-4 text-center text-white/60">
                No sensitivity results are available.
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const rowUnavailable = !row.available;
              return (
                <tr
                  key={`${row.parameter_id}:${row.metric_id}`}
                  className="border-t border-white/10 align-top"
                >
                  <th scope="row" className="px-3 py-2 font-normal text-white">
                    {row.parameter_id}
                  </th>
                  <td className="px-3 py-2 text-white/70">{row.metric_id}</td>
                  <td className="px-3 py-2 tabular-nums text-white/80">
                    {rowUnavailable
                      ? unavailableLabel("local result")
                      : formatNumber(row.sensitivity)}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-white/80">
                    {rowUnavailable
                      ? unavailableLabel("relative heuristic")
                      : formatNumber(row.normalized_sensitivity)}
                  </td>
                  <td className="px-3 py-2 text-white/60">{methodLabel(row)}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
      <p id="sensitivity-table-description" className="border-t border-white/10 px-3 py-2 text-[11px] text-white/50">
        Local finite-difference responses describe model behavior near the baseline.
        The relative value is an uncertainty-impact ranking heuristic, not a confidence
        measure, probability, or clinical conclusion. Unavailable values were not estimated.
      </p>
    </div>
  );
}
