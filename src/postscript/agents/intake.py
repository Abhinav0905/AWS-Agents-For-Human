"""Intake: read the shoebox of mail and turn it into institutions, accounts and tasks."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel
from pypdf import PdfReader
from strands import Agent

from .. import playbooks
from ..models import Account, Estate, Flags, Institution, Task
from ..store import SQLiteLedgerStore
from .models import make_model

INTAKE_SYSTEM_PROMPT = """You are the intake clerk for an estate. You read one piece of mail at a time and extract
only what the document supports: the institution's name, what kind of institution it is, how it wants to be
contacted, and the last four digits of the account. Never guess account numbers. Marketing mail and flyers are
not relevant. If a document is an image you cannot read, say so in notes and mark it not relevant."""


class IntakeExtraction(BaseModel):
    is_relevant: bool
    institution_name: str
    kind: str
    account_label: str
    masked_last4: str | None = None
    contact_channel: str = "mail"
    document_type: str = "document"
    confidence: float = 0.5
    notes: str = ""


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]


def read_document(path: Path) -> list[dict]:
    """Return Strands content blocks for one file: text for PDFs/emails, an image block for scans."""
    if path.suffix.lower() == ".pdf":
        text = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
        return [{"text": f"DOCUMENT: {path.name}\n{text}"}]
    if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        fmt = "png" if path.suffix.lower() == ".png" else "jpeg"
        return [{"text": f"DOCUMENT: {path.name} (scanned image)"},
                {"image": {"format": fmt, "source": {"bytes": path.read_bytes()}}}]
    return [{"text": f"DOCUMENT: {path.name}\n{path.read_text(errors='replace')}"}]


def run_intake(store: SQLiteLedgerStore, estate_dir: Path, sim_start: str, model=None) -> dict:
    import json

    est_raw = json.loads((estate_dir / "estate.json").read_text())
    estate = Estate(**{k: v for k, v in est_raw.items() if k in Estate.model_fields})
    store.save_estate(estate)
    store.set_clock(sim_start)
    model = model or make_model("intake")
    agent = Agent(model=model, system_prompt=INTAKE_SYSTEM_PROMPT, callback_handler=None, name="postscript-intake")

    found: dict[tuple[str, str], dict] = {}
    skipped: list[dict] = []
    files = sorted(p for p in (estate_dir / "mail").iterdir() if p.is_file())
    for path in files:
        blocks = read_document(path)
        blocks.append({"text": "Extract the institution, kind, contact channel and account last-four from this document."})
        agent.messages.clear()  # one document per conversation; nothing carries over
        result = agent(blocks, structured_output_model=IntakeExtraction)
        ex = result.structured_output
        if ex is None:  # a model that declined to extract: treat as not relevant, keep the receipt
            ex = IntakeExtraction(is_relevant=False, institution_name="", kind="other", account_label="",
                                  notes="model returned no structured output")
        store.append_receipt(store.make_receipt(
            tool="intake.extract", args={"file": path.name},
            result_summary=(f"{ex.institution_name} / {ex.kind} / ****{ex.masked_last4}" if ex.is_relevant
                            else f"not relevant: {ex.notes or ex.document_type}"),
            task_id=None, actor="intake", evidence=[f"mail:{path.name}"]))
        if not ex.is_relevant or not ex.masked_last4:
            skipped.append({"file": path.name, "why": ex.notes or "not relevant"})
            continue
        key = (slug(ex.institution_name), ex.masked_last4)
        if key in found:
            found[key]["files"].append(path.name)
            continue
        found[key] = {"extraction": ex, "files": [path.name]}

    created = []
    seen_inst: set[str] = set()
    for (inst_id, last4), item in found.items():
        ex: IntakeExtraction = item["extraction"]
        pb = playbooks.load(ex.kind)
        if inst_id not in seen_inst:
            store.upsert_institution(Institution(id=inst_id, name=ex.institution_name, kind=ex.kind if ex.kind in
                                                 Institution.model_fields["kind"].annotation.__args__ else "other",
                                                 contact_channel=ex.contact_channel if ex.contact_channel in
                                                 Institution.model_fields["contact_channel"].annotation.__args__ else "mail",
                                                 typical_response_days=pb.typical_response_days, playbook_id=pb.kind))
            seen_inst.add(inst_id)
        acct = Account(id=f"acct_{inst_id}_{last4}", institution_id=inst_id, label=ex.account_label or ex.document_type,
                       masked_last4=last4)
        store.upsert_account(acct)
        if not any(t.institution_id == inst_id for t in created):
            task = Task(id=f"task_{inst_id}", estate_id=store.estate_id, institution_id=inst_id, account_id=acct.id,
                        kind=pb.initial_task, due_sim_date=sim_start, flags=Flags(**pb.likely_flags))  # type: ignore[arg-type]
            store.create_task(task)
            created.append(task)
    store.log_event("intake", f"intake: {len(files)} documents, {len(seen_inst)} institutions, "
                              f"{len(created)} tasks, {len(skipped)} skipped",
                    {"skipped": skipped, "institutions": sorted(seen_inst)}, sim_date=sim_start)
    return {"documents": len(files), "institutions": len(seen_inst), "tasks": len(created), "skipped": skipped,
            "accounts": len(found)}


def today_iso() -> str:
    return date.today().isoformat()
