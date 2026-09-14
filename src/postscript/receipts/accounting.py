"""The Executor's Accounting: the receipt chain rendered as a document a probate clerk could read."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import DECISION_LABELS
from ..store import SQLiteLedgerStore

INK = colors.HexColor("#1f2a37")
RULE = colors.HexColor("#c9cfd6")
SOFT = colors.HexColor("#f2f4f6")


def _styles():
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor("#4b5563"))
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontName="Times-Bold", fontSize=24, leading=30, alignment=TA_LEFT,
                        textColor=INK, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Times-Bold", fontSize=15, leading=19, textColor=INK,
                        spaceBefore=14, spaceAfter=6)
    mono = ParagraphStyle("mono", parent=body, fontName="Courier", fontSize=7.5, leading=9.5)
    return body, small, h1, h2, mono


def _table(rows, widths, header=True, mono_cols=()):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if header:
        style += [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK)]
    for c in mono_cols:
        style.append(("FONTNAME", (c, 1), (c, -1), "Courier"))
    t.setStyle(TableStyle(style))
    return t


def build_accounting(store: SQLiteLedgerStore, out_path: Path) -> Path:
    body, small, h1, h2, mono = _styles()

    def P(text, st=body):
        """Escape a value and wrap it as a flowable paragraph."""
        return Paragraph(str(text).replace("&", "&amp;").replace("<", "&lt;"), st)

    est = store.get_estate()
    receipts = store.iter_receipts()
    decisions = store.list_decisions()
    tasks = store.list_tasks()
    insts = {i.id: i for i in store.list_institutions()}
    ok, chain_msg = store.verify_chain()
    period = (receipts[0].sim_time, receipts[-1].sim_time) if receipts else (store.get_clock(), store.get_clock())
    genesis = receipts[0].prev_hash if receipts else "n/a"
    head = receipts[-1].hash if receipts else "n/a"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out_path), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.8 * inch, bottomMargin=0.8 * inch, title="Executor's Accounting",
                            author="Postscript")
    story = []
    # ---- cover ------------------------------------------------------------------------------
    story += [P("Executor's Accounting", h1),
              P(f"Estate of {est.decedent_name}", h2),
              P(f"Executor: {est.executor_name}. Date of death: {est.date_of_death.isoformat()}. "
                f"Period covered: {period[0]} to {period[1]}.", body), Spacer(1, 8),
              P("This accounting was produced from an append-only record of every action taken on the estate's "
                "behalf by the Postscript agent and every decision made by the executor. Each record carries a "
                "SHA-256 hash of its contents and of the record before it; changing any record breaks the chain.",
                body), Spacer(1, 10)]
    story.append(_table([
        ["Verification", ""],
        ["Chain status", "VERIFIED: " + chain_msg if ok else "FAILED: " + chain_msg],
        ["Records", str(len(receipts))],
        ["Genesis hash", genesis],
        ["Head hash", head],
    ], [1.6 * inch, 5.2 * inch], header=True, mono_cols=(1,)))
    story.append(Spacer(1, 14))

    # ---- summary -------------------------------------------------------------------------------
    external = [r for r in receipts if r.actor == "runner" and r.policy.decision == "permit"
                and r.tool in {"submit_notification", "send_follow_up", "submit_document", "pay", "close_account",
                               "elect_option"}]
    blocked = [r for r in receipts if r.policy.decision == "forbid"]
    consumed = [r for r in receipts if r.tool in ("submit_notification", "submit_document")
                and r.policy.decision == "permit" and str(r.args_redacted.get("includes_original")).lower() == "true"]
    paid = [r for r in receipts if r.tool == "pay" and r.policy.decision == "permit"]
    story.append(P("Summary", h2))
    story.append(_table([
        ["Item", "Count / value"],
        ["Institutions notified", str(len(insts))],
        ["Tasks completed / total", f"{len([t for t in tasks if t.state == 'done'])} / {len(tasks)}"],
        ["Actions taken with institutions", str(len(external))],
        ["Actions stopped by policy pending a decision", str(len(blocked))],
        ["Decisions put to the executor", f"{len(decisions)} (" + ", ".join(
            f"{k} {v}" for k, v in sorted(Counter(d.status for d in decisions).items())) + ")"],
        ["Original certified copies consumed / remaining",
         f"{len(consumed)} / {est.certified_copies_on_hand}"],
        ["Payments made from the estate", f"{len(paid)}: " + ", ".join(
            f"${int(r.args_redacted.get('amount_cents', 0)) / 100:,.2f} (approval {r.policy.human_approval_id})" for r in paid)
         if paid else "0"],
    ], [3.3 * inch, 3.5 * inch]))

    # ---- decisions -----------------------------------------------------------------------------
    story.append(P("Decisions made by the executor", h2))
    rows = [["Date", "Institution", "Type", "Question", "Answer", "By"]]
    for d in decisions:
        rows.append([d.sim_date, P(insts[d.institution_id].name if d.institution_id in insts else d.institution_id, small),
                     "+".join(d.types), P(d.question, small),
                     P(f"{d.status}: {d.chosen_option or ''}", small), P(d.resolved_by or "", small)])
    story.append(_table(rows, [0.75 * inch, 1.2 * inch, 0.55 * inch, 2.6 * inch, 1.0 * inch, 0.7 * inch]))
    story.append(Spacer(1, 6))
    story.append(P("Decision types. " + " ".join(f"{k}: {v}." for k, v in DECISION_LABELS.items()), small))

    # ---- documents consumed --------------------------------------------------------------------
    story.append(P("Original certified documents consumed", h2))
    rows = [["Date", "Institution", "Action", "Approval"]]
    for r in consumed:
        t = store.get_task(r.task_id) if r.task_id else None
        rows.append([r.sim_time, insts[t.institution_id].name if t and t.institution_id in insts else "", r.tool,
                     r.policy.human_approval_id or ""])
    if len(rows) == 1:
        rows.append(["", "none", "", ""])
    story.append(_table(rows, [0.9 * inch, 2.6 * inch, 1.6 * inch, 1.7 * inch]))

    # ---- open items ------------------------------------------------------------------------------
    open_items = [t for t in tasks if t.state != "done"]
    story.append(P("Open items", h2))
    if open_items:
        rows = [["Task", "Institution", "State", "Next check"]]
        for t in open_items:
            rows.append([t.kind, insts[t.institution_id].name if t.institution_id in insts else t.institution_id,
                         t.state, t.due_sim_date])
        story.append(_table(rows, [1.0 * inch, 2.9 * inch, 1.5 * inch, 1.4 * inch]))
    else:
        story.append(P("None. Every institution reached a final state.", body))
    story.append(PageBreak())

    # ---- schedule of actions ------------------------------------------------------------------------
    story.append(P("Schedule of actions", h2))
    story.append(P("One row per record, in order. 'Basis' is the policy rule that allowed the action, or the "
                   "executor's approval that it ran under. Blocked rows are calls the policy stopped.", small))
    story.append(Spacer(1, 6))
    rows = [["#", "Date", "Actor", "Institution", "Action", "Result", "Basis", "Hash"]]
    for i, r in enumerate(receipts, start=1):
        t = store.get_task(r.task_id) if r.task_id else None
        inst = insts[t.institution_id].name if t and t.institution_id in insts else ("intake" if r.actor == "intake" else "")
        basis = r.policy.policy_id if r.policy.decision != "n/a" else "human"
        if r.policy.human_approval_id and r.policy.decision == "permit":
            basis = f"approval {r.policy.human_approval_id}"
        if r.policy.decision == "forbid":
            basis = "BLOCKED " + r.policy.policy_id
        rows.append([str(i), r.sim_time, P(r.actor, small), P(inst, small), P(r.tool, small),
                     P(r.result_summary[:160], small), P(basis, small), P(r.hash[7:19], mono)])
    story.append(_table(rows, [0.3 * inch, 0.7 * inch, 0.55 * inch, 1.0 * inch, 1.05 * inch, 1.85 * inch, 0.85 * inch,
                               0.7 * inch]))
    doc.build(story)
    return out_path
