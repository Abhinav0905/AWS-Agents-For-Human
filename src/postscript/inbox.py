"""The decision inbox: how a human answers. Every answer is a receipt too."""

from __future__ import annotations

from .models import PolicyRecord
from .store import SQLiteLedgerStore


def resolve(store: SQLiteLedgerStore, decision_id: str, action: str, chosen_option: str | None, by: str,
            sim_date: str | None = None) -> dict:
    """action: approve | deny | edit. edit approves with a different option than recommended."""
    sim_date = sim_date or store.get_clock()
    d = store.get_decision(decision_id)
    if d.status != "open":
        return {"ok": False, "error": f"decision {decision_id} is already {d.status}"}
    if action == "deny":
        status, chosen = "denied", chosen_option or "denied"
    elif action == "edit":
        status, chosen = "edited", chosen_option or d.recommendation
    else:
        status, chosen = "approved", chosen_option or d.recommendation
    d = store.resolve_decision(decision_id, status, chosen, by, sim_date)
    if "D5" in d.types and status in ("approved", "edited") and chosen != "pause":
        store.update_task(d.task_id, flags={"heir_conflict": False}, note="executor chose to continue despite objection")
    inst = store.get_institution(d.institution_id)
    store.append_receipt(store.make_receipt(
        tool=f"inbox.{action}", args={"decision_id": decision_id, "chosen_option": chosen},
        result_summary=f"{status}: {chosen} ({'+'.join(d.types)}) for {inst.name if inst else d.institution_id}",
        task_id=d.task_id, actor=f"executor:{by}", evidence=[f"decision:{decision_id}"],
        policy=PolicyRecord(decision="n/a", policy_id="human", human_approval_id=decision_id)))
    store.log_event("decision_resolved", f"{inst.name if inst else d.institution_id}: {status} ({chosen})",
                    {"decision_id": decision_id, "types": d.types, "by": by}, sim_date=sim_date)
    return {"ok": True, "decision_id": decision_id, "status": status, "chosen_option": chosen}
