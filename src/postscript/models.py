"""Domain model. Everything the agent touches is one of these."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

InstitutionKind = Literal[
    "bank", "utility", "telecom", "insurer", "pension", "subscription",
    "credit_bureau", "dmv", "brokerage", "gym", "other",
]
Channel = Literal["portal", "email", "mail", "fax", "phone", "in_person"]
TaskKind = Literal["notify", "follow_up", "submit_form", "close", "transfer", "claim", "cancel", "pay", "respond"]
TaskState = Literal["queued", "drafted", "sent", "awaiting_institution", "awaiting_human", "blocked", "done", "failed"]
DecisionType = Literal["D1", "D2", "D3", "D4", "D5"]

DECISION_LABELS: dict[str, str] = {
    "D1": "money leaves the estate",
    "D2": "an original certified document leaves your hands",
    "D3": "your signature, a notary, or an in-person visit",
    "D4": "an irreversible step (closure, sale, election)",
    "D5": "an heir disagrees",
}

# The task state machine. update_task refuses anything not listed here.
TRANSITIONS: dict[str, set[str]] = {
    "queued": {"drafted", "sent", "awaiting_institution", "awaiting_human", "blocked", "failed", "done"},
    "drafted": {"sent", "awaiting_institution", "awaiting_human", "blocked", "failed"},
    "sent": {"awaiting_institution", "awaiting_human", "blocked", "done", "failed"},
    "awaiting_institution": {"awaiting_institution", "awaiting_human", "blocked", "done", "failed", "queued"},
    "awaiting_human": {"queued", "awaiting_institution", "blocked", "done", "failed"},
    "blocked": {"queued", "awaiting_institution", "awaiting_human", "done", "failed"},
    "done": set(),
    "failed": {"queued"},
}


class DocumentRequirement(BaseModel):
    doc_type: str
    original_required: bool = False
    notes: str = ""


class Institution(BaseModel):
    id: str
    name: str
    kind: InstitutionKind
    contact_channel: Channel
    requirements: list[DocumentRequirement] = Field(default_factory=list)
    typical_response_days: int = 7
    playbook_id: str = ""


class Account(BaseModel):
    id: str
    institution_id: str
    label: str
    masked_last4: str
    owner_role: Literal["decedent", "joint"] = "decedent"
    status: str = "open"


class Flags(BaseModel):
    money_out: bool = False
    consumes_original: bool = False
    requires_signature: bool = False
    irreversible: bool = False
    heir_conflict: bool = False


class TaskEvent(BaseModel):
    sim_date: str
    note: str


class Approval(BaseModel):
    decision_id: str
    types: list[DecisionType]
    chosen_option: str
    token: str
    used: bool = False


class Task(BaseModel):
    id: str
    estate_id: str
    institution_id: str
    account_id: str | None = None
    kind: TaskKind
    state: TaskState = "queued"
    due_sim_date: str
    last_action_sim_date: str | None = None
    attempts: int = 0
    case_ref: str | None = None
    flags: Flags = Field(default_factory=Flags)
    approval: Approval | None = None
    history: list[TaskEvent] = Field(default_factory=list)


class Decision(BaseModel):
    id: str
    estate_id: str
    task_id: str
    institution_id: str
    types: list[DecisionType]
    question: str
    options: list[str]
    recommendation: str
    raised_by: Literal["agent", "governor"]
    sim_date: str
    status: Literal["open", "approved", "denied", "edited"] = "open"
    chosen_option: str | None = None
    resolved_by: str | None = None
    resolved_sim_date: str | None = None
    evidence_receipt_ids: list[str] = Field(default_factory=list)


class PolicyRecord(BaseModel):
    decision: Literal["permit", "forbid", "n/a"] = "n/a"
    policy_id: str = ""
    human_approval_id: str | None = None


class Receipt(BaseModel):
    receipt_id: str
    estate_id: str
    task_id: str | None
    sim_time: str
    wall_time: str
    actor: str
    tool: str
    args_redacted: dict
    result_summary: str
    evidence: list[str] = Field(default_factory=list)
    policy: PolicyRecord = Field(default_factory=PolicyRecord)
    prev_hash: str
    hash: str = ""


class Estate(BaseModel):
    id: str
    decedent_name: str
    date_of_death: date
    executor_name: str
    executor_id: str
    heirs: list[str]
    certified_copies_on_hand: int = 5
    timezone: str = "America/Los_Angeles"


class Event(BaseModel):
    """One line in out/events.jsonl. Not a receipt: receipts are for tool calls."""

    seq: int = 0
    estate_id: str
    sim_date: str
    kind: str  # action | decision_raised | decision_resolved | inbound | tick | intake | note
    summary: str
    data: dict = Field(default_factory=dict)
