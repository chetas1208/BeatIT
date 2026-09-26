"""CareGuard workflow routes (FHIR import, staged runs, getters, feedback,
export, CDS Hooks). Registered onto the router built in ``api.py``.

Populated across build phases; Phase 1 leaves this as a no-op so health/config/
system-check are independently testable. Later phases attach the real handlers.
"""

from __future__ import annotations

from fastapi import APIRouter


def register_routes(router: APIRouter) -> None:
    # Phase 2+: FHIR import, case get.
    try:
        from python.hearttwin.careguard.routes_fhir import attach as attach_fhir

        attach_fhir(router)
    except ImportError:
        pass

    # Phase 3+: staged runs.
    try:
        from python.hearttwin.careguard.routes_runs import attach as attach_runs

        attach_runs(router)
    except ImportError:
        pass

    # Phase 4/5: case getters, feedback, export, CDS Hooks.
    try:
        from python.hearttwin.careguard.routes_case import attach as attach_case

        attach_case(router)
    except ImportError:
        pass

    try:
        from python.hearttwin.careguard.cds_hooks.routes import attach as attach_cds

        attach_cds(router)
    except ImportError:
        pass

    # MedSafety: Multimorbidity Medication Safety routes.
    try:
        from python.hearttwin.careguard.routes_medication import attach as attach_med

        attach_med(router)
    except ImportError:
        pass

    # VISTA-3D imaging routes (optional, external).
    try:
        from python.hearttwin.careguard.routes_vista import attach as attach_vista

        attach_vista(router)
    except ImportError:
        pass

    # Care-evaluation harness + Copilot analysis agent.
    try:
        from python.hearttwin.careguard.routes_analysis import attach as attach_analysis

        attach_analysis(router)
    except ImportError:
        pass

    # CT imaging + VISTA linkage/fusion routes (additive; verified-linkage gated).
    try:
        from python.hearttwin.careguard.imaging.routes_imaging import attach as attach_imaging

        attach_imaging(router)
    except ImportError:
        pass

    # Case browser + demo routes (additive; list/select/demo packaged cases).
    try:
        from python.hearttwin.careguard.imaging.routes_cases import attach as attach_cases

        attach_cases(router)
    except ImportError:
        pass

    # Per-case CT + echo modality mapping (matched external research modalities).
    try:
        from python.hearttwin.careguard.imaging.routes_modality import attach as attach_modality

        attach_modality(router)
    except ImportError:
        pass
