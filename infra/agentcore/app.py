"""Postscript on Amazon Bedrock AgentCore Runtime.

One entrypoint, several actions. EventBridge Scheduler (via the Lambda in infra/scheduler) calls
{"action": "tick"} once a day. The dashboard or a phone can call {"action": "decision", ...}.

    agentcore configure --entrypoint infra/agentcore/app.py --name postscript
    agentcore launch
    agentcore invoke '{"action": "intake"}'
    agentcore invoke '{"action": "tick"}'

Environment (set at configure/launch time):
    POSTSCRIPT_MODE=aws  POSTSCRIPT_MODEL=bedrock  POSTSCRIPT_MODEL_ID=<inference profile>
    POSTSCRIPT_LEDGER_S3=s3://<bucket>/postscript/ledger.db   durable ledger between invocations
    POSTSCRIPT_GATEWAY_URL=https://<host>/mcp                 institution gateway (MCP over HTTP); stdio if unset
    POSTSCRIPT_MEMORY_ID=<agentcore memory id>                 optional AgentCore Memory session manager
    OTEL_EXPORTER_OTLP_ENDPOINT=...                            optional, AgentCore Observability
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402

from postscript.config import settings  # noqa: E402
from postscript.store_sync import ledger  # noqa: E402

app = BedrockAgentCoreApp()

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    try:
        from strands.telemetry import StrandsTelemetry

        StrandsTelemetry().setup_otlp_exporter()
    except Exception as exc:  # observability is optional
        print(f"telemetry disabled: {exc}", file=sys.stderr)


def gateway():
    """MCP client for the institution gateway: HTTP in the cloud, stdio locally."""
    from strands.tools.mcp import MCPClient

    url = os.getenv("POSTSCRIPT_GATEWAY_URL")
    if url:
        from mcp.client.streamable_http import streamablehttp_client

        return MCPClient(lambda: streamablehttp_client(url))
    from postscript.simulate import gateway_client

    return gateway_client(settings.seed)


@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    action = (payload or {}).get("action", "tick")
    if action == "intake":
        from postscript.agents.intake import run_intake

        with ledger(reset=True) as store:
            return run_intake(store, Path(payload.get("estate_dir", str(settings.estate_dir))), settings.sim_start)

    if action == "tick":
        from postscript.agents.runner import RunnerContext
        from postscript.agents.tick import run_tick
        from postscript.sim.server import HARNESS_TOOLS
        from postscript.simulate import _payload

        with ledger() as store:
            sim_date = payload.get("sim_date") or (date.fromisoformat(store.get_clock()) + timedelta(days=1)).isoformat()
            client = gateway()
            with client:
                tools = [t for t in client.list_tools_sync() if t.tool_name not in HARNESS_TOOLS]
                inbox = list(_payload(client.call_tool_sync("inbox", "get_inbox")) or [])
                result = run_tick(store, RunnerContext(store, tools), sim_date, settings.sim_start, inbox=inbox)
                if payload.get("advance_world", True):
                    client.call_tool_sync("advance", "advance_clock", {"days": 1})
            return result

    if action == "decision":
        from postscript.inbox import resolve

        with ledger() as store:
            return resolve(store, payload["decision_id"], payload.get("answer", "approve"), payload.get("option"),
                           payload.get("by", "executor"))

    if action == "state":
        with ledger() as store:
            ok, msg = store.verify_chain()
            return {"clock": store.get_clock(), "tasks": [t.model_dump(mode="json") for t in store.list_tasks()],
                    "open_decisions": [d.model_dump(mode="json") for d in store.list_decisions(status="open")],
                    "chain": msg}

    if action == "simulate":
        from postscript.simulate import simulate

        m = simulate(weeks=int(payload.get("weeks", 8)), out_dir=Path("/tmp/out"))
        return {k: v for k, v in m.items() if k != "world"}

    return {"error": f"unknown action {action}", "actions": ["intake", "tick", "decision", "state", "simulate"]}


if __name__ == "__main__":
    app.run()
