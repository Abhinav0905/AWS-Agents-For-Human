"""Decision wording shared by the decisions_request tool and the governor."""

from __future__ import annotations

from ..models import DECISION_LABELS

GATED_TOOLS = {"pay": "D1", "close_account": "D4", "elect_option": "D4"}


def gate_types(tool_name: str, args: dict, heir_conflict: bool) -> list[str]:
    """Which decision types a tool call would trip, before any approval is considered."""
    types: list[str] = []
    if heir_conflict and tool_name not in {"decisions_request", "notes_log", "ledger_get_task", "ledger_update_task"}:
        types.append("D5")
    if tool_name in GATED_TOOLS:
        types.append(GATED_TOOLS[tool_name])
    if tool_name in {"submit_notification", "submit_document"}:
        if args.get("includes_original") is True:
            types.append("D2")
        if args.get("signature_kind", "none") not in (None, "none"):
            types.append("D3")
    return sorted(set(types))


def default_question(types: list[str], institution_name: str, tool_name: str, args: dict,
                     certificates_left: int | None = None) -> tuple[str, list[str], str]:
    """Question, options and recommendation for a governor-raised decision."""
    if types == ["D1"]:
        amt = int(args.get("amount_cents", 0)) / 100.0
        return (f"Pay ${amt:,.2f} to {institution_name} from the estate account? The amount matches their final bill.",
                ["pay", "hold"], "pay")
    if types == ["D4"] and tool_name == "close_account":
        return (f"Close the accounts at {institution_name} and take a cashier's check payable to the estate? "
                "This cannot be undone.", ["close", "wait"], "close")
    if types == ["D4"]:
        return (f"Record the election '{args.get('option')}' with {institution_name}? This cannot be undone.",
                [str(args.get("option", "proceed")), "wait"], str(args.get("option", "proceed")))
    parts = [DECISION_LABELS[t] for t in types]
    left = f" You have {certificates_left} certified originals left." if "D2" in types and certificates_left is not None else ""
    return (f"{institution_name} needs: {'; '.join(parts)}. Proceed?{left}", ["proceed", "hold"], "proceed")
