"""One tick = the mailroom, then the runner over every task due today."""

from __future__ import annotations

from datetime import date, timedelta

from ..store import SQLiteLedgerStore
from .clerk import match_institution
from .runner import RunnerContext

WORKABLE = ("queued", "drafted", "awaiting_institution")


def mailroom(store: SQLiteLedgerStore, inbox: list[dict], sim_date: str) -> list[dict]:
    """Turn inbound mail into ledger updates. No model involved: this is sorting, not judgment."""
    handled = []
    tasks = store.list_tasks()
    for msg in inbox:
        kind = msg.get("kind")
        if kind == "institution":
            hits = [t for t in tasks if t.case_ref and t.case_ref == msg.get("case_ref")]
            for t in hits:
                if t.state == "awaiting_institution":
                    store.update_task(t.id, due_sim_date=sim_date, note=f"Reply from {msg['from']}: {msg.get('status')}",
                                      sim_date=sim_date)
            store.log_event("inbound", f"{msg['from']}: {msg.get('body', '')[:140]}",
                            {"case_ref": msg.get("case_ref"), "status": msg.get("status")}, sim_date=sim_date)
        elif kind == "heir":
            # the heir names the institution; match it to the ledger's institution the same way the clerk does
            listing = [{"id": i.id, "name": i.name, "kind": i.kind} for i in store.list_institutions()]
            target = match_institution(listing, msg.get("institution_name", ""), "")
            hits = [t for t in tasks if t.institution_id == target and t.state != "done"]
            for t in hits:
                if msg.get("action") == "object":
                    store.update_task(t.id, flags={"heir_conflict": True}, due_sim_date=sim_date,
                                      state="queued" if t.state in ("awaiting_institution", "blocked") else t.state,
                                      note=f"Heir {msg['from']} objects: {msg.get('body', '')[:120]}", sim_date=sim_date)
                elif msg.get("action") == "agree":
                    task = store.get_task(t.id)
                    if task.approval and "D5" in task.approval.types:
                        store.consume_approval(t.id)
                    new_state = "awaiting_institution" if task.case_ref else "queued"
                    store.update_task(t.id, flags={"heir_conflict": False}, state=new_state, due_sim_date=sim_date,
                                      note=f"Heir {msg['from']} agrees: {msg.get('body', '')[:120]}", sim_date=sim_date)
            store.log_event("inbound", f"{msg['from']} ({msg.get('action')}): {msg.get('body', '')[:140]}",
                            {"institution_id": msg.get("institution_id")}, sim_date=sim_date)
        handled.append(msg)
    return handled


def run_tick(store: SQLiteLedgerStore, runner: RunnerContext, sim_date: str, sim_start: str,
             inbox: list[dict] | None = None, max_tasks: int = 30) -> dict:
    store.set_clock(sim_date)
    if inbox:
        mailroom(store, inbox, sim_date)
    due = [t for t in store.list_tasks(states=WORKABLE, due_before=sim_date)][:max_tasks]
    store.log_event("tick", f"tick {sim_date}: {len(due)} task(s) due", {"due": [t.id for t in due]}, sim_date=sim_date)
    results = []
    for task in due:
        # a task re-queued with an approval today is worked today; skip tasks already advanced by an earlier agent
        current = store.get_task(task.id)
        if current.state not in WORKABLE or current.due_sim_date > sim_date:
            continue
        try:
            results.append(runner.run_task(task.id, sim_date, sim_start))
        except Exception as exc:  # a failing task must not stop the tick
            store.update_task(task.id, state="blocked",
                              due_sim_date=(date.fromisoformat(sim_date) + timedelta(days=1)).isoformat(),
                              note=f"runner error: {exc}"[:200], sim_date=sim_date)
            store.log_event("note", f"runner error on {task.id}: {exc}"[:300], {"task_id": task.id}, sim_date=sim_date)
            results.append({"task_id": task.id, "error": str(exc)[:200]})
    return {"sim_date": sim_date, "worked": results}
