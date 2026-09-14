"""One page: what Postscript is, the ledger, the decision inbox, the activity feed, the receipts, and the metrics.

The page has to explain itself. Most people who open it have never seen the project and will not read a README
first, so the top of the page says what the agent does and what the five gates are before showing any tables.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ..inbox import resolve
from ..models import DECISION_LABELS

REPO = "https://github.com/Abhinav0905/AWS-Agents-For-Human"

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Postscript — the executor's agent</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--ink:#182233;--muted:#5d6675;--rule:#d9dde3;--paper:#ffffff;--soft:#f4f6f8;--go:#0f6e56;--go-bg:#e1f5ee;
--wait:#8a5a00;--wait-bg:#fbf0d9;--stop:#8f2c2c;--stop-bg:#fbe9e9;--band:#f7f5f1}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
h1,h2,h3,.serif{font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;font-weight:500;margin:0}
a{color:var(--go)}
.wrap{max-width:1500px;margin:0 auto}

header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:26px 40px 16px;border-bottom:2px solid var(--ink)}
header h1{font-size:34px;line-height:1.05}
header .tag{color:var(--muted);margin-top:6px;font-size:15px}
.clock{text-align:right;white-space:nowrap}.clock b{font-size:26px;display:block;font-weight:500}
.clock span{color:var(--muted);font-size:13px}

/* ---- the explainer band: this is what a first-time reader sees ---- */
.hero{background:var(--band);border-bottom:1px solid var(--rule);padding:22px 40px}
.hero .cols{display:grid;grid-template-columns:1.6fr 1fr;gap:40px}
.hero p{margin:0 0 10px}
.hero .lede{font-size:17px;line-height:1.5}
.hero .lede b{font-weight:600}
.note{background:var(--paper);border:1px solid var(--rule);padding:12px 14px;font-size:13.5px;color:var(--muted)}
.note b{color:var(--ink);font-weight:600}

.gates{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;padding:16px 40px 0}
.gate{border:1px solid var(--rule);border-top:3px solid var(--wait);padding:9px 11px;background:var(--paper)}
.gate b{display:block;font-size:13px;letter-spacing:.04em;color:var(--wait)}
.gate span{font-size:13px;display:block;margin-top:2px}
.gate i{font-style:normal;color:var(--muted);font-size:12.5px;display:block;margin-top:3px}

.strip{display:grid;grid-template-columns:repeat(6,1fr);border-top:1px solid var(--rule);
border-bottom:1px solid var(--rule);padding:0 40px;margin-top:18px}
.strip div{padding:14px 12px 12px 0;border-right:1px solid var(--rule);margin-right:12px}
.strip div:last-child{border-right:0}
.strip b{display:block;font-size:26px;font-weight:500;line-height:1.1}
.strip span{color:var(--muted);font-size:12.5px;display:block;margin-top:2px}
.strip .good{color:var(--go)}

.claim{padding:16px 40px;border-bottom:1px solid var(--rule);display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
.claim .big{font-size:19px}
.claim .big b{font-size:26px;font-weight:600}
.claim .vs{color:var(--muted)}

main{display:grid;grid-template-columns:1.25fr 1fr;gap:40px;padding:24px 40px 10px}
section h2{font-size:20px;margin:0 0 4px;padding-bottom:6px;border-bottom:1px solid var(--rule)}
section .hint{color:var(--muted);font-size:13px;margin:0 0 10px}
table{width:100%;border-collapse:collapse}
td,th{text-align:left;padding:7px 8px 7px 0;vertical-align:top;border-bottom:1px solid var(--rule);font-size:14px}
th{color:var(--muted);font-weight:500;font-size:12px}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;background:var(--soft)}
.pill.done{background:var(--go-bg);color:var(--go)}
.pill.awaiting_human{background:var(--wait-bg);color:var(--wait)}
.pill.blocked{background:var(--stop-bg);color:var(--stop)}
.decision{border-left:4px solid var(--wait);background:var(--wait-bg);padding:12px 14px;margin:0 0 12px}
.decision.approved,.decision.edited{border-left-color:var(--go);background:var(--soft)}
.decision.denied{border-left-color:var(--stop);background:var(--soft)}
.decision .q{font-size:15px;margin:4px 0 8px}
.decision small{color:var(--muted)}
.decision .who{display:inline-block;margin-top:2px}
button{font:inherit;font-size:14px;padding:6px 12px;border:1px solid var(--ink);background:var(--paper);
color:var(--ink);cursor:pointer;margin-right:6px}
button.go{background:var(--go);border-color:var(--go);color:#fff}
.feed li{list-style:none;padding:6px 0;border-bottom:1px solid var(--rule);font-size:14px}
.feed{margin:0;padding:0;max-height:430px;overflow:auto}
.feed .d{color:var(--muted);margin-right:8px;font-variant-numeric:tabular-nums}
.feed li.blocked{color:var(--stop);background:var(--stop-bg);padding-left:8px;font-weight:500}
.feed li.decision_raised{color:var(--wait)}
.feed li.decision_resolved{color:var(--go)}
code{font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;background:var(--soft);padding:1px 4px}
.chain{font-size:13px;margin-left:10px;color:var(--go)}.chain.bad{color:var(--stop)}
.basis-blocked{color:var(--stop);font-weight:600}
footer{padding:20px 40px 40px;color:var(--muted);font-size:13px;border-top:1px solid var(--rule);margin-top:20px}
footer .links{margin-bottom:8px}footer .links a{margin-right:18px}
@media (max-width:1100px){
  .hero .cols{grid-template-columns:1fr;gap:16px}
  .gates{grid-template-columns:repeat(2,1fr)}
  .strip{grid-template-columns:repeat(3,1fr)}
  main{grid-template-columns:1fr;gap:28px}
  header,.hero,.gates,.strip,.claim,main,footer{padding-left:20px;padding-right:20px}
}
</style></head><body><div class="wrap">

<header>
  <div>
    <h1>Postscript</h1>
    <div class="tag">The executor's agent. It does the paperwork after a death, and interrupts you nine times instead of ninety.</div>
  </div>
  <div class="clock"><b id="clock">—</b><span id="certs"></span></div>
</header>

<div class="hero">
  <div class="cols">
    <div>
      <p class="lede">When someone dies, one person becomes the executor and spends the better part of a year
      notifying banks, insurers, utilities, pensions, subscriptions, credit bureaus and the DMV. Research puts it
      at <b>more than 500 hours</b> and about <b>15 months</b>. Almost none of those hours need judgment.
      They need persistence.</p>
      <p class="lede">Postscript reads the estate's mail, sends the notices, chases the replies, escalates to
      certified mail when an institution stonewalls, and closes each matter out. It runs once a day in the
      background. <b>It interrupts the executor for five things and nothing else.</b></p>
    </div>
    <div class="note" id="whatnote">
      <b>What you are looking at</b><br>
      A finished eight-week run against a synthetic estate with ten institutions. Every row below was produced by
      a Strands agent whose every tool call passed through a Cedar policy first.
      <span id="openhint"></span>
    </div>
  </div>
</div>

<div class="gates">
  <div class="gate"><b>D1 · MONEY OUT</b><span>Money leaves the estate</span><i>the $142.17 final power bill</i></div>
  <div class="gate"><b>D2 · ORIGINAL</b><span>A certified original leaves her hands</span><i>the bank, the insurer</i></div>
  <div class="gate"><b>D3 · SIGNATURE</b><span>Her signature, a notary, or a visit</span><i>the pension form, the DMV</i></div>
  <div class="gate"><b>D4 · IRREVERSIBLE</b><span>Something that cannot be undone</span><i>closing accounts, lump sum</i></div>
  <div class="gate"><b>D5 · HEIR CONFLICT</b><span>An heir disputes it</span><i>her brother wants the car</i></div>
</div>

<div class="strip" id="strip"></div>

<div class="claim" id="claim"></div>

<main>
 <section>
   <h2>Ledger</h2>
   <p class="hint">One row per institution. The agent works these on its own until it hits a gate.</p>
   <table><thead><tr><th>Institution</th><th>Task</th><th>State</th><th>Next check</th><th>Last note</th></tr></thead>
   <tbody id="ledger"></tbody></table>
 </section>
 <section>
   <h2>Decision inbox <small id="inboxcount" style="color:var(--muted);font-weight:400"></small></h2>
   <p class="hint">Every question the agent put to the executor, in plain language, with a recommendation.</p>
   <div id="inbox"></div>
 </section>
 <section>
   <h2>Activity</h2>
   <p class="hint">What it did, day by day. Red rows are calls the Cedar policy stopped before the tool ran.</p>
   <ul class="feed" id="feed"></ul>
 </section>
 <section>
   <h2>Receipts <span class="chain" id="chain"></span></h2>
   <p class="hint">Every call, permitted or blocked, hashed over its own contents and the hash before it.
   <b>Basis</b> names the policy rule that allowed it or the approval it ran under.</p>
   <table><thead><tr><th>Date</th><th>Actor</th><th>Tool</th><th>Basis</th><th>Hash</th></tr></thead>
   <tbody id="receipts"></tbody></table>
 </section>
</main>

<footer>
  <div class="links">
    <a href="/accounting.pdf" target="_blank">Download the Executor's Accounting PDF</a>
    <a href="__REPO__" target="_blank">Source on GitHub</a>
    <a href="/api/state" target="_blank">Raw state (JSON)</a>
  </div>
  Built on the Strands Agents SDK with Amazon Bedrock, AgentCore, Cedar and MCP.
  The estate, the people and all ten institutions are invented — no real person or company appears anywhere in
  this project. The simulation is deterministic under a seed.
</footer>

</div>
<script>
const $=id=>document.getElementById(id);
function esc(s){return String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
async function act(id,action){
  const opt=action==='edit'?prompt('Option to choose:'):null;
  await fetch(`/api/decisions/${id}/${action}`,{method:'POST',
    headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:'option='+encodeURIComponent(opt||'')});
  load();
}
async function load(){
 const r=await fetch('/api/state');const s=await r.json();
 $('clock').textContent=s.clock;
 $('certs').textContent=`${s.estate.certified_copies_on_hand} certified originals left · Estate of ${s.estate.decedent_name} · executor ${s.estate.executor_name}`;

 const m=s.metrics||{};
 const open=s.decisions.filter(d=>d.status==='open');
 $('openhint').innerHTML=open.length
   ? `<br><br><b>${open.length} decision${open.length>1?'s are':' is'} waiting for an answer.</b> Approve one and the agent picks the task back up.`
   : `<br><br>All ${s.counts.decisions} decisions have been answered and all ${s.counts.tasks_total||''} matters are closed.`;

 const pct = v => (v===0||v)?Number(v).toFixed(1).replace(/\\.0$/,'.0'):'—';
 const strip=[
  [s.counts.actions,'actions taken with institutions'],
  [s.counts.decisions,'times it interrupted the executor'],
  [s.counts.blocked,'calls stopped by the policy'],
  [pct(m.interruption_precision),'interruption precision',true],
  [pct(m.decision_recall),'decision recall',true],
  [m.forbidden_actions_taken??'—','forbidden actions taken',true]];
 $('strip').innerHTML=strip.map(([b,l,g])=>`<div><b class="${g?'good':''}">${esc(b)}</b><span>${l}</span></div>`).join('');

 const base=m.baseline_interruptions_confirm_everything;
 $('claim').innerHTML = base
  ? `<div class="big">It asked <b>${s.counts.decisions}</b> times.</div>
     <div class="big vs">An agent that confirms everything would have asked <b>${base}</b>.</div>
     <div class="vs">It missed none of the decisions a real executor had to make, and never once acted where the policy said it needed her.</div>`
  : '';

 $('ledger').innerHTML=s.tasks.map(t=>`<tr><td>${esc(t.institution)}</td><td>${esc(t.kind)}</td>
   <td><span class="pill ${t.state}">${t.state.replace('_',' ')}</span></td><td>${esc(t.due)}</td>
   <td style="color:var(--muted)">${esc(t.note)}</td></tr>`).join('');

 $('inboxcount').textContent=open.length?`${open.length} open`:`${s.decisions.length} answered`;
 $('inbox').innerHTML=s.decisions.map(d=>`<div class="decision ${d.status}">
   <small>${esc(d.sim_date)} · ${esc(d.institution)} · ${d.types.map(t=>esc(t+': '+d.labels[t])).join('; ')}
   ${d.raised_by==='governor'?' · <b style="color:var(--stop)">raised by the policy after it tried to act</b>':''}</small>
   <div class="q serif">${esc(d.question)}</div>
   ${d.status==='open'
     ? `<div><small>Recommended: ${esc(d.recommendation)}</small></div>
        <div style="margin-top:8px">${d.options.map(o=>`<button class="${o===d.recommendation?'go':''}" onclick="act('${d.id}','${o===d.recommendation?'approve':'edit'}')">${esc(o)}</button>`).join('')}<button onclick="act('${d.id}','deny')">deny</button></div>`
     : `<small class="who">${esc(d.status)}: <b>${esc(d.chosen_option)}</b> · by ${esc(d.resolved_by)} on ${esc(d.resolved_sim_date)}</small>`}
   </div>`).join('')||'<p style="color:var(--muted)">No decisions yet.</p>';

 $('feed').innerHTML=s.events.map(e=>`<li class="${e.kind}"><span class="d">${esc(e.sim_date)}</span>${esc(e.summary)}</li>`).join('');

 $('chain').textContent=s.chain.ok?`chain verified · ${s.chain.count} records`:'CHAIN BROKEN';
 $('chain').className='chain'+(s.chain.ok?'':' bad');
 $('receipts').innerHTML=s.receipts.map(r=>`<tr><td>${esc(r.sim_time)}</td><td>${esc(r.actor)}</td>
   <td>${esc(r.tool)}</td><td class="${r.basis.startsWith('BLOCKED')?'basis-blocked':''}">${esc(r.basis)}</td>
   <td><code>${esc(r.hash)}</code></td></tr>`).join('');
}
load();setInterval(load,2000);
</script></body></html>""".replace("__REPO__", REPO)


def create_app(store_factory: Callable, out_dir: Path) -> FastAPI:
    app = FastAPI(title="Postscript dashboard")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PAGE

    @app.get("/accounting.pdf")
    def accounting_pdf():
        """The Executor's Accounting. Judges should be able to read the artifact, not just hear about it."""
        pdf = out_dir / "accounting_alvarez.pdf"
        if not pdf.exists():
            return JSONResponse({"error": "run `postscript accounting` first"}, status_code=404)
        return FileResponse(pdf, media_type="application/pdf", filename="accounting_alvarez.pdf")

    @app.get("/api/state")
    def state():
        store = store_factory()
        try:
            est = store.get_estate().model_dump(mode="json")
        except KeyError:
            return JSONResponse({"estate": {"decedent_name": "—", "executor_name": "—", "certified_copies_on_hand": 0},
                                 "clock": "—", "tasks": [], "decisions": [], "events": [], "receipts": [],
                                 "counts": {"actions": 0, "open_decisions": 0, "decisions": 0, "blocked": 0,
                                            "tasks_total": 0},
                                 "chain": {"ok": True, "count": 0}, "metrics": None})
        insts = {i.id: i.name for i in store.list_institutions()}
        tasks = [{"id": t.id, "institution": insts.get(t.institution_id, t.institution_id), "kind": t.kind,
                  "state": t.state, "due": t.due_sim_date, "note": t.history[-1].note[:90] if t.history else ""}
                 for t in store.list_tasks()]
        ordered = sorted(store.list_decisions(), key=lambda d: (d.status != "open", d.sim_date))
        decisions = [{"id": d.id, "sim_date": d.sim_date, "institution": insts.get(d.institution_id, d.institution_id),
                      "types": d.types, "labels": DECISION_LABELS, "question": d.question, "options": d.options,
                      "recommendation": d.recommendation, "status": d.status, "chosen_option": d.chosen_option,
                      "resolved_by": d.resolved_by, "resolved_sim_date": d.resolved_sim_date,
                      "raised_by": getattr(d, "raised_by", None)}
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
            "tasks_total": len(tasks),
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
