from postscript.sim.roster import ROSTER
from postscript.sim.world import TERMINAL, World


def perfect_executor(world: World, days: int = 60) -> None:
    """Drive every institution to a final state the way a tireless human would."""
    for r in ROSTER:
        docs = [{"doc_type": d["doc_type"], "is_original": d["original_required"], "doc_ref": d["doc_type"]}
                for d in r["requirements"]]
        res = world.submit_notification(r["id"], r["accounts"][0]["last4"], "letter", docs,
                                        any(d["is_original"] for d in docs), r["signature_kind"])
        assert res["accepted"], res
    for _ in range(days):
        world.advance(1)
        for c in list(world.cases.values()):
            if c.status in TERMINAL:
                continue
            if c.status in ("no_response", "denied_no_record"):
                world.send_follow_up(c.case_ref, "follow up", certified=c.status == "denied_no_record" and c.denials >= 2)
            elif c.status == "form_required":
                world.submit_document(c.case_ref, c.requested_items[0], False, "none")
            elif c.status == "requires_original":
                world.submit_document(c.case_ref, "death_certificate", True, "none")
            elif c.status == "notarized_form_required":
                world.submit_document(c.case_ref, "survivor_form", False, "notarized")
            elif c.status == "final_bill":
                world.pay(c.case_ref, int(round(c.amount_due * 100)))
            elif c.status == "closing_offer":
                world.close_account(c.case_ref)
            elif c.status == "election_required":
                world.elect_option(c.case_ref, c.options[0])


def test_every_institution_reaches_a_final_state():
    w = World(seed=7)
    perfect_executor(w)
    assert len(w.cases) == len(ROSTER)
    assert all(c.status in TERMINAL for c in w.cases.values()), {c.institution_id: c.status for c in w.cases.values()}
    assert w.certificates_received == 3  # Harborline, Sequoia, Summit
    assert abs(w.money_received - 142.17) < 0.01


def test_originals_are_enforced_and_packets_validated():
    w = World(seed=7)
    copy = [{"doc_type": "death_certificate", "is_original": False, "doc_ref": "dc"},
            {"doc_type": "letters_testamentary", "is_original": False, "doc_ref": "lt"}]
    assert not w.submit_notification("harborline", "4417", "l", copy, False, "none")["accepted"]
    inconsistent = w.submit_notification("harborline", "4417", "l", copy, True, "none")
    assert "inconsistent" in inconsistent["error"].lower()


def test_world_is_deterministic():
    a, b = World(seed=7), World(seed=7)
    for w in (a, b):
        w.submit_notification("redwood_fitness", "1177", "l", [{"doc_type": "death_certificate", "is_original": False,
                                                              "doc_ref": "dc"}], False, "none")
    assert list(a.cases) == list(b.cases)
