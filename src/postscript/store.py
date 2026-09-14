"""Ledger store. SQLite for local mode; the same interface is what aws mode implements.

Receipts are append-only at the SQL level: this module has no UPDATE or DELETE for that table.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

from .models import (
    TRANSITIONS,
    Account,
    Approval,
    Decision,
    Estate,
    Event,
    Institution,
    PolicyRecord,
    Receipt,
    Task,
    TaskEvent,
)
from .redaction import redact


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class LedgerStore(Protocol):
    def get_estate(self) -> Estate: ...
    def save_estate(self, estate: Estate) -> None: ...
    def upsert_institution(self, inst: Institution) -> None: ...
    def upsert_account(self, acct: Account) -> None: ...
    def create_task(self, task: Task) -> Task: ...
    def update_task(self, task_id: str, **patch) -> Task: ...
    def list_tasks(self, states: Iterable[str] | None = None, due_before: str | None = None) -> list[Task]: ...
    def create_decision(self, d: Decision) -> Decision: ...
    def resolve_decision(self, decision_id: str, status: str, chosen_option: str, by: str, sim_date: str) -> Decision: ...
    def append_receipt(self, receipt: Receipt) -> Receipt: ...
    def iter_receipts(self) -> list[Receipt]: ...
    def last_receipt_hash(self) -> str: ...
    def get_clock(self) -> str: ...
    def set_clock(self, sim_date: str) -> None: ...


class SQLiteLedgerStore:
    def __init__(self, path: Path | str, estate_id: str = "est_alvarez", reset: bool = False):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if reset and self.path.exists():
            self.path.unlink()
        self.estate_id = estate_id
        self._lock = threading.RLock()
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self._init()

    def _init(self) -> None:
        with self.db:
            self.db.executescript(
                """
                CREATE TABLE IF NOT EXISTS entities (kind TEXT, id TEXT, estate_id TEXT, json TEXT, updated TEXT,
                    PRIMARY KEY (kind, id));
                CREATE TABLE IF NOT EXISTS receipts (seq INTEGER PRIMARY KEY AUTOINCREMENT, receipt_id TEXT UNIQUE,
                    estate_id TEXT, task_id TEXT, prev_hash TEXT, hash TEXT, json TEXT);
                CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, estate_id TEXT,
                    sim_date TEXT, kind TEXT, json TEXT);
                CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT);
                """
            )

    # ---- generic helpers -------------------------------------------------
    def _put(self, kind: str, obj) -> None:
        with self._lock, self.db:
            self.db.execute(
                "INSERT INTO entities(kind,id,estate_id,json,updated) VALUES(?,?,?,?,?) "
                "ON CONFLICT(kind,id) DO UPDATE SET json=excluded.json, updated=excluded.updated",
                (kind, obj.id, self.estate_id, obj.model_dump_json(), datetime.now(UTC).isoformat()),
            )

    def _get(self, kind: str, id_: str, cls):
        row = self.db.execute("SELECT json FROM entities WHERE kind=? AND id=?", (kind, id_)).fetchone()
        return cls.model_validate_json(row[0]) if row else None

    def _all(self, kind: str, cls) -> list:
        rows = self.db.execute("SELECT json FROM entities WHERE kind=? ORDER BY id", (kind,)).fetchall()
        return [cls.model_validate_json(r[0]) for r in rows]

    # ---- estate / institutions / accounts ----------------------------------
    def get_estate(self) -> Estate:
        est = self._get("estate", self.estate_id, Estate)
        if est is None:
            raise KeyError("estate not initialised")
        return est

    def save_estate(self, estate: Estate) -> None:
        self.estate_id = estate.id
        self._put("estate", estate)

    def upsert_institution(self, inst: Institution) -> None:
        self._put("institution", inst)

    def get_institution(self, id_: str) -> Institution | None:
        return self._get("institution", id_, Institution)

    def list_institutions(self) -> list[Institution]:
        return self._all("institution", Institution)

    def upsert_account(self, acct: Account) -> None:
        self._put("account", acct)

    def list_accounts(self) -> list[Account]:
        return self._all("account", Account)

    # ---- tasks -------------------------------------------------------------
    def create_task(self, task: Task) -> Task:
        self._put("task", task)
        return task

    def get_task(self, task_id: str) -> Task:
        t = self._get("task", task_id, Task)
        if t is None:
            raise KeyError(task_id)
        return t

    def update_task(self, task_id: str, **patch) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            new_state = patch.get("state")
            if new_state and new_state != task.state and new_state not in TRANSITIONS[task.state]:
                raise ValueError(f"illegal transition {task.state} -> {new_state} for {task_id}")
            note = patch.pop("note", None)
            sim_date = patch.pop("sim_date", None) or self.get_clock()
            data = task.model_dump()
            for k, v in patch.items():
                if k == "flags" and isinstance(v, dict):
                    data["flags"].update(v)
                elif k == "approval" and isinstance(v, dict):
                    data["approval"] = v
                else:
                    data[k] = v
            if note:
                data["history"].append(TaskEvent(sim_date=sim_date, note=note).model_dump())
            data["last_action_sim_date"] = sim_date
            updated = Task.model_validate(data)
            self._put("task", updated)
            return updated

    def list_tasks(self, states: Iterable[str] | None = None, due_before: str | None = None) -> list[Task]:
        tasks = self._all("task", Task)
        if states is not None:
            s = set(states)
            tasks = [t for t in tasks if t.state in s]
        if due_before is not None:
            tasks = [t for t in tasks if t.due_sim_date <= due_before]
        return sorted(tasks, key=lambda t: (t.due_sim_date, t.id))

    # ---- decisions ---------------------------------------------------------
    def create_decision(self, d: Decision) -> Decision:
        self._put("decision", d)
        self.update_task(d.task_id, state="awaiting_human", note=f"decision {d.id} raised ({'+'.join(d.types)})")
        return d

    def get_decision(self, decision_id: str) -> Decision:
        d = self._get("decision", decision_id, Decision)
        if d is None:
            raise KeyError(decision_id)
        return d

    def list_decisions(self, status: str | None = None) -> list[Decision]:
        ds = self._all("decision", Decision)
        if status:
            ds = [d for d in ds if d.status == status]
        return sorted(ds, key=lambda d: (d.sim_date, d.id))

    def find_open_decision(self, task_id: str, types: list[str]) -> Decision | None:
        for d in self.list_decisions():
            if d.task_id == task_id and set(d.types) == set(types) and d.status in ("open", "approved", "edited"):
                return d
        return None

    def resolve_decision(self, decision_id: str, status: str, chosen_option: str, by: str, sim_date: str) -> Decision:
        d = self.get_decision(decision_id)
        d.status = status  # type: ignore[assignment]
        d.chosen_option = chosen_option
        d.resolved_by = by
        d.resolved_sim_date = sim_date
        self._put("decision", d)
        if status in ("approved", "edited"):
            token = uuid.uuid4().hex
            approval = Approval(decision_id=d.id, types=d.types, chosen_option=chosen_option, token=token)
            self.update_task(d.task_id, state="queued", due_sim_date=sim_date, approval=approval.model_dump(),
                             note=f"decision {d.id} {status}: {chosen_option}")
        else:
            self.update_task(d.task_id, state="blocked", note=f"decision {d.id} denied")
        return d

    def consume_approval(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if task.approval and not task.approval.used:
            ap = task.approval.model_dump()
            ap["used"] = True
            self.update_task(task_id, approval=ap, note="approval token consumed")

    # ---- receipts (append-only) -------------------------------------------
    def last_receipt_hash(self) -> str:
        row = self.db.execute("SELECT hash FROM receipts ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else sha256(f"genesis:{self.estate_id}")

    def append_receipt(self, receipt: Receipt) -> Receipt:
        with self._lock, self.db:
            receipt.prev_hash = self.last_receipt_hash()
            receipt.args_redacted = redact(receipt.args_redacted)
            body = receipt.model_dump()
            body.pop("hash", None)
            receipt.hash = sha256(canonical(body))
            self.db.execute(
                "INSERT INTO receipts(receipt_id, estate_id, task_id, prev_hash, hash, json) VALUES(?,?,?,?,?,?)",
                (receipt.receipt_id, receipt.estate_id, receipt.task_id, receipt.prev_hash, receipt.hash,
                 receipt.model_dump_json()),
            )
        return receipt

    def iter_receipts(self) -> list[Receipt]:
        rows = self.db.execute("SELECT json FROM receipts ORDER BY seq").fetchall()
        return [Receipt.model_validate_json(r[0]) for r in rows]

    def verify_chain(self) -> tuple[bool, str]:
        prev = sha256(f"genesis:{self.estate_id}")
        for i, r in enumerate(self.iter_receipts()):
            if r.prev_hash != prev:
                return False, f"receipt #{i + 1} {r.receipt_id}: prev_hash mismatch"
            body = r.model_dump()
            body.pop("hash", None)
            if sha256(canonical(body)) != r.hash:
                return False, f"receipt #{i + 1} {r.receipt_id}: hash mismatch (tampered)"
            prev = r.hash
        return True, f"{len(self.iter_receipts())} receipts verified"

    # ---- events / clock ------------------------------------------------------
    def log_event(self, kind: str, summary: str, data: dict | None = None, sim_date: str | None = None) -> Event:
        ev = Event(estate_id=self.estate_id, sim_date=sim_date or self.get_clock(), kind=kind, summary=summary,
                   data=data or {})
        with self._lock, self.db:
            cur = self.db.execute("INSERT INTO events(estate_id, sim_date, kind, json) VALUES(?,?,?,?)",
                                  (ev.estate_id, ev.sim_date, ev.kind, ev.model_dump_json()))
            ev.seq = cur.lastrowid or 0
        return ev

    def iter_events(self, since_seq: int = 0) -> list[Event]:
        rows = self.db.execute("SELECT seq, json FROM events WHERE seq>? ORDER BY seq", (since_seq,)).fetchall()
        out = []
        for seq, js in rows:
            ev = Event.model_validate_json(js)
            ev.seq = seq
            out.append(ev)
        return out

    def get_clock(self) -> str:
        row = self.db.execute("SELECT value FROM kv WHERE key='clock'").fetchone()
        return row[0] if row else date.today().isoformat()

    def set_clock(self, sim_date: str) -> None:
        with self._lock, self.db:
            self.db.execute("INSERT INTO kv(key,value) VALUES('clock',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (sim_date,))

    def make_receipt(self, *, tool: str, args: dict, result_summary: str, task_id: str | None, actor: str,
                     evidence: list[str] | None = None, policy: PolicyRecord | None = None) -> Receipt:
        return Receipt(
            receipt_id=new_id("rcp"), estate_id=self.estate_id, task_id=task_id, sim_time=self.get_clock(),
            wall_time=datetime.now(UTC).isoformat(timespec="seconds"), actor=actor, tool=tool,
            args_redacted=args, result_summary=result_summary[:400], evidence=evidence or [],
            policy=policy or PolicyRecord(), prev_hash="",
        )
