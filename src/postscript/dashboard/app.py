"""One page: the ledger, the decision inbox, the activity feed, the receipts, and the metric strip."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse

from ..inbox import resolve
from ..models import DECISION_LABELS

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Postscript</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--ink:#182233;--muted:#5d6675;--rule:#d9dde3;--paper:#ffffff;--soft:#f4f6f8;--go:#0f6e56;--go-bg:#e1f5ee;--wait:#8a5a00;--wait-bg:#fbf0d9;--stop:#8f2c2c;--stop-bg:#fbe9e9}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
h1,h2,.serif{font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;font-weight:500;margin:0}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:28px 40px 18px;border-bottom:2px solid var(--ink)}
header h1{font-size:34px;line-height:1.1}header .sub{color:var(--muted);margin-top:4px}
.clock{text-align:right}.clock b{font-size:28px;display:block;font-weight:500}.clock span{color:var(--muted)}
.strip{display:grid;grid-template-columns:repeat(6,1fr);gap:0;border-bottom:1px solid var(--rule);padding:0 40px}
.strip div{padding:14px 12px 12px 0;border-right:1px solid var(--rule);margin-right:12px}.strip div:last-child{border-right:0}
.strip b{display:block;font-size:26px;font-weight:500;line-height:1.1}.strip span{color:var(--muted);font-size:13px}
main{display:grid;grid-template-columns:1.25fr 1fr;gap:40px;padding:24px 40px 40px}
section h2{font-size:20px;margin:0 0 10px;padding-bottom:6px;border-bottom:1px solid var(--rule)}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:7px 8px 7px 0;vertical-align:top;border-bottom:1px solid var(--rule);font-size:14px}th{color:var(--muted);font-weight:500;font-size:12px}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;background:var(--soft)}
.pill.done{background:var(--go-bg);color:var(--go)}.pill.awaiting_human{background:var(--wait-bg);color:var(--wait)}.pill.blocked{background:var(--stop-bg);color:var(--stop)}
.decision{border-left:4px solid var(--wait);background:var(--wait-bg);padding:12px 14px;margin:0 0 12px}
.decision.approved,.decision.edited{border-left-color:var(--go);background:var(--soft)}.decision.denied{border-left-color:var(--stop);background:var(--soft)}
.decision .q{font-size:15px;margin:4px 0 8px}.decision small{color:var(--muted)}
button{font:inherit;font-size:14px;padding:6px 12px;border:1px solid var(--ink);background:var(--paper);color:var(--ink);cursor:pointer;margin-right:6px}
button.go{background:var(--go);border-color:var(--go);color:#fff}
.feed li{list-style:none;padding:6px 0;border-bottom:1px solid var(--rule);font-size:14px}.feed{margin:0;padding:0}.feed .d{color:var(--muted);margin-right:8px;font-variant-numeric:tabular-nums}
.feed .blocked{color:var(--stop)}.feed .decision_raised{color:var(--wait)}.feed .decision_resolved{color:var(--go)}
code{font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;background:var(--soft);padding:1px 4px}
.chain{font-size:13px;margin-left:10px;color:var(--go)}.chain.bad{color:var(--stop)}
.full{grid-column:1/3}
</style></head><body>
<header><div><h1>Postscript</h1><div class="sub" id="sub">Loading the estate…</div></div>
<div class="clock"><b id="clock">—</b><span id="certs"></span></div></header>
<div class="strip" id="strip"></div>
<main>
 <section><h2>Ledger</h2><table><thead><tr><th>Institution</th><th>Task</th><th>State</th><th>Next check</th><th>Last note</th></tr></thead><tbody id="ledger"></tbody></table></section>
 <section><h2>Decision inbox <small id="inboxcount" style="color:var(--muted);font-weight:400"></small></h2><div id="inbox"></div></section>
 <section><h2>Activity</h2><ul class="feed" id="feed"></ul></section>
 <section><h2>Receipts <span class="chain" id="chain"></span></h2><table><thead><tr><th>Date</th><th>Actor</th><th>Tool</th><th>Basis</th><th>Hash</th></tr></thead><tbody id="receipts"></tbody></table></section>
</main>
<script>
const $=id=>document.getElementById(id);
function esc(s){return String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function act(id,action){const opt=action==='edit'?prompt('Option to choose:'):null;await fetch(`/api/decisions/${id}/${action}`,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'option='+encodeURIComponent(opt||'')});load();}
async function load(){const r=await fetch('/api/state');const s=await r.json();
 $('sub').textContent=`Estate of ${s.estate.decedent_name}. Executor ${s.estate.executor_name}.`;
 $('clock').textContent=s.clock;$('certs').textContent=`${s.estate.certified_copies_on_hand} certified originals on hand`;
 const m=s.metrics||{};const strip=[[s.counts.actions,'actions taken'],[s.counts.open_decisions,'decisions waiting on you'],[s.counts.decisions,'decisions in total'],[m.interruption_precision??'—','interruption precision'],[m.decision_recall??'—','decision recall'],[s.counts.blocked,'calls stopped by policy']];
 $('strip').innerHTML=strip.map(([b,l])=>`<div><b>${esc(b)}</b><span>${l}</span></div>`).join('');
 $('ledger').innerHTML=s.tasks.map(t=>`<tr><td>${esc(t.institution)}</td><td>${esc(t.kind)}</td><td><span class="pill ${t.state}">${t.state.replace('_',' ')}</span></td><td>${esc(t.due)}</td><td style="color:var(--muted)">${esc(t.note)}</td></tr>`).join('');
 const open=s.decisions.filter(d=>d.status==='open');$('inboxcount').textContent=open.length?`${open.length} open`:'nothing waiting';
 $('inbox').innerHTML=s.decisions.map(d=>`<div class="decision ${d.status}"><small>${esc(d.sim_date)} · ${esc(d.institution)} · ${d.types.map(t=>esc(t+': '+d.labels[t])).join('; ')}</small><div class="q serif">${esc(d.question)}</div>${d.status==='open'?`<div><small>Recommended: ${esc(d.recommendation)}</small></div><div style="margin-top:8px">${d.options.map(o=>`<button class="${o===d.recommendation?'go':''}" onclick="act('${d.id}','${o===d.recommendation?'approve':'edit'}')" data-o="${esc(o)}">${esc(o)}</button>`).join('')}<button onclick="act('${d.id}','deny')">deny</button></div>`:`<small>${esc(d.status)}: ${esc(d.chosen_option)} · by ${esc(d.resolved_by)} on ${esc(d.resolved_sim_date)}</small>`}</div>`).join('')||'<p style="color:var(--muted)">No decisions yet.</p>';
 $('feed').innerHTML=s.events.map(e=>`<li class="${e.kind}"><span class="d">${esc(e.sim_date)}</span>${esc(e.summary)}</li>`).join('');
 $('chain').textContent=s.chain.ok?`chain verified (${s.chain.count})`:'CHAIN BROKEN';$('chain').className='chain'+(s.chain.ok?'':' bad');
 $('receipts').innerHTML=s.receipts.map(r=>`<tr><td>${esc(r.sim_time)}</td><td>${esc(r.actor)}</td><td>${esc(r.tool)}</td><td>${esc(r.basis)}</td><td><code>${esc(r.hash)}</code></td></tr>`).join('');}
load();setInterval(load,2000);
</script></body></html>"""


def create_app(store_factory: Callable, out_dir: Path) -> FastAPI:
    app = FastAPI(title="Postscript dashboard")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PAGE

    @app.get("/api/state")
    def state():
        store = store_factory()
        try:
            est = store.get_estate().model_dump(mode="json")
        except KeyError:
            return JSONResponse({"estate": {"decedent_name": "—", "executor_name": "—", "certified_copies_on_hand": 0},
                                 "clock": "—", "tasks": [], "decisions": [], "events": [], "receipts": [],
                                 "counts": {"actions": 0, "open_decisions": 0, "decisions": 0, "blocked": 0},
                                 "chain": {"ok": True, "count": 0}, "metrics": None})
        insts = {i.id: i.name for i in store.list_institutions()}
        tasks = [{"id": t.id, "institution": insts.get(t.institution_id, t.institution_id), "kind": t.kind,
                  "state": t.state, "due": t.due_sim_date, "note": t.history[-1].note[:90] if t.history else ""}
                 for t in store.list_tasks()]
        ordered = sorted(store.list_decisions(), key=lambda d: (d.status != "open", d.sim_date))
        decisions = [{"id": d.id, "sim_date": d.sim_date, "institution": insts.get(d.institution_id, d.institution_id),
                      "types": d.types, "labels": DECISION_LABELS, "question": d.question, "options": d.options,
                      "recommendation": d.recommendation, "status": d.status, "chosen_option": d.chosen_option,
                      "resolved_by": d.resolved_by, "resolved_sim_date": d.resolved_sim_date}
                     for d in ordered]
        events = [e.model_dump() for e in store.iter_events()[-40:]][::-1]
        receipts = store.iter_receipts()
        ok, msg = store.verify_chain()
        recent = [{"sim_time": r.sim_time, "actor": r.actor, "tool": r.tool, "hash": r.hash[7:19],
                   "basis": "BLOCKED" if r.policy.decision == "forbid" else
                   (f"approval {r.policy.human_approval_id}" if r.policy.human_approval_id else r.policy.policy_id)}
                  for r in receipts[-20:]][::-1]
        metrics = None
        mp = out_dir / "metrics.json"
        if mp.exists():
            try:
                metrics = json.loads(mp.read_text())
            except json.JSONDecodeError:
                metrics = None
        external = {"submit_notification", "send_follow_up", "submit_document", "pay", "close_account", "elect_option"}
        counts = {
            "actions": len([r for r in receipts if r.actor == "runner" and r.policy.decision == "permit" and r.tool in external]),
            "open_decisions": len([d for d in decisions if d["status"] == "open"]),
            "decisions": len(decisions),
            "blocked": len([r for r in receipts if r.policy.decision == "forbid"]),
        }
        return {"estate": est, "clock": store.get_clock(), "tasks": tasks, "decisions": decisions, "events": events,
                "receipts": recent, "counts": counts, "chain": {"ok": ok, "count": len(receipts)}, "metrics": metrics}

    @app.post("/api/decisions/{decision_id}/{action}")
    def decide(decision_id: str, action: str, option: str = Form(default="")):
        store = store_factory()
        if action not in ("approve", "deny", "edit"):
            return JSONResponse({"ok": False, "error": "unknown action"}, status_code=400)
        return resolve(store, decision_id, action, option or None, by="maya")

    return app
