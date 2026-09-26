"""CDS Hooks service: discovery + patient-view + order-sign. Returns CARDS ONLY.

CareGuard never returns an automatically executable order. Order-sign produces
information/warning cards (with override requirements) for a clinician to act on.
"""

from __future__ import annotations

__all__ = ["discovery", "patient_view", "order_sign", "cards", "routes"]
