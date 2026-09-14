"""ReceiptHooks: a Strands HookProvider that turns every tool call into a receipt.

Blocked calls are receipts too (policy.decision = forbid). Originals consumed by a permitted
packet decrement the estate's certificate count here, because this is the one place that sees
both the call and its result.
"""

from __future__ import annotations

import json
from typing import Any

from strands.hooks import AfterToolCallEvent, HookProvider, HookRegistry

from ..models import PolicyRecord
from ..store import SQLiteLedgerStore

GATEWAY_TOOLS = {"list_institutions", "get_requirements", "submit_notification", "check_status", "send_follow_up",
                 "submit_document", "pay", "close_account", "elect_option", "get_inbox"}


def parse_result(result: Any) -> tuple[dict | list | str | None, str]:
    """Return (payload, status) from a Strands ToolResult."""
    if not isinstance(result, dict):
        return None, "unknown"
    status = result.get("status", "unknown")
    items: list = []
    for block in result.get("content", []) or []:
        if "json" in block:
            items.append(block["json"])
        elif "text" in block:
            try:
                items.append(json.loads(block["text"]))
            except (json.JSONDecodeError, TypeError):
                items.append(block["text"])
    if not items:
        return None, status
    return (items[0] if len(items) == 1 else items), status


def summarize(tool: str, payload: Any, status: str, cancelled: str | None) -> str:
    if cancelled:
        try:
            p = json.loads(cancelled)
            return f"blocked: {p.get('reason', cancelled)}"
        except (json.JSONDecodeError, TypeError):
            return f"blocked: {cancelled}"
    if isinstance(payload, dict):
        if payload.get("error"):
            return f"error: {payload['error']}"
        bits = []
        for k in ("case_ref", "status", "message", "paid", "closed", "election", "acknowledged", "accepted", "ok"):
            if k in payload and payload[k] not in (None, ""):
                bits.append(f"{k}={payload[k]}")
        return "; ".join(bits)[:300] or f"{tool} {status}"
    if isinstance(payload, list):
        return f"{len(payload)} items"
    if isinstance(payload, str):
        return payload[:200]
    return f"{tool} {status}"


class ReceiptHooks(HookProvider):
    def __init__(self, store: SQLiteLedgerStore, actor: str = "runner"):
        self.store = store
        self.actor = actor

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(AfterToolCallEvent, self.after_tool_call)

    def after_tool_call(self, event: AfterToolCallEvent) -> None:
        inv = event.invocation_state or {}
        task = inv.get("task") or {}
        tool_use = event.tool_use
        tool = tool_use["name"]
        args = dict(tool_use.get("input") or {})
        pol = (inv.get("_policy") or {}).get(tool_use["toolUseId"], {})
        cancelled = event.cancel_message
        payload, status = parse_result(event.result)
        summary = summarize(tool, payload, status, cancelled)
        evidence: list[str] = []
        if isinstance(payload, dict):
            if payload.get("case_ref"):
                evidence.append(f"gateway:case:{payload['case_ref']}")
            if payload.get("confirmation"):
                evidence.append(f"gateway:payment:{payload['confirmation']}")
            if payload.get("final_statement_ref"):
                evidence.append(f"gateway:statement:{payload['final_statement_ref']}")
        if args.get("case_ref"):
            evidence.append(f"gateway:case:{args['case_ref']}")
        for d in args.get("documents", []) or []:
            if isinstance(d, dict) and d.get("doc_ref"):
                evidence.append(f"doc:{d['doc_ref']}")
        policy = PolicyRecord(
            decision="forbid" if cancelled else ("permit" if pol.get("decision") != "forbid" else "forbid"),
            policy_id=pol.get("policy_id", "clerical" if not cancelled else "cedar"),
            human_approval_id=pol.get("human_approval_id"),
        )
        receipt = self.store.make_receipt(tool=tool, args=args, result_summary=summary, task_id=task.get("id"),
                                          actor=self.actor, evidence=sorted(set(evidence)), policy=policy)
        self.store.append_receipt(receipt)
        kind = "blocked" if cancelled else ("action" if tool in GATEWAY_TOOLS else "clerical")
        self.store.log_event(kind, f"{tool}: {summary}", {"receipt_id": receipt.receipt_id, "tool": tool,
                                                          "task_id": task.get("id"), "policy": policy.model_dump()})
        if not cancelled and isinstance(payload, dict) and payload.get("consumed_originals"):
            est = self.store.get_estate()
            est.certified_copies_on_hand -= int(payload["consumed_originals"])
            self.store.save_estate(est)
            self.store.log_event("note", f"{payload['consumed_originals']} original certificate(s) consumed; "
                                         f"{est.certified_copies_on_hand} left", {"task_id": task.get("id")})
