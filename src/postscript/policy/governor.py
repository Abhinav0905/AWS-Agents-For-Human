"""The interruption governor: a Strands InterventionHandler wrapping the vended CedarAuthorization.

Every tool call is authorized against policies/postscript.cedar. When Cedar denies a call because
it would trip one of the five decision types, the governor raises the Decision itself (once per
task and type set) and blocks the call. The model sees a structured 'blocked' result and stops
working that task; the executor sees a question in the inbox.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from strands.hooks import AfterToolCallEvent, BeforeToolCallEvent
from strands.interventions import Deny, InterventionHandler, Proceed
from strands.vended_interventions.cedar import CedarAuthorization

from ..models import Decision
from ..store import SQLiteLedgerStore, new_id
from .decisions import default_question, gate_types

POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "postscript.cedar"


class PostscriptGovernor(InterventionHandler):
    name = "postscript-governor"

    def __init__(self, store: SQLiteLedgerStore, policy_path: Path | str = POLICY_PATH):
        self.store = store
        self.policy_path = str(policy_path)
        self.cedar = CedarAuthorization(
            policies=self.policy_path,
            principal={"type": "Agent", "id": "runner"},
            context_enricher=self._enrich,
            on_error="deny",
        )

    # --- context the policy sees -------------------------------------------------------------
    def _task(self, invocation_state: dict | None) -> dict:
        task = (invocation_state or {}).get("task") or {}
        if task.get("id"):
            try:
                return self.store.get_task(task["id"]).model_dump()
            except KeyError:
                return task
        return task

    def _enrich(self, info: dict[str, Any]) -> dict[str, Any]:
        task = self._task(info.get("invocation_state"))
        approval = task.get("approval") or {}
        live = bool(approval) and not approval.get("used", False)
        return {
            "task_id": task.get("id", ""),
            "heir_conflict": bool((task.get("flags") or {}).get("heir_conflict", False)),
            "human_approved": live,
            "approval_types": "+".join(approval.get("types", [])) if live else "",
        }

    # --- lifecycle -----------------------------------------------------------------------
    def before_tool_call(self, event: BeforeToolCallEvent, **kwargs: Any) -> Proceed | Deny:
        inv = event.invocation_state if event.invocation_state is not None else {}
        task = self._task(inv)
        tool_name = event.tool_use["name"]
        args = event.tool_use.get("input") or {}
        heir_conflict = bool((task.get("flags") or {}).get("heir_conflict", False))
        types = gate_types(tool_name, args, heir_conflict)
        approval = task.get("approval") or {}
        live_approval = bool(approval) and not approval.get("used", False)

        action = self.cedar.before_tool_call(event)
        policies = inv.setdefault("_policy", {})
        tool_use_id = event.tool_use["toolUseId"]

        if isinstance(action, Deny):
            if types and task.get("id"):
                decision = self.store.find_open_decision(task["id"], types)
                if decision is None:
                    decision = self._raise_decision(task, types, tool_name, args)
                policies[tool_use_id] = {"decision": "forbid", "policy_id": "gate:" + "+".join(types),
                                         "decision_id": decision.id}
                payload = {
                    "blocked": True, "decision_types": types, "decision_id": decision.id,
                    "reason": f"Policy requires the executor's decision ({', '.join(types)}). "
                              f"Decision {decision.id} is in the inbox.",
                    "instruction": "Stop working this task now. Do not retry. It resumes once the executor answers.",
                }
                return Deny(reason=json.dumps(payload))
            policies[tool_use_id] = {"decision": "forbid", "policy_id": "cedar", "reason": action.reason}
            return Deny(reason=json.dumps({"blocked": True, "reason": action.reason,
                                           "instruction": "This call is not allowed. Choose a different action."}))

        policies[tool_use_id] = {
            "decision": "permit",
            "policy_id": ("approved:" + "+".join(types)) if types else "clerical",
            "human_approval_id": approval.get("decision_id") if (types and live_approval) else None,
            "consume": bool(types and live_approval),
            "task_id": task.get("id"),
        }
        return Proceed()

    def after_tool_call(self, event: AfterToolCallEvent, **kwargs: Any) -> Proceed:
        inv = event.invocation_state if event.invocation_state is not None else {}
        pol = (inv.get("_policy") or {}).get(event.tool_use["toolUseId"], {})
        if pol.get("consume") and event.cancel_message is None and pol.get("task_id"):
            status = (event.result or {}).get("status") if isinstance(event.result, dict) else None
            if status == "success" and not _result_is_error(event.result):
                self.store.consume_approval(pol["task_id"])
        return Proceed()

    # --- decisions raised by the governor -------------------------------------------------
    def _raise_decision(self, task: dict, types: list[str], tool_name: str, args: dict) -> Decision:
        inst = self.store.get_institution(task["institution_id"])
        name = inst.name if inst else task["institution_id"]
        left = None
        try:
            left = self.store.get_estate().certified_copies_on_hand
        except KeyError:
            pass
        question, options, rec = default_question(types, name, tool_name, args, left)
        decision = Decision(
            id=new_id("dec"), estate_id=self.store.estate_id, task_id=task["id"], institution_id=task["institution_id"],
            types=types, question=question, options=options, recommendation=rec, raised_by="governor",
            sim_date=self.store.get_clock(),
        )
        self.store.create_decision(decision)
        self.store.log_event("decision_raised", f"{name}: {question}",
                             {"decision_id": decision.id, "types": types, "raised_by": "governor", "tool": tool_name})
        return decision


def _result_is_error(result: Any) -> bool:
    try:
        for block in result.get("content", []):
            payload = block.get("json") if "json" in block else json.loads(block.get("text", "{}"))
            if isinstance(payload, dict) and (payload.get("error") or payload.get("accepted") is False
                                              or payload.get("paid") is False or payload.get("closed") is False):
                return True
    except (json.JSONDecodeError, AttributeError, TypeError):
        return False
    return False
