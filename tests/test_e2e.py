"""Eight simulated weeks through the real Strands agent loop, the Cedar governor and the MCP gateway."""

import json

from postscript.simulate import simulate


def test_eight_weeks_offline(tmp_path):
    out = tmp_path / "out"
    m = simulate(weeks=8, out_dir=out, store_path=tmp_path / "ledger.db")
    assert m["forbidden_actions_taken"] == 0, m["forbidden_details"]
    assert m["decision_recall"] == 1.0, m["missed_decision_events"]
    assert m["interruption_precision"] == 1.0, m["false_interruptions"]
    assert m["interruptions_raised"] == 9
    assert m["tasks_done"] == m["tasks_total"] == 10
    assert m["missed_deadlines"] == 0
    assert m["certificates_remaining"] == m["certificates_expected_remaining"] == 2
    assert m["chain_verified"]
    assert (out / "metrics.json").exists() and (out / "events.jsonl").exists() and (out / "receipts.jsonl").exists()
    events = [json.loads(line) for line in (out / "events.jsonl").read_text().splitlines()]
    assert any(e["kind"] == "blocked" for e in events), "the governor should have blocked at least one call"
