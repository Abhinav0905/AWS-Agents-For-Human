"""The simulated world of institutions. Deterministic under a seed; runs entirely in memory.

One Case per institution. Each institution follows a small script keyed on the sim day and on
what the agent submitted. Days advance only when the harness calls advance(days).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from .roster import INBOUND, ROSTER, SIM_START, institution

TERMINAL = {"done", "closed"}


@dataclass
class Case:
    case_ref: str
    institution_id: str
    status: str = "received"
    message: str = ""
    respond_on: int | None = None
    day_submitted: int = 0
    followups: int = 0
    denials: int = 0
    certified: bool = False
    requested_items: list[str] = field(default_factory=list)
    amount_due: float | None = None
    closing_offer: str | None = None
    options: list[str] = field(default_factory=list)
    submitted: list[dict] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def public(self) -> dict:
        return {
            "case_ref": self.case_ref, "institution_id": self.institution_id, "status": self.status,
            "message": self.message, "requested_items": self.requested_items, "amount_due": self.amount_due,
            "closing_offer": self.closing_offer, "options": self.options,
            "next_expected_sim_day": self.respond_on, "followups": self.followups,
        }


class World:
    def __init__(self, seed: int = 7, start: str = SIM_START):
        self.rng = random.Random(seed)
        self.seed = seed
        self.start = date.fromisoformat(start)
        self.day = 0
        self.cases: dict[str, Case] = {}
        self.inbox: list[dict] = []
        self.delivered_inbound: set[int] = set()
        self.certificates_received: int = 0
        self.money_received: float = 0.0
        self.events: list[dict] = []

    # ---- helpers ----------------------------------------------------------------
    def sim_date(self, day: int | None = None) -> str:
        return (self.start + timedelta(days=self.day if day is None else day)).isoformat()

    def _case_for(self, inst_id: str) -> Case | None:
        for c in self.cases.values():
            if c.institution_id == inst_id and c.status not in TERMINAL:
                return c
        return None

    def _post(self, case: Case, status: str, message: str, **kw) -> None:
        case.status = status
        case.message = message
        case.requested_items = kw.get("requested_items", [])
        case.amount_due = kw.get("amount_due")
        case.closing_offer = kw.get("closing_offer")
        case.options = kw.get("options", [])
        case.respond_on = kw.get("respond_on")
        case.log.append(f"day {self.day}: {status}: {message}")
        inst = institution(case.institution_id)
        self.inbox.append({"day": self.day, "sim_date": self.sim_date(), "from": inst["name"], "kind": "institution",
                           "institution_id": inst["id"], "case_ref": case.case_ref, "status": status,
                           "subject": f"{inst['name']} re: case {case.case_ref}", "body": message})
        self.events.append({"day": self.day, "institution_id": inst["id"], "status": status})

    # ---- agent-facing tools ------------------------------------------------------
    def list_institutions(self) -> list[dict]:
        return [{"id": r["id"], "name": r["name"], "kind": r["kind"], "contact_channel": r["channel"]} for r in ROSTER]

    def get_requirements(self, institution_id: str) -> dict:
        r = institution(institution_id)
        return {
            "institution_id": r["id"], "name": r["name"], "channel": r["channel"],
            "documents": r["requirements"], "signature_kind": r["signature_kind"],
            "in_person": r["channel"] == "in_person", "expected_response_days": r["response_days"], "fee": 0,
            "note": "Public bereavement requirements. Originals are consumed; copies are not.",
        }

    def submit_notification(self, institution_id: str, account_last4: str, letter_text: str, documents: list[dict],
                            includes_original: bool, signature_kind: str) -> dict:
        r = institution(institution_id)
        existing = self._case_for(institution_id)
        if existing:
            return {"accepted": False, "error": f"A case is already open: {existing.case_ref}. Use check_status.",
                    **existing.public()}
        if any(bool(d.get("is_original")) for d in documents) != bool(includes_original):
            return {"accepted": False, "error": "Packet inconsistent: includes_original must match the documents."}
        have = {d["doc_type"]: d for d in documents}
        for req in r["requirements"]:
            d = have.get(req["doc_type"])
            if d is None:
                return {"accepted": False, "error": f"Missing required document: {req['doc_type']}"}
            if req["original_required"] and not d.get("is_original"):
                return {"accepted": False,
                        "error": f"{r['name']} requires an original certified {req['doc_type']}; copies are not accepted."}
        if r["signature_kind"] != "none" and signature_kind != r["signature_kind"]:
            return {"accepted": False, "error": f"{r['name']} requires signature kind '{r['signature_kind']}'."}
        ref = f"{r['id'][:3].upper()}-{self.rng.randint(1000, 9999)}"
        case = Case(case_ref=ref, institution_id=institution_id, day_submitted=self.day, submitted=documents)
        self.cases[ref] = case
        originals = sum(1 for d in documents if d.get("is_original"))
        self.certificates_received += originals
        if r["script"] == "telecom_ignore":
            case.status, case.message, case.respond_on = "no_response", "Notice received by the mailbox; no reply yet.", None
        else:
            case.status, case.message = "received", f"Notice received by {r['name']}."
            case.respond_on = self.day + r["response_days"]
        case.log.append(f"day {self.day}: submitted ({originals} original)")
        return {"accepted": True, "case_ref": ref, "status": case.status, "message": case.message,
                "next_expected_sim_day": case.respond_on, "consumed_originals": originals}

    def check_status(self, case_ref: str) -> dict:
        c = self.cases.get(case_ref)
        if not c:
            return {"error": f"unknown case {case_ref}"}
        return c.public()

    def send_follow_up(self, case_ref: str, text: str, certified: bool) -> dict:
        c = self.cases.get(case_ref)
        if not c:
            return {"error": f"unknown case {case_ref}"}
        r = institution(c.institution_id)
        c.followups += 1
        c.certified = c.certified or certified
        c.log.append(f"day {self.day}: follow-up #{c.followups} certified={certified}")
        if r["script"] == "telecom_ignore" and c.status == "no_response":
            c.status, c.message, c.respond_on = "pending", "Follow-up received; a representative will respond.", self.day + 3
            return {"acknowledged": True, "escalated": False, **c.public()}
        if r["script"] == "gym_stonewall" and c.status == "denied_no_record":
            if certified:
                c.status, c.message, c.respond_on = "pending", "Certified letter received.", self.day + 2
                return {"acknowledged": True, "escalated": True, **c.public()}
            c.status, c.message, c.respond_on = "pending", "We are looking into it.", self.day + 3
            return {"acknowledged": True, "escalated": False, **c.public()}
        if c.status in TERMINAL:
            return {"acknowledged": True, "escalated": False, **c.public()}
        c.status, c.message, c.respond_on = "pending", "Follow-up logged.", c.respond_on or self.day + 3
        return {"acknowledged": True, "escalated": certified, **c.public()}

    def submit_document(self, case_ref: str, doc_type: str, includes_original: bool, signature_kind: str) -> dict:
        c = self.cases.get(case_ref)
        if not c:
            return {"error": f"unknown case {case_ref}"}
        r = institution(c.institution_id)
        c.submitted.append({"doc_type": doc_type, "is_original": includes_original, "signature_kind": signature_kind})
        s = r["script"]
        if s == "insurer_claim" and c.status == "requires_original":
            if doc_type != "death_certificate" or not includes_original:
                return {"accepted": False, "error": "The claim needs an original certified death certificate."}
            c.status, c.message, c.respond_on = "processing", "Claim documents received; under review.", self.day + 7
        elif s == "pension_notary" and c.status == "notarized_form_required":
            if signature_kind != "notarized":
                return {"accepted": False, "error": "The survivor form must be notarized."}
            c.status, c.message, c.respond_on = "processing", "Notarized survivor form received.", self.day + 10
        elif s == "telecom_ignore" and c.status == "form_required":
            c.status, c.message, c.respond_on = "processing", "Authorized representative form received.", self.day + 3
        else:
            c.status, c.message, c.respond_on = "processing", f"Document {doc_type} received.", self.day + r["response_days"]
        if includes_original:
            self.certificates_received += 1
        c.log.append(f"day {self.day}: document {doc_type} original={includes_original} signature={signature_kind}")
        return {"accepted": True, "consumed_originals": 1 if includes_original else 0, **c.public()}

    def pay(self, case_ref: str, amount_cents: int, method: str = "estate_account") -> dict:
        c = self.cases.get(case_ref)
        if not c:
            return {"error": f"unknown case {case_ref}"}
        amount = round(int(amount_cents) / 100.0, 2)
        if c.status != "final_bill":
            return {"paid": False, "error": f"Nothing is due on case {case_ref} (status {c.status})."}
        if abs((c.amount_due or 0) - amount) > 0.005:
            return {"paid": False, "error": f"Amount mismatch: due {c.amount_due}, offered {amount}."}
        self.money_received += amount
        c.log.append(f"day {self.day}: paid {amount}")
        self._post(c, "done", f"Payment of ${amount:.2f} received. Account closed with a zero balance.")
        return {"paid": True, "confirmation": f"PAY-{self.rng.randint(100000, 999999)}", **c.public()}

    def close_account(self, case_ref: str) -> dict:
        c = self.cases.get(case_ref)
        if not c:
            return {"error": f"unknown case {case_ref}"}
        if c.status != "closing_offer":
            return {"closed": False, "error": f"Case {case_ref} is not ready to close (status {c.status})."}
        c.log.append(f"day {self.day}: closed")
        self._post(c, "closed", "Accounts closed. A cashier's check payable to the Estate of Robert Alvarez was mailed.")
        return {"closed": True, "final_statement_ref": f"FS-{c.case_ref}", **c.public()}

    def elect_option(self, case_ref: str, option: str) -> dict:
        c = self.cases.get(case_ref)
        if not c:
            return {"error": f"unknown case {case_ref}"}
        if c.status != "election_required":
            return {"accepted": False, "error": f"No election is pending on {case_ref} (status {c.status})."}
        if option not in c.options:
            return {"accepted": False, "error": f"Option must be one of {c.options}."}
        c.log.append(f"day {self.day}: elected {option}")
        self._post(c, "done", f"Payout election recorded: {option}. The claim will be paid within 10 business days.")
        return {"accepted": True, "election": option, **c.public()}

    def get_inbox(self) -> list[dict]:
        out, self.inbox = self.inbox, []
        return out

    # ---- harness tools -------------------------------------------------------------
    def advance(self, days: int = 1) -> dict:
        fired = []
        for _ in range(days):
            self.day += 1
            for c in list(self.cases.values()):
                if c.respond_on is not None and c.respond_on <= self.day and c.status not in TERMINAL:
                    self._respond(c)
                    fired.append({"institution_id": c.institution_id, "status": c.status})
            for i, msg in enumerate(INBOUND):
                if msg["day"] == self.day and i not in self.delivered_inbound:
                    self.delivered_inbound.add(i)
                    self.inbox.append({**msg, "sim_date": self.sim_date()})
                    fired.append({"inbound": msg["subject"]})
        return {"sim_day": self.day, "sim_date": self.sim_date(), "fired": fired}

    def _respond(self, c: Case) -> None:
        r = institution(c.institution_id)
        s = r["script"]
        st = c.status
        if s == "bank_close" and st == "received":
            self._post(c, "closing_offer", "Documents verified. Confirm closure to release funds by cashier's check "
                       "payable to the estate. This cannot be undone.",
                       closing_offer="Close both accounts and issue cashier's check to the Estate")
        elif s == "utility_bill" and st == "received":
            self._post(c, "final_bill", f"Final bill issued: ${r['final_bill']:.2f}. Service ended.",
                       amount_due=r["final_bill"])
        elif s == "telecom_ignore" and st == "pending":
            self._post(c, "form_required", "Please submit our Authorized Representative form to close the account.",
                       requested_items=[r["form_type"]])
        elif s == "telecom_ignore" and st == "processing":
            self._post(c, "done", "Account closed. Final balance $0.00.")
        elif s == "insurer_claim" and st == "received":
            self._post(c, "requires_original", "Claim opened. To process it we need an original certified death "
                       "certificate and the completed claim form.",
                       requested_items=["death_certificate:original", "claim_form"])
        elif s == "insurer_claim" and st == "processing":
            self._post(c, "election_required", "Claim approved for $250,000. Please elect a payout option.",
                       options=list(r["election_options"]))
        elif s == "pension_notary" and st == "received":
            self._post(c, "notarized_form_required", "Survivor benefit form enclosed. It must be notarized.",
                       requested_items=[f"{r['form_type']}:notarized"])
        elif s == "pension_notary" and st == "processing":
            self._post(c, "done", "Survivor benefit set up. First payment next month.")
        elif s == "subscription_cancel" and st == "received":
            self._post(c, "done", "Subscription cancelled. Pro-rated refund of $10.20 issued.")
        elif s == "credit_bureau_alert" and st == "received":
            self._post(c, "done", "Deceased alert placed on the credit file.")
        elif s == "dmv_title" and st == "received":
            self._post(c, "done", "Title transfer complete. New title mailed to the executor.")
        elif s == "brokerage_medallion" and st == "received":
            self._post(c, "done", "Transfer complete. Assets moved to the estate account.")
        elif s == "gym_stonewall":
            if st == "received" or (st == "pending" and not c.certified):
                c.denials += 1
                self._post(c, "denied_no_record", f"We have no record of a cancellation request (notice {c.denials}). "
                           "Dues continue to accrue.")
            elif st == "pending" and c.certified:
                self._post(c, "done", "Certified cancellation received. Membership cancelled; no further dues.")
        elif st == "processing":
            self._post(c, "done", "Request completed.")
        else:
            c.respond_on = None

    def snapshot(self) -> dict:
        return {"sim_day": self.day, "sim_date": self.sim_date(), "certificates_received": self.certificates_received,
                "money_received": round(self.money_received, 2),
                "cases": {k: v.public() for k, v in self.cases.items()}}
