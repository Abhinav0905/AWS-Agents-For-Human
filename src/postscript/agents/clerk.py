"""The scripted clerk: the deterministic decision rules behind ScriptedModel.

It reads the same context a real model would (the task prompt and prior tool results) and picks
the next tool call. It deliberately behaves like a careful but imperfect clerk: it asks before
consuming originals or booking signatures, and it tries to pay bills and close accounts directly,
which lets the governor demonstrate the Cedar gate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from ..models import DECISION_LABELS

KIND_KEYWORDS = [
    ("credit_bureau", ["credit bureau", "credit file", "tradelines"]),
    ("bank", ["bank", "checking", "savings"]),
    ("utility", ["power", "energy", "electric", "gas service", "utility"]),
    ("telecom", ["telecom", "mobile", "internet", "wireless"]),
    ("insurer", ["life insurance", "insurance", "policy", "beneficiary"]),
    ("pension", ["pension", "retirement", "survivor"]),
    ("subscription", ["stream", "subscription", "premium plan"]),
    ("dmv", ["motor vehicles", "dmv", "registration", "title transfer"]),
    ("brokerage", ["brokerage", "portfolio", "medallion"]),
    ("gym", ["fitness", "gym", "membership", "dues"]),
]


@dataclass
class Call:
    id: str
    name: str
    args: dict
    result: Any = None
    status: str = ""


@dataclass
class Convo:
    ctx: dict = field(default_factory=dict)
    calls: list[Call] = field(default_factory=list)


def _text_of(block: dict) -> str:
    return block.get("text", "") if isinstance(block, dict) else ""


def _parse_result(tr: dict) -> Any:
    """MCP list results arrive as one text block per item; dict results as a single block."""
    items: list[Any] = []
    for c in tr.get("content", []) or []:
        if "json" in c:
            items.append(c["json"])
        elif "text" in c:
            try:
                items.append(json.loads(c["text"]))
            except (json.JSONDecodeError, TypeError):
                items.append(c["text"])
    if not items:
        return None
    return items[0] if len(items) == 1 else items


def parse_conversation(messages: list[dict]) -> Convo:
    convo = Convo()
    by_id: dict[str, Call] = {}
    for m in messages:
        for block in m.get("content", []) or []:
            if m["role"] == "user" and "text" in block and "TASK_CONTEXT:" in block["text"] and not convo.ctx:
                raw = block["text"].split("TASK_CONTEXT:", 1)[1].strip()
                try:
                    convo.ctx = json.loads(raw)
                except json.JSONDecodeError:
                    convo.ctx = {}
            if m["role"] == "assistant" and "toolUse" in block:
                tu = block["toolUse"]
                call = Call(id=tu["toolUseId"], name=tu["name"], args=tu.get("input") or {})
                convo.calls.append(call)
                by_id[call.id] = call
            if m["role"] == "user" and "toolResult" in block:
                tr = block["toolResult"]
                call = by_id.get(tr.get("toolUseId"))
                if call:
                    call.result = _parse_result(tr)
                    call.status = tr.get("status", "")
    return convo


class ClerkBrain:
    def __init__(self, role: str = "runner"):
        self.role = role

    # ------------------------------------------------------------------ intake
    def structured(self, output_model, prompt, system_prompt: str | None):
        text = ""
        has_image = False
        for m in prompt if isinstance(prompt, list) else [prompt]:
            if isinstance(m, dict):
                for block in m.get("content", []) or []:
                    if isinstance(block, dict) and "text" in block:
                        text += block["text"] + "\n"
                    if isinstance(block, dict) and "image" in block:
                        has_image = True
            elif isinstance(m, str):
                text += m
        return output_model.model_validate(extract_intake(text, has_image))

    # ------------------------------------------------------------------ runner
    def next(self, messages: list[dict], tool_specs: list[dict], system_prompt: str | None) -> tuple:
        # Structured output at invocation time arrives as a tool named after the Pydantic model.
        structured = next((t for t in tool_specs if t.get("name") == "IntakeExtraction"), None)
        if structured is not None:
            text, has_image = "", False
            users = [m for m in messages if m.get("role") == "user"]
            for m in users[-1:]:  # the current document only
                for block in m.get("content", []) or []:
                    if isinstance(block, dict) and "text" in block:
                        text += block["text"] + "\n"
                    if isinstance(block, dict) and "image" in block:
                        has_image = True
            return ("tool", "IntakeExtraction", extract_intake(text, has_image))
        convo = parse_conversation(messages)
        if not convo.ctx:
            return ("text", "I have no task context to work on.")
        try:
            return clerk_step(convo.ctx, convo.calls)
        except Exception as exc:  # the clerk never crashes the agent loop
            return ("text", f"Clerk stopped: {exc}")


# ---------------------------------------------------------------------------------- intake rules

def extract_intake(text: str, has_image: bool) -> dict:
    doc = text.split("DOCUMENT:", 1)[1] if "DOCUMENT:" in text else text
    lines = [ln.strip() for ln in doc.strip().splitlines() if ln.strip()]
    if lines and lines[0].startswith("mail_") or (lines and lines[0].endswith((".pdf", ".png", ".eml"))):
        lines = lines[1:]  # the file name header
    lines = [ln for ln in lines if not ln.startswith("Extract the institution")]
    if has_image and len(lines) < 2:
        return {"is_relevant": False, "institution_name": "", "kind": "other", "account_label": "",
                "masked_last4": None, "contact_channel": "mail", "document_type": "scan", "confidence": 0.0,
                "notes": "Image scan: needs a vision-capable model (run with POSTSCRIPT_MODEL=bedrock)."}
    if not lines:
        return {"is_relevant": False, "institution_name": "", "kind": "other", "account_label": "",
                "masked_last4": None, "contact_channel": "mail", "document_type": "empty", "confidence": 0.0, "notes": ""}
    # e-mails: skip headers
    body_lines = lines
    if lines[0].lower().startswith("from:"):
        idx = next((i for i, ln in enumerate(lines) if ln.lower().startswith("date:")), 3)
        body_lines = lines[idx + 1:] or lines
    institution = body_lines[0]
    title = body_lines[1] if len(body_lines) > 1 else ""
    blob = " ".join(body_lines).lower()
    m = re.search(r"account ending in\s*(\d{4})", blob)
    last4 = m.group(1) if m else None
    relevant = "account holder" in blob and last4 is not None
    kind = "other"
    for k, words in KIND_KEYWORDS:
        if any(w in institution.lower() or w in title.lower() for w in words):
            kind = k
            break
    if kind == "other":
        for k, words in KIND_KEYWORDS:
            if any(w in blob for w in words):
                kind = k
                break
    channel = "mail"
    if lines[0].lower().startswith("from:"):
        channel = "email"
    elif "in-person" in blob or "in person" in blob:
        channel = "in_person"
    elif re.search(r"at [a-z0-9.]+\.example/|upload", blob):
        channel = "portal"
    return {
        "is_relevant": relevant,
        "institution_name": institution if relevant else "",
        "kind": kind if relevant else "other",
        "account_label": title,
        "masked_last4": last4,
        "contact_channel": channel,
        "document_type": title.lower() or "document",
        "confidence": 0.92 if relevant else 0.2,
        "notes": "" if relevant else "No account holder or account reference found; treated as not relevant.",
    }


# ---------------------------------------------------------------------------------- runner rules

def _plus(sim_date: str, days: int) -> str:
    return (date.fromisoformat(sim_date) + timedelta(days=max(1, days))).isoformat()


def _find(calls: list[Call], name: str) -> Call | None:
    for c in reversed(calls):
        if c.name == name:
            return c
    return None


def clerk_step(ctx: dict, calls: list[Call]) -> tuple:
    task = ctx["task"]
    inst = ctx["institution"]
    est = ctx["estate"]
    today = ctx["sim_date"]
    tid = task["id"]
    approval = task.get("approval") or {}
    approved = bool(approval) and not approval.get("used", False)
    approved_types = set(approval.get("types", [])) if approved else set()
    flags = task.get("flags", {})
    last = calls[-1] if calls else None

    # terminal conditions ------------------------------------------------------------------
    if len(calls) >= 12:
        return ("text", "Stopping: tool budget for this task reached.")
    if last and isinstance(last.result, dict) and last.result.get("blocked"):
        return ("text", f"Blocked by the interruption policy; {last.result.get('reason', '')} Stopping this task.")
    if last and isinstance(last.result, str) and "blocked" in last.result:
        return ("text", "Blocked by the interruption policy. Stopping this task.")
    if last and last.name == "decisions_request":
        return ("text", "Decision sent to the executor. Stopping this task until she answers.")
    if last and last.name == "ledger_update_task":
        return ("text", "Task updated; done for today.")

    def update(state: str, note: str, **kw) -> tuple:
        args = {"task_id": tid, "state": state, "note": note}
        args.update({k: v for k, v in kw.items() if v not in (None, "")})
        return ("tool", "ledger_update_task", args)

    def ask(types: list[str], question: str, options: list[str], rec: str) -> tuple:
        return ("tool", "decisions_request", {"task_id": tid, "types": types, "question": question,
                                              "options": options, "recommendation": rec})

    # D5: an heir objected ------------------------------------------------------------------
    if flags.get("heir_conflict"):
        if "D5" in approved_types:
            if approval.get("chosen_option") == "pause":
                return update("blocked", "Paused at the heirs' request until they agree.")
        else:
            return ask(["D5"], f"Daniel objects to the {inst['name']} step for {task['kind']}. "
                               "Pause it until you two agree, or continue as the will directs?",
                       ["pause", "continue"], "pause")

    # fresh task: find the institution at the gateway, then learn its requirements ---------------
    if task["state"] in ("queued", "drafted") and not task.get("case_ref"):
        listing = _find(calls, "list_institutions")
        if listing is None:
            return ("tool", "list_institutions", {})
        gateway_id = match_institution(listing.result, inst["name"], inst["kind"])
        if gateway_id is None:
            return update("blocked", f"{inst['name']} is not reachable through the gateway yet.",
                          due_sim_date=_plus(today, 7))
        inst = {**inst, "id": gateway_id}
        req_call = _find(calls, "get_requirements")
        if req_call is None:
            return ("tool", "get_requirements", {"institution_id": gateway_id})
        req = req_call.result or {}
        docs = req.get("documents", [])
        originals = [d for d in docs if d.get("original_required")]
        signature = req.get("signature_kind", "none") or "none"
        needed = (["D2"] if originals else []) + (["D3"] if signature != "none" else [])
        if needed and not needed_covered(needed, approved_types):
            left = est.get("certified_copies_on_hand")
            parts = [DECISION_LABELS[t] for t in needed]
            extra = f" You have {left} certified originals left." if "D2" in needed else ""
            how = f" ({signature} signature)" if signature != "none" else ""
            return ask(needed, f"{inst['name']} will only accept the notice with {' and '.join(parts)}{how}."
                               f" Go ahead?{extra}", ["proceed", "hold"], "proceed")
        letter_call = _find(calls, "render_letter")
        if letter_call is None:
            return ("tool", "render_letter", {"kind": inst["kind"], "institution_name": inst["name"],
                                              "account_last4": task.get("account_last4", "")})
        submit = _find(calls, "submit_notification")
        if submit is None:
            documents = []
            for d in docs:
                documents.append({"doc_type": d["doc_type"], "is_original": bool(d.get("original_required")),
                                  "doc_ref": f"{d['doc_type']}_{'orig' if d.get('original_required') else 'copy'}"})
            if not documents:
                documents = [{"doc_type": "death_certificate", "is_original": False, "doc_ref": "death_certificate_copy"}]
            return ("tool", "submit_notification", {
                "institution_id": inst["id"], "account_last4": task.get("account_last4", ""),
                "letter_text": str(letter_call.result)[:2000], "documents": documents,
                "includes_original": bool(originals), "signature_kind": signature,
            })
        res = submit.result or {}
        if isinstance(res, dict) and res.get("accepted"):
            nxt = res.get("next_expected_sim_day")
            due = _plus(ctx["sim_start"], int(nxt)) if nxt is not None else _plus(today, 7)
            return update("awaiting_institution", f"Notice sent; case {res.get('case_ref')}. {res.get('message', '')}",
                          case_ref=res.get("case_ref"), due_sim_date=due)
        return update("blocked", f"Submission rejected: {res.get('error') if isinstance(res, dict) else res}",
                      due_sim_date=_plus(today, 1))

    # open case: check status and act ----------------------------------------------------------
    status_call = _find(calls, "check_status")
    if status_call is None:
        return ("tool", "check_status", {"case_ref": task["case_ref"]})
    st = status_call.result or {}
    status = st.get("status", "")
    nxt = st.get("next_expected_sim_day")
    due_next = _plus(ctx["sim_start"], int(nxt)) if nxt is not None else _plus(today, 3)
    action_calls = [c for c in calls if c.name in ("send_follow_up", "submit_document", "pay", "close_account",
                                                   "elect_option")]
    acted = action_calls[-1] if action_calls else None

    if acted is not None:
        res = acted.result or {}
        ok = isinstance(res, dict) and not res.get("error") and res.get("accepted", True) is not False \
            and res.get("paid", True) is not False and res.get("closed", True) is not False
        if not ok:
            return update("blocked", f"{acted.name} failed: {res.get('error') if isinstance(res, dict) else res}",
                          due_sim_date=_plus(today, 2))
        if acted.name in ("pay", "close_account", "elect_option"):
            return update("done", f"{acted.name} completed. {res.get('message', '')}")
        n2 = res.get("next_expected_sim_day") if isinstance(res, dict) else None
        due = _plus(ctx["sim_start"], int(n2)) if n2 is not None else _plus(today, 3)
        attempts = task.get("attempts", 0) + (1 if acted.name == "send_follow_up" else 0)
        return update("awaiting_institution", f"{acted.name} sent. {res.get('message', '')}", due_sim_date=due,
                      attempts=attempts)

    if status in ("done", "closed"):
        return update("done", f"{inst['name']}: {st.get('message', 'complete')}")
    if status in ("received", "pending", "processing"):
        return update("awaiting_institution", f"Waiting on {inst['name']}: {st.get('message', '')}", due_sim_date=due_next)
    if status == "no_response":
        return ("tool", "send_follow_up", {"case_ref": task["case_ref"], "certified": task.get("attempts", 0) >= 2,
                                           "text": "Following up on the death notification sent for this account."})
    if status == "denied_no_record":
        certified = task.get("attempts", 0) >= 1
        return ("tool", "send_follow_up", {"case_ref": task["case_ref"], "certified": certified,
                                           "text": "Second notice: the cancellation letter was sent on the date shown. "
                                                   "Please confirm cancellation and stop billing."})
    if status == "form_required":
        item = (st.get("requested_items") or ["form"])[0].split(":")[0]
        return ("tool", "submit_document", {"case_ref": task["case_ref"], "doc_type": item,
                                            "includes_original": False, "signature_kind": "none"})
    if status == "final_bill":
        cents = int(round(float(st.get("amount_due") or 0) * 100))
        # the clerk tries to pay; the governor turns this into a D1 decision unless approved
        return ("tool", "pay", {"case_ref": task["case_ref"], "amount_cents": cents, "method": "estate_account"})
    if status == "closing_offer":
        return ("tool", "close_account", {"case_ref": task["case_ref"]})
    if status == "requires_original":
        if "D2" in approved_types:
            return ("tool", "submit_document", {"case_ref": task["case_ref"], "doc_type": "death_certificate",
                                                "includes_original": True, "signature_kind": "none"})
        return ask(["D2"], f"{inst['name']} needs an original certified death certificate to process the claim. "
                           f"Mail one? You have {est.get('certified_copies_on_hand')} left.", ["proceed", "hold"], "proceed")
    if status == "election_required":
        options = st.get("options") or ["proceed"]
        if "D4" in approved_types and approval.get("chosen_option") in options:
            return ("tool", "elect_option", {"case_ref": task["case_ref"], "option": approval["chosen_option"]})
        return ask(["D4"], f"{inst['name']} approved the claim and needs a payout election. {st.get('message', '')} "
                           "A lump sum keeps the estate simple; an annuity spreads it out.", options, options[0])
    if status == "notarized_form_required":
        item = (st.get("requested_items") or ["survivor_form"])[0].split(":")[0]
        if "D3" in approved_types:
            return ("tool", "submit_document", {"case_ref": task["case_ref"], "doc_type": item,
                                                "includes_original": False, "signature_kind": "notarized"})
        return ask(["D3"], f"{inst['name']} needs the {item.replace('_', ' ')} notarized and signed by you. "
                           "Book a notary this week?", ["proceed", "hold"], "proceed")
    if status == "signature_required":
        if "D3" in approved_types:
            return ("tool", "submit_document", {"case_ref": task["case_ref"], "doc_type": "title",
                                                "includes_original": False, "signature_kind": "wet"})
        return ask(["D3"], f"{inst['name']} needs your signature in person to finish this. Book the visit?",
                   ["proceed", "hold"], "proceed")
    return update("awaiting_institution", f"Status {status or 'unknown'}: {st.get('message', '')}", due_sim_date=due_next)


def match_institution(listing: Any, name: str, kind: str) -> str | None:
    """Pick the gateway institution whose name best matches the ledger name (then kind as a tiebreaker)."""
    if not isinstance(listing, list):
        return None
    norm = re.sub(r"[^a-z0-9 ]", "", name.lower())
    tokens = [t for t in norm.split() if len(t) > 2]
    best, best_score = None, 0
    for item in listing:
        iname = re.sub(r"[^a-z0-9 ]", "", str(item.get("name", "")).lower())
        score = sum(1 for t in tokens if t in iname)
        if item.get("kind") == kind:
            score += 1
        if score > best_score:
            best, best_score = item.get("id"), score
    return best if best_score >= 2 else None


def needed_covered(needed: list[str], approved_types: set[str]) -> bool:
    return bool(approved_types) and set(needed) <= approved_types
