"""Ledger, playbook and decision tools for the runner. Each is a Strands @tool closure over the store."""

from __future__ import annotations

import json

from strands import tool

from .. import playbooks
from ..models import Decision
from ..store import SQLiteLedgerStore, new_id


def make_tools(store: SQLiteLedgerStore) -> list:
    @tool
    def ledger_get_task(task_id: str) -> str:
        """Read one task from the estate ledger (state, flags, case_ref, history, approval)."""
        return store.get_task(task_id).model_dump_json()

    @tool
    def ledger_update_task(task_id: str, state: str, note: str, case_ref: str = "", due_sim_date: str = "",
                           attempts: int = -1) -> str:
        """Update a task after acting on it. state is one of queued|drafted|sent|awaiting_institution|
        awaiting_human|blocked|done|failed. Always include a one-line note. Set case_ref after a submission,
        due_sim_date (YYYY-MM-DD) to schedule the next check, attempts to record follow-ups."""
        patch: dict = {"state": state, "note": note}
        if case_ref:
            patch["case_ref"] = case_ref
        if due_sim_date:
            patch["due_sim_date"] = due_sim_date
        if attempts >= 0:
            patch["attempts"] = attempts
        task = store.update_task(task_id, **patch)
        return json.dumps({"ok": True, "task_id": task.id, "state": task.state, "due_sim_date": task.due_sim_date})

    @tool
    def schedule_follow_up(task_id: str, days: int, note: str) -> str:
        """Schedule the next check on a task in N simulated days from today and record why."""
        from datetime import date, timedelta

        today = date.fromisoformat(store.get_clock())
        due = (today + timedelta(days=days)).isoformat()
        task = store.update_task(task_id, due_sim_date=due, note=note)
        return json.dumps({"ok": True, "due_sim_date": task.due_sim_date})

    @tool
    def notes_log(task_id: str, text: str) -> str:
        """Add a note to a task's history without changing its state."""
        store.update_task(task_id, note=text)
        return json.dumps({"ok": True})

    @tool
    def get_playbook(kind: str) -> str:
        """Playbook for an institution kind (bank, utility, telecom, insurer, pension, subscription, credit_bureau,
        dmv, brokerage, gym): documents usually needed, whether originals are typical, escalation ladder."""
        return playbooks.load(kind).model_dump_json()

    @tool
    def render_letter(kind: str, institution_name: str, account_last4: str) -> str:
        """Render the standard notification letter for an institution from the estate's details."""
        est = store.get_estate()
        return playbooks.render_letter(kind, institution_name, account_last4, est.decedent_name, est.executor_name,
                                       est.date_of_death.isoformat())

    @tool
    def decisions_request(task_id: str, types: list[str], question: str, options: list[str],
                          recommendation: str) -> str:
        """Ask the executor for a decision and stop working this task. types is a list from D1 (money leaves the
        estate), D2 (an original certified document leaves her hands), D3 (her signature, a notary or an in-person
        visit), D4 (irreversible step), D5 (an heir disagrees). Ask once per event, in plain language, with two or
        three options and your recommendation."""
        task = store.get_task(task_id)
        types = sorted({t.strip().upper() for t in types})
        existing = store.find_open_decision(task_id, types)
        if existing:
            return json.dumps({"ok": True, "decision_id": existing.id, "status": existing.status,
                               "instruction": "A decision for this is already open. Stop working this task."})
        inst = store.get_institution(task.institution_id)
        d = Decision(id=new_id("dec"), estate_id=store.estate_id, task_id=task_id, institution_id=task.institution_id,
                     types=types, question=question, options=options, recommendation=recommendation,  # type: ignore[arg-type]
                     raised_by="agent", sim_date=store.get_clock())
        store.create_decision(d)
        store.log_event("decision_raised", f"{inst.name if inst else task.institution_id}: {question}",
                        {"decision_id": d.id, "types": types, "raised_by": "agent"})
        return json.dumps({"ok": True, "decision_id": d.id, "status": "open",
                           "instruction": "Decision recorded and sent to the executor. Stop working this task."})

    return [ledger_get_task, ledger_update_task, schedule_follow_up, notes_log, get_playbook, render_letter,
            decisions_request]
