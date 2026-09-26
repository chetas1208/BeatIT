"""Read-only bridge into DualBeat's existing deterministic simulation.

CareGuard NEVER reimplements a DualBeat formula and NEVER mutates DualBeat
state. This package deep-copies inputs, calls the existing tested functions, and
maps results into CareGuard schemas with explicit uncertainty. It predicts no
clinical outcome — only physiologic direction for comparison.
"""

from __future__ import annotations

__all__ = ["hearttwin_adapter", "parameter_mapping", "scenario_validator", "result_mapper"]
