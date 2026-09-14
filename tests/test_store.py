import pytest

from postscript.models import Estate, Institution, PolicyRecord, Task
from postscript.redaction import redact
from postscript.store import SQLiteLedgerStore


def make_store(tmp_path):
    s = SQLiteLedgerStore(tmp_path / "ledger.db", reset=True)
    s.save_estate(Estate(id="est_alvarez", decedent_name="Bob", date_of_death="2026-03-02", executor_name="Maya",
                         executor_id="maya", heirs=["Maya", "Daniel"], certified_copies_on_hand=5))
    s.set_clock("2026-03-09")
    s.upsert_institution(Institution(id="bank", name="Bank", kind="bank", contact_channel="mail"))
    s.create_task(Task(id="t1", estate_id="est_alvarez", institution_id="bank", kind="notify", due_sim_date="2026-03-09"))
    return s


def test_state_machine_rejects_illegal_transition(tmp_path):
    s = make_store(tmp_path)
    s.update_task("t1", state="awaiting_institution", note="sent")
    with pytest.raises(ValueError):
        s.update_task("t1", state="drafted", note="backwards")
    s.update_task("t1", state="done", note="closed")
    with pytest.raises(ValueError):
        s.update_task("t1", state="queued", note="reopen a done task")


def test_receipts_are_chained_and_tamper_evident(tmp_path):
    s = make_store(tmp_path)
    for i in range(3):
        s.append_receipt(s.make_receipt(tool="check_status", args={"case_ref": f"C{i}"}, result_summary="ok",
                                        task_id="t1", actor="runner", policy=PolicyRecord(decision="permit")))
    ok, msg = s.verify_chain()
    assert ok and "3 receipts" in msg
    # tamper with the middle receipt directly in SQL: the chain must break
    s.db.execute("UPDATE receipts SET json = replace(json, '\"result_summary\":\"ok\"', '\"result_summary\":\"changed\"') "
                 "WHERE seq = 2")
    s.db.commit()
    ok, msg = s.verify_chain()
    assert not ok and "#2" in msg


def test_redaction_masks_numbers_and_drops_secrets():
    out = redact({"account": "Account 123456789012", "ssn": "123-45-6789", "note": "call 555-01-2345 later",
                  "approval_token": "abc"})
    assert out["ssn"] == "[dropped]" and out["approval_token"] == "[dropped]"
    assert out["account"].endswith("9012") and "123456789012" not in out["account"]
    assert "[ssn]" in out["note"]


def test_decision_resolution_mints_single_use_approval(tmp_path):
    from postscript.models import Decision

    s = make_store(tmp_path)
    d = Decision(id="dec1", estate_id="est_alvarez", task_id="t1", institution_id="bank", types=["D2"], question="q",
                 options=["proceed", "hold"], recommendation="proceed", raised_by="agent", sim_date="2026-03-09")
    s.create_decision(d)
    assert s.get_task("t1").state == "awaiting_human"
    s.resolve_decision("dec1", "approved", "proceed", "maya", "2026-03-10")
    t = s.get_task("t1")
    assert t.state == "queued" and t.approval and not t.approval.used
    s.consume_approval("t1")
    assert s.get_task("t1").approval.used
