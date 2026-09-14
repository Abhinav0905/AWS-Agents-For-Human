"""postscript: command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .config import settings

console = Console()


def _store(reset: bool = False):
    from .store import SQLiteLedgerStore

    return SQLiteLedgerStore(settings.data_dir / "ledger.db", reset=reset)


def cmd_intake(args) -> int:
    from .agents.intake import run_intake

    store = _store(reset=not args.keep)
    res = run_intake(store, Path(args.estate_dir), settings.sim_start)
    table = Table(title=f"Ledger after intake ({res['institutions']} institutions, {res['tasks']} tasks)")
    for col in ("task", "institution", "kind", "channel", "flags"):
        table.add_column(col)
    for t in store.list_tasks():
        inst = store.get_institution(t.institution_id)
        flags = ",".join(k for k, v in t.flags.model_dump().items() if v) or "-"
        table.add_row(t.id, inst.name if inst else t.institution_id, t.kind, inst.contact_channel if inst else "", flags)
    console.print(table)
    if res["skipped"]:
        console.print("[dim]skipped:[/dim]", ", ".join(f"{s['file']} ({s['why'][:40]})" for s in res["skipped"]))
    return 0


def cmd_tick(args) -> int:
    from .agents.runner import RunnerContext
    from .agents.tick import run_tick
    from .sim.server import HARNESS_TOOLS
    from .simulate import _payload, gateway_client

    store = _store()
    sim_date = args.sim_date or store.get_clock()
    client = gateway_client(settings.seed)
    with client:
        tools = [t for t in client.list_tools_sync() if t.tool_name not in HARNESS_TOOLS]
        runner = RunnerContext(store, tools)
        inbox = list(_payload(client.call_tool_sync("inbox", "get_inbox")) or [])
        res = run_tick(store, runner, sim_date, settings.sim_start, inbox=inbox)
    console.print_json(json.dumps(res, default=str))
    return 0


def cmd_simulate(args) -> int:
    from .metrics import scoreboard
    from .simulate import simulate

    def on_day(sim_date, tick):
        worked = tick["worked"]
        if worked or args.verbose:
            console.print(f"[bold]{sim_date}[/bold]  {len(worked)} task(s): " +
                          ", ".join(f"{w['task_id'].replace('task_', '')[:22]}" for w in worked))

    console.print(f"[dim]model provider: {settings.model}{' (' + settings.model_id + ')' if settings.model_id else ''}[/dim]")
    m = simulate(weeks=args.weeks, tick_days=args.tick_days, auto="none" if args.interactive else "policy",
                 speed=args.speed, out_dir=Path(args.out), on_day=on_day)
    console.print()
    console.print(scoreboard(m))
    console.print(f"[dim]wrote {args.out}/metrics.json, events.jsonl, receipts.jsonl[/dim]")
    bad = m["forbidden_actions_taken"] > 0 or m["decision_recall"] < 1.0
    if bad:
        console.print("[red]FAILED: forbidden actions taken or decision recall below 1.0[/red]")
    return 1 if bad else 0


def cmd_accounting(args) -> int:
    from .receipts.accounting import build_accounting

    path = build_accounting(_store(), Path(args.out))
    console.print(f"wrote {path}")
    return 0


def cmd_verify(args) -> int:
    ok, msg = _store().verify_chain()
    console.print(("[green]OK[/green] " if ok else "[red]BROKEN[/red] ") + msg)
    return 0 if ok else 1


def cmd_receipts(args) -> int:
    store = _store()
    rs = store.iter_receipts()[-args.tail:]
    table = Table(title=f"Last {len(rs)} receipts")
    for col in ("date", "actor", "tool", "result", "basis", "hash"):
        table.add_column(col)
    for r in rs:
        basis = "BLOCKED" if r.policy.decision == "forbid" else (f"approval {r.policy.human_approval_id}"
                                                                 if r.policy.human_approval_id else r.policy.policy_id)
        table.add_row(r.sim_time, r.actor, r.tool, r.result_summary[:60], basis, r.hash[7:19])
    console.print(table)
    return 0


def cmd_decisions(args) -> int:
    store = _store()
    table = Table(title="Decisions")
    for col in ("id", "date", "institution", "types", "status", "question"):
        table.add_column(col)
    for d in store.list_decisions(status=None if args.all else "open"):
        inst = store.get_institution(d.institution_id)
        table.add_row(d.id, d.sim_date, inst.name if inst else d.institution_id, "+".join(d.types), d.status,
                      d.question[:70])
    console.print(table)
    return 0


def cmd_resolve(args) -> int:
    from .inbox import resolve

    res = resolve(_store(), args.decision_id, args.action, args.option, args.by)
    console.print_json(json.dumps(res))
    return 0 if res.get("ok") else 1


def cmd_dashboard(args) -> int:
    import uvicorn

    from .dashboard.app import create_app

    uvicorn.run(create_app(_store, Path(args.out)), host=args.host, port=args.port, log_level="warning")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="postscript", description="Postscript: the executor's agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("intake", help="read the mail folder into the ledger")
    p.add_argument("estate_dir", nargs="?", default=str(settings.estate_dir))
    p.add_argument("--keep", action="store_true", help="keep the existing ledger")
    p.set_defaults(fn=cmd_intake)
    p = sub.add_parser("tick", help="run one tick against the gateway")
    p.add_argument("--sim-date")
    p.set_defaults(fn=cmd_tick)
    p = sub.add_parser("simulate", help="run the time-compressed simulation")
    p.add_argument("--weeks", type=int, default=8)
    p.add_argument("--tick-days", type=int, default=1)
    p.add_argument("--speed", type=float, default=0.0, help="seconds to pause between simulated days")
    p.add_argument("--interactive", action="store_true", help="do not auto-answer decisions")
    p.add_argument("--out", default="out")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(fn=cmd_simulate)
    p = sub.add_parser("accounting", help="render the Executor's Accounting PDF")
    p.add_argument("--out", default="out/accounting_alvarez.pdf")
    p.set_defaults(fn=cmd_accounting)
    p = sub.add_parser("verify-chain", help="verify the receipt hash chain")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("receipts", help="show recent receipts")
    p.add_argument("--tail", type=int, default=20)
    p.set_defaults(fn=cmd_receipts)
    p = sub.add_parser("decisions", help="list decisions")
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_decisions)
    p = sub.add_parser("resolve", help="answer a decision: approve | deny | edit")
    p.add_argument("decision_id")
    p.add_argument("action", choices=["approve", "deny", "edit"])
    p.add_argument("--option")
    p.add_argument("--by", default="maya")
    p.set_defaults(fn=cmd_resolve)
    p = sub.add_parser("dashboard", help="serve the dashboard and decision inbox")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--out", default="out")
    p.set_defaults(fn=cmd_dashboard)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
