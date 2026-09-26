"""Approved-tool registry. Claude may request ONLY these CareGuard tools; any
other tool name is refused. Tools never browse the web, run shell, write to the
DB, mutate DualBeat state, create prescriptions, or generate doses.
"""

from __future__ import annotations

APPROVED_TOOLS = frozenset(
    {
        "get_fhir_resource",
        "search_local_guidelines",
        "retrieve_guideline_passage",
        "normalize_medication_rxnorm",
        "retrieve_openfda_label",
        "retrieve_dailymed_label",
        "build_cross_organ_matrix",
        "run_hearttwin_scenario",
        "get_existing_case_state",
        "write_audit_event",
    }
)

FORBIDDEN_CAPABILITIES = frozenset(
    {
        "browse_web",
        "execute_shell",
        "query_unapproved_source",
        "write_database",
        "mutate_hearttwin_state",
        "create_prescription",
        "generate_dose",
    }
)


def is_approved(tool_name: str) -> bool:
    return tool_name in APPROVED_TOOLS


def assert_approved(tool_name: str) -> None:
    if tool_name not in APPROVED_TOOLS:
        from python.hearttwin.careguard.errors import SafetyBoundaryError

        raise SafetyBoundaryError(
            f"tool {tool_name!r} is not on the CareGuard approved list",
            reason="unapproved_tool",
        )
