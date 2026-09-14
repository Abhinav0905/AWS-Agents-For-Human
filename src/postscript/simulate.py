"""Time-compressed simulation: intake, then one tick per simulated day, against the MCP gateway."""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient

from .agents.intake import run_intake
from .agents.models import make_model
from .agents.runner import RunnerContext
from .agents.tick import run_tick
from .config import settings
from .inbox import resolve
from .metrics import compute_metrics, write_outputs
from .sim.server import HARNESS_TOOLS
from .store import SQLiteLedgerStore


def gateway_client(seed: int) -> MCPClient:
    env = {**os.environ, "POSTSCRIPT_SIM_SEED": str(seed)}
    src = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    params = StdioServerParameters(command=sys.executable, args=["-m", "postscript.sim.server"], env=env)
    return MCPClient(lambda: stdio_client(params))


def _payload(result) -> dict | list:
    sc = result.get("structuredContent")
    if isinstance(sc, dict) and "result" in sc:
        return sc["result"]
    items: list = []
    for block in result.get("content", []):
        if "json" in block:
            items.append(block["json"])
        elif "text" in block:
            try:
                items.append(json.loads(block["text"]))
            except json.JSONDecodeError:
                items.append({"text": block["text"]})
    if not items:
        return {}
    return items[0] if len(items) == 1 else items


def auto_approve(store: SQLiteLedgerStore, sim_date: str, delay_days: int, by: str = "maya") -> list[dict]:
    """Stand-in for the executor during unattended runs: answer each open decision with the agent's
    recommendation once it is delay_days old. The heir-conflict decision follows its recommendation (pause)."""
    out = []
    for d in store.list_decisions(status="open"):
        age = (date.fromisoformat(sim_date) - date.fromisoformat(d.sim_date)).days
        if age >= delay_days:
            out.append(resolve(store, d.id, "approve", d.recommendation, by, sim_date))
    return out


def simulate(weeks: int = 8, tick_days: int = 1, auto: str = "policy", approve_delay: int = 1, speed: float = 0.0,
             out_dir: Path = Path("out"), seed: int | None = None, on_day: Callable[[str, dict], None] | None = None,
             store_path: Path | None = None) -> dict:
    seed = settings.seed if seed is None else seed
    sim_start = settings.sim_start
    store = SQLiteLedgerStore(store_path or settings.data_dir / "ledger.db", reset=True)
    gt = json.loads((settings.estate_dir / "ground_truth.json").read_text())
    model = make_model("runner")
    client = gateway_client(seed)
    with client:
        client.call_tool_sync("harness-reset", "reset_world", {"seed": seed, "start": sim_start})
        gateway_tools = [t for t in client.list_tools_sync() if t.tool_name not in HARNESS_TOOLS]
        run_intake(store, settings.estate_dir, sim_start, model=make_model("intake"))
        runner = RunnerContext(store, gateway_tools, model=model)
        inbox: list[dict] = []
        start = date.fromisoformat(sim_start)
        days = weeks * 7
        sim_date = sim_start
        for day in range(0, days + 1, tick_days):
            sim_date = (start + timedelta(days=day)).isoformat()
            store.set_clock(sim_date)
            if auto == "policy":
                auto_approve(store, sim_date, approve_delay)
            tick = run_tick(store, runner, sim_date, sim_start, inbox=inbox)
            if on_day:
                on_day(sim_date, tick)
            client.call_tool_sync(f"harness-adv-{day}", "advance_clock", {"days": tick_days})
            inbox = list(_payload(client.call_tool_sync(f"harness-inbox-{day}", "get_inbox")) or [])
            if speed:
                time.sleep(speed)
        snapshot = _payload(client.call_tool_sync("harness-snap", "world_snapshot"))
    metrics = compute_metrics(store, gt, sim_start, sim_date, snapshot if isinstance(snapshot, dict) else None)
    write_outputs(store, metrics, out_dir)
    return metrics
