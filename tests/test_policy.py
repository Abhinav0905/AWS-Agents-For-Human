"""The five gates, checked directly against the Cedar policy and through the Strands governor."""

import json
from pathlib import Path

import cedarpy
import pytest
from strands import Agent, tool

from postscript.agents.models import ScriptedModel
from postscript.models import Estate, Institution, Task
from postscript.policy.governor import POLICY_PATH, PostscriptGovernor
from postscript.receipts.hooks import ReceiptHooks
from postscript.store import SQLiteLedgerStore

POLICIES = Path(POLICY_PATH).read_text()
BASE = {"hour_utc": 1, "call_count": 1, "task_id": "t", "heir_conflict": False, "human_approved": False, "approval_types": ""}


def decide(action, inp, **session):
    req = {"principal": 'Agent::"runner"', "action": f'Action::"{action}"', "resource": 'Resource::"agent"',
           "context": {"input": inp, "session": {**BASE, **session}}}
    return cedarpy.is_authorized(req, POLICIES, [], None).decision.value


@pytest.mark.parametrize("action,inp", [
    ("check_status", {"case_ref": "X"}), ("get_requirements", {"institution_id": "x"}),
    ("send_follow_up", {"case_ref": "X", "text": "t", "certified": False}),
    ("submit_notification", {"includes_original": False, "signature_kind": "none"}),
    ("submit_document", {"case_ref": "X", "doc_type": "form", "includes_original": False, "signature_kind": "none"}),
    ("decisions_request", {"task_id": "t"}), ("ledger_update_task", {"task_id": "t"}),
])
def test_clerical_work_is_permitted(action, inp):
    assert decide(action, inp) == "Allow"


@pytest.mark.parametrize("action,inp,types", [
    ("pay", {"case_ref": "X", "amount_cents": 14217}, "D1"),
    ("submit_notification", {"includes_original": True, "signature_kind": "none"}, "D2"),
    ("submit_document", {"case_ref": "X", "doc_type": "f", "includes_original": False, "signature_kind": "notarized"}, "D3"),
    ("close_account", {"case_ref": "X"}, "D4"),
    ("elect_option", {"case_ref": "X", "option": "lump_sum"}, "D4"),
])
def test_gated_actions_are_denied_without_approval_and_allowed_with_it(action, inp, types):
    assert decide(action, inp) == "Deny"
    assert decide(action, inp, human_approved=True) == "Allow"


def test_heir_conflict_freezes_everything_but_asking():
    assert decide("check_status", {"case_ref": "X"}, heir_conflict=True) == "Deny"
    assert decide("pay", {"case_ref": "X", "amount_cents": 1}, heir_conflict=True, human_approved=True) == "Deny"
    assert decide("decisions_request", {"task_id": "t"}, heir_conflict=True) == "Allow"
    assert decide("ledger_update_task", {"task_id": "t"}, heir_conflict=True) == "Allow"


def test_unknown_tools_and_undeclared_packets_are_denied():
    assert decide("delete_everything", {}) == "Deny"
    assert decide("submit_notification", {"documents": []}) == "Deny"


# ---- through the Strands agent loop -----------------------------------------------------------

class _TryToPay:
    """A 'model' that attempts to pay a bill, then reports what happened."""

    def next(self, messages, tool_specs, system_prompt):
        calls = [b for m in messages for b in m.get("content", []) if isinstance(b, dict) and "toolUse" in b]
        if not calls:
            return ("tool", "pay", {"case_ref": "PAC-1", "amount_cents": 14217, "method": "estate_account"})
        return ("text", "done")

    def structured(self, *a, **k):
        raise NotImplementedError


def _store(tmp_path):
    s = SQLiteLedgerStore(tmp_path / "ledger.db", reset=True)
    s.save_estate(Estate(id="est_alvarez", decedent_name="Bob", date_of_death="2026-03-02", executor_name="Maya",
                         executor_id="maya", heirs=["Maya", "Daniel"], certified_copies_on_hand=5))
    s.set_clock("2026-03-11")
    s.upsert_institution(Institution(id="pacific_coast_power", name="Pacific Coast Power", kind="utility",
                                     contact_channel="portal"))
    s.create_task(Task(id="task_pacific", estate_id="est_alvarez", institution_id="pacific_coast_power", kind="notify",
                       state="awaiting_institution", due_sim_date="2026-03-11", case_ref="PAC-1"))
    return s


def test_governor_blocks_payment_raises_decision_and_writes_receipt(tmp_path):
    store = _store(tmp_path)
    paid = []

    @tool
    def pay(case_ref: str, amount_cents: int, method: str = "estate_account") -> str:
        """Pay an amount due on a case, in cents."""
        paid.append(amount_cents)
        return json.dumps({"paid": True})

    agent = Agent(model=ScriptedModel(_TryToPay()), tools=[pay], interventions=[PostscriptGovernor(store)],
                  hooks=[ReceiptHooks(store)], callback_handler=None)
    task = store.get_task("task_pacific").model_dump()
    agent("Work this task.", invocation_state={"task": task, "sim_date": "2026-03-11"})

    assert paid == [], "the tool must not have run"
    decisions = store.list_decisions()
    assert len(decisions) == 1 and decisions[0].types == ["D1"] and decisions[0].raised_by == "governor"
    assert store.get_task("task_pacific").state == "awaiting_human"
    receipts = store.iter_receipts()
    assert len(receipts) == 1 and receipts[0].policy.decision == "forbid" and receipts[0].tool == "pay"
    assert store.verify_chain()[0]


def test_governor_permits_payment_with_live_approval_and_consumes_token(tmp_path):
    store = _store(tmp_path)
    from postscript.inbox import resolve
    from postscript.models import Decision

    store.create_decision(Decision(id="dec1", estate_id="est_alvarez", task_id="task_pacific",
                                   institution_id="pacific_coast_power", types=["D1"], question="Pay?",
                                   options=["pay", "hold"], recommendation="pay", raised_by="agent",
                                   sim_date="2026-03-11"))
    resolve(store, "dec1", "approve", "pay", "maya", "2026-03-12")
    paid = []

    @tool
    def pay(case_ref: str, amount_cents: int, method: str = "estate_account") -> str:
        """Pay an amount due on a case, in cents."""
        paid.append(amount_cents)
        return json.dumps({"paid": True, "confirmation": "PAY-1"})

    agent = Agent(model=ScriptedModel(_TryToPay()), tools=[pay], interventions=[PostscriptGovernor(store)],
                  hooks=[ReceiptHooks(store)], callback_handler=None)
    task = store.get_task("task_pacific").model_dump()
    agent("Work this task.", invocation_state={"task": task, "sim_date": "2026-03-12"})
    assert paid == [14217]
    t = store.get_task("task_pacific")
    assert t.approval is not None and t.approval.used, "the approval token is single use"
    r = [x for x in store.iter_receipts() if x.tool == "pay"][0]
    assert r.policy.decision == "permit" and r.policy.human_approval_id == "dec1"
