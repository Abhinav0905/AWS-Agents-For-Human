"""The runner: one Strands Agent per task per tick, wrapped in the governor and the receipt hooks."""

from __future__ import annotations

import json
import os
from datetime import date

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager

from ..policy.governor import PostscriptGovernor
from ..receipts.hooks import ReceiptHooks
from ..store import SQLiteLedgerStore
from ..tools.ledger_tools import make_tools
from .models import make_model

RUNNER_SYSTEM_PROMPT = """You are the clerk for an estate. A person has died and their executor has asked you to
handle the paperwork of telling banks, insurers, utilities, pensions, subscriptions and agencies, and to see each
matter through to the end. You work in the background, one task per session, on the simulated date given to you.

How you work. Read the task context. For a new task, first ask the institution gateway what it requires
(get_requirements), then render the standard letter and send the notification with copies of documents.
For an open case, check its status and take the next sensible step: wait, follow up (certified mail after two
non-responses), send a requested form, or complete the matter. After every action, update the ledger with a short
note and the next check date, then stop. Never take more than a handful of tool calls per task.

What you never do without the executor's approval: send an original certified document (includes_original=true),
sign or notarize anything or book an in-person visit (signature_kind other than none), pay money, close an
account, or record an election. If a task needs one of those, call decisions_request once with a plain-language
question, two or three options and your recommendation, then stop. If a tool result says blocked, the policy has
already asked the executor: stop working that task. If an heir has objected (heir_conflict), do nothing on that
task except ask the executor how to proceed.

Style. Letters are short, factual and kind. Notes are one line. You do not guess account numbers and you never
write down a Social Security number."""


class RunnerContext:
    """Everything a tick needs to build runner agents; created once per tick."""

    def __init__(self, store: SQLiteLedgerStore, gateway_tools: list, model=None, max_window: int = 24):
        self.store = store
        self.gateway_tools = gateway_tools
        self.model = model or make_model("runner")
        self.governor = PostscriptGovernor(store)
        self.receipts = ReceiptHooks(store, actor="runner")
        self.max_window = max_window

    def session_manager(self, task_id: str):
        """AgentCore Memory in aws mode (POSTSCRIPT_MEMORY_ID); no session manager otherwise. Tasks carry their own
        state in the ledger, so the agent never depends on conversation memory to be correct."""
        memory_id = os.getenv("POSTSCRIPT_MEMORY_ID")
        if not memory_id:
            return None
        try:
            from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
            from bedrock_agentcore.memory.integrations.strands.session_manager import (
                AgentCoreMemorySessionManager,
            )

            est = self.store.get_estate()
            cfg = AgentCoreMemoryConfig(memory_id=memory_id, session_id=f"{est.id}-{task_id}", actor_id=est.executor_id)
            return AgentCoreMemorySessionManager(cfg, region_name=os.getenv("AWS_REGION", "us-west-2"))
        except Exception as exc:  # memory is a nicety; the ledger is the source of truth
            self.store.log_event("note", f"AgentCore Memory unavailable: {exc}"[:200])
            return None

    def build_agent(self, task_id: str, sim_date: str) -> Agent:
        return Agent(
            session_manager=self.session_manager(task_id),
            model=self.model,
            system_prompt=RUNNER_SYSTEM_PROMPT,
            tools=[*make_tools(self.store), *self.gateway_tools],
            interventions=[self.governor],
            hooks=[self.receipts],
            conversation_manager=SlidingWindowConversationManager(window_size=self.max_window),
            state={"task_id": task_id, "sim_date": sim_date},
            callback_handler=None,
            name="postscript-runner",
        )

    def task_prompt(self, task_id: str, sim_date: str, sim_start: str) -> tuple[str, dict]:
        task = self.store.get_task(task_id)
        inst = self.store.get_institution(task.institution_id)
        est = self.store.get_estate()
        accounts = [a for a in self.store.list_accounts() if a.id == task.account_id]
        last4 = accounts[0].masked_last4 if accounts else ""
        ctx = {
            "sim_date": sim_date,
            "sim_start": sim_start,
            "estate": {"decedent_name": est.decedent_name, "executor_name": est.executor_name,
                       "certified_copies_on_hand": est.certified_copies_on_hand, "heirs": est.heirs},
            "institution": {"id": inst.id, "name": inst.name, "kind": inst.kind, "channel": inst.contact_channel}
            if inst else {"id": task.institution_id, "name": task.institution_id, "kind": "other", "channel": "mail"},
            "task": {**task.model_dump(), "account_last4": last4, "history": [h.model_dump() for h in task.history[-5:]]},
        }
        prompt = (f"Today is {sim_date}. Work this task and then stop.\n\nTASK_CONTEXT: {json.dumps(ctx)}")
        return prompt, ctx

    def run_task(self, task_id: str, sim_date: str, sim_start: str) -> dict:
        prompt, ctx = self.task_prompt(task_id, sim_date, sim_start)
        agent = self.build_agent(task_id, sim_date)
        invocation_state = {"task": ctx["task"], "sim_date": sim_date, "estate_id": self.store.estate_id}
        result = agent(prompt, invocation_state=invocation_state)
        final = "".join(b.get("text", "") for b in (result.message.get("content") or []) if isinstance(b, dict))
        return {"task_id": task_id, "stop_reason": result.stop_reason, "final": final.strip()[:300],
                "tool_calls": len([k for k in invocation_state.get("_policy", {})])}


def ensure_iso(d: str | date) -> str:
    return d if isinstance(d, str) else d.isoformat()
