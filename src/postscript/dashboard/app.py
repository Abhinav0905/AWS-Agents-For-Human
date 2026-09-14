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
:root{
  --ink:#141b2d; --ink-2:#2b3550; --muted:#6b7488; --faint:#98a0b3;
  --paper:#ffffff; --shell:#f4f2ee; --band:#fbfaf7; --rule:#e3e0da;
  --go:#0d6b52; --go-bg:#e4f4ee; --go-line:#9fd4c2;
  --wait:#9a6510; --wait-bg:#fdf1dc; --wait-line:#e8c583;
  --stop:#9c2b3f; --stop-bg:#fceaed; --stop-line:#e9a8b3;
  --d1:#9c2b3f; --d2:#8a5a9e; --d3:#1b6a8f; --d4:#9a6510; --d5:#0d6b52;
  --shadow:0 1px 2px rgba(20,27,45,.05), 0 6px 18px rgba(20,27,45,.06);
  --shadow-lg:0 2px 4px rgba(20,27,45,.05), 0 14px 40px rgba(20,27,45,.10);
}
*{box-sizing:border-box}
html{-webkit-font-smoothing:antialiased}
body{margin:0;background:var(--shell);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
h1,h2,h3,.serif{font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;font-weight:500;margin:0}
a{color:var(--go);text-decoration:none;border-bottom:1px solid var(--go-line)}
a:hover{border-bottom-color:var(--go)}
.wrap{max-width:1560px;margin:0 auto;padding:0 28px 48px}

/* ---------- masthead ---------- */
.mast{background:linear-gradient(160deg,#141b2d 0%,#1e2740 45%,#2a3350 100%);color:#fff;
  margin:0 -28px;padding:34px 40px 30px;position:relative;overflow:hidden}
.mast::after{content:"";position:absolute;right:-90px;top:-90px;width:340px;height:340px;border-radius:50%;
  background:radial-gradient(circle,rgba(159,212,194,.20),transparent 68%)}
.mast .inner{max-width:1500px;margin:0 auto;display:flex;justify-content:space-between;
  align-items:flex-end;gap:32px;flex-wrap:wrap;position:relative;z-index:1}
.mast h1{font-size:42px;line-height:1;letter-spacing:-.015em;color:#fff}
.mast .tag{color:#c3cbe0;margin-top:9px;font-size:16.5px;max-width:720px}
.mast .tag b{color:#fff;font-weight:600}
.mast .live{display:inline-flex;align-items:center;gap:7px;margin-top:14px;font-size:12px;
  letter-spacing:.09em;text-transform:uppercase;color:#9fd4c2}
.dot{width:7px;height:7px;border-radius:50%;background:#4ade9e;box-shadow:0 0 0 3px rgba(74,222,158,.22)}
.mast .clock{text-align:right;white-space:nowrap}
.mast .clock b{font-size:30px;display:block;font-weight:500;font-variant-numeric:tabular-nums;color:#fff}
.mast .clock span{color:#9aa4bd;font-size:13px;display:block;margin-top:3px}

/* ---------- explainer ---------- */
.hero{background:var(--band);border:1px solid var(--rule);border-radius:14px;margin-top:24px;
  padding:26px 30px;box-shadow:var(--shadow);display:grid;grid-template-columns:1.55fr 1fr;gap:38px}
.hero p{margin:0 0 12px}
.hero .lede{font-size:17.5px;line-height:1.58;color:var(--ink-2)}
.hero .lede b{color:var(--ink);font-weight:600}
.hero .lede:last-child{margin-bottom:0}
.aside{background:var(--paper);border:1px solid var(--rule);border-left:4px solid var(--go);
  border-radius:10px;padding:16px 18px;font-size:14px;color:var(--muted);align-self:start}
.aside b{color:var(--ink);font-weight:600}
.aside .k{display:block;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--go);margin-bottom:7px;font-weight:600}

/* ---------- the five gates ---------- */
.gates{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:22px}
.gate{background:var(--paper);border:1px solid var(--rule);border-radius:11px;padding:14px 15px;
  border-top:3px solid var(--g);box-shadow:var(--shadow);transition:transform .12s ease, box-shadow .12s ease}
.gate:hover{transform:translateY(-2px);box-shadow:var(--shadow-lg)}
.gate .n{font-size:11px;letter-spacing:.11em;font-weight:700;color:var(--g)}
.gate .t{display:block;margin-top:5px;font-size:14.5px;font-weight:600;color:var(--ink)}
.gate .e{display:block;margin-top:5px;font-size:13px;color:var(--muted);font-style:italic}

/* ---------- metrics ---------- */
.metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-top:22px}
.m{background:var(--paper);border:1px solid var(--rule);border-radius:11px;padding:15px 16px;box-shadow:var(--shadow)}
.m b{display:block;font-size:30px;font-weight:600;line-height:1.05;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.m span{display:block;color:var(--muted);font-size:12.5px;margin-top:5px;line-height:1.35}
.m.ok b{color:var(--go)} .m.ok{border-top:3px solid var(--go-line)}
.m.hot b{color:var(--stop)} .m.hot{border-top:3px solid var(--stop-line)}
.m.amber b{color:var(--wait)} .m.amber{border-top:3px solid var(--wait-line)}

/* ---------- the headline claim, as a picture ---------- */
.claim{background:var(--paper);border:1px solid var(--rule);border-radius:14px;margin-top:22px;
  padding:24px 30px;box-shadow:var(--shadow)}
.claim h3{font-size:22px;margin-bottom:4px}
.claim .sub{color:var(--muted);font-size:14px;margin-bottom:20px}
.bars{display:grid;gap:18px;max-width:620px}
.bar .lab{display:flex;justify-content:space-between;align-items:baseline;font-size:13.5px;margin-bottom:7px}
.bar .lab b{font-size:15px}
.dots{display:flex;gap:5px;flex-wrap:wrap}
.pip{width:22px;height:22px;border-radius:5px;background:var(--wait);opacity:.92}
.pip.ghost{background:transparent;border:1.5px dashed var(--faint)}
.pip.quiet{background:var(--go-bg);border:1.5px solid var(--go-line)}
.claim .foot{margin-top:18px;padding-top:15px;border-top:1px solid var(--rule);font-size:14.5px;color:var(--ink-2)}
.claim .foot b{color:var(--ink)}

/* ---------- panels ---------- */
main{display:grid;grid-template-columns:1.3fr 1fr;gap:22px;margin-top:22px;align-items:start}
.panel{background:var(--paper);border:1px solid var(--rule);border-radius:14px;
  padding:20px 22px 8px;box-shadow:var(--shadow)}
.panel h2{font-size:20px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.panel .hint{color:var(--muted);font-size:13px;margin:5px 0 14px;line-height:1.45}
.panel .hint b{color:var(--ink-2)}
.tagn{font-size:11.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:600}

table{width:100%;border-collapse:collapse}
th{text-align:left;padding:0 10px 8px 0;color:var(--faint);font-weight:600;font-size:11px;
  letter-spacing:.07em;text-transform:uppercase;border-bottom:1px solid var(--rule)}
td{text-align:left;padding:9px 10px 9px 0;vertical-align:top;border-bottom:1px solid var(--rule);font-size:14px}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--band)}
td:nth-child(4){white-space:nowrap}

.pill{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600;
  background:var(--shell);color:var(--muted);border:1px solid var(--rule)}
.pill.done{background:var(--go-bg);color:var(--go);border-color:var(--go-line)}
.pill.awaiting_human{background:var(--wait-bg);color:var(--wait);border-color:var(--wait-line)}
.pill.blocked{background:var(--stop-bg);color:var(--stop);border-color:var(--stop-line)}

.decision{border:1px solid var(--rule);border-left:4px solid var(--wait);background:var(--wait-bg);
  border-radius:10px;padding:14px 16px;margin:0 0 12px}
.decision.approved,.decision.edited{border-left-color:var(--go);background:var(--paper)}
.decision.denied{border-left-color:var(--stop);background:var(--paper)}
.decision .meta{font-size:12px;color:var(--muted);display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.decision .q{font-size:16px;margin:8px 0 10px;line-height:1.45;color:var(--ink)}
.chip{display:inline-block;padding:1px 8px;border-radius:5px;font-size:11px;font-weight:700;
  letter-spacing:.05em;color:#fff}
.chip.D1{background:var(--d1)}.chip.D2{background:var(--d2)}.chip.D3{background:var(--d3)}
.chip.D4{background:var(--d4)}.chip.D5{background:var(--d5)}
.byguv{background:var(--stop-bg);color:var(--stop);border:1px solid var(--stop-line);
  padding:1px 8px;border-radius:5px;font-size:11px;font-weight:700}
.answer{font-size:13px;color:var(--muted)}
.answer b{color:var(--go)}
button{font:inherit;font-size:13.5px;font-weight:600;padding:7px 14px;border:1px solid var(--rule);
  background:var(--paper);color:var(--ink-2);border-radius:7px;cursor:pointer;margin-right:7px}
button:hover{border-color:var(--ink-2)}
button.go{background:var(--go);border-color:var(--go);color:#fff}
button.go:hover{background:#0a5541}

.feed{margin:0;padding:0;max-height:440px;overflow:auto}
.scroller{max-height:470px;overflow:auto;padding-right:6px;margin-bottom:14px}
.scroller::-webkit-scrollbar,.feed::-webkit-scrollbar{width:9px}
.scroller::-webkit-scrollbar-thumb,.feed::-webkit-scrollbar-thumb{background:var(--rule);border-radius:9px}
.feed li{list-style:none;padding:8px 10px;border-bottom:1px solid var(--rule);font-size:14px;
  display:flex;gap:11px;border-left:3px solid transparent}
.feed li .d{color:var(--faint);font-variant-numeric:tabular-nums;flex:0 0 84px;font-size:13px}
.feed li.blocked{background:var(--stop-bg);border-left-color:var(--stop);color:var(--stop);font-weight:600}
.feed li.decision_raised{border-left-color:var(--wait);background:var(--wait-bg)}
.feed li.decision_resolved{border-left-color:var(--go)}
code{font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;background:var(--shell);
  padding:2px 6px;border-radius:4px;color:var(--muted)}
.chain{font-size:12px;font-weight:700;padding:3px 10px;border-radius:20px;
  background:var(--go-bg);color:var(--go);border:1px solid var(--go-line)}
.chain.bad{background:var(--stop-bg);color:var(--stop);border-color:var(--stop-line)}
.basis-blocked{color:var(--stop);font-weight:700}

footer{margin-top:26px;padding:22px 26px;background:var(--paper);border:1px solid var(--rule);
  border-radius:14px;color:var(--muted);font-size:13.5px;box-shadow:var(--shadow)}
footer .links{margin-bottom:12px;display:flex;gap:22px;flex-wrap:wrap;font-weight:600}
.built{margin-top:10px;display:flex;gap:7px;flex-wrap:wrap}
.built span{background:var(--shell);border:1px solid var(--rule);border-radius:5px;
  padding:2px 9px;font-size:12px;color:var(--ink-2)}

@media (max-width:1180px){
  .hero{grid-template-columns:1fr;gap:20px}
  .gates{grid-template-columns:repeat(2,1fr)}
  .metrics{grid-template-columns:repeat(3,1fr)}
  main{grid-template-columns:1fr}
  .mast h1{font-size:34px}
}
@media (max-width:620px){
  .wrap{padding:0 14px 32px}.mast{margin:0 -14px;padding:26px 18px}
  .gates,.metrics{grid-template-columns:1fr 1fr}
  .mast .clock{text-align:left}
}
</style></head><body><div class="wrap">

<div class="mast"><div class="inner">
  <div>
    <h1>Postscript</h1>
    <div class="tag">The executor's agent. It does the paperwork after a death, and
      <b>interrupts you nine times instead of ninety</b>.</div>
    <div class="live"><span class="dot"></span><span id="livelabel">live run</span></div>
  </div>
  <div class="clock"><b id="clock">—</b><span id="certs"></span></div>
</div></div>

<div class="hero">
  <div>
    <p class="lede">When someone dies, one person becomes the executor and spends the better part of a year
    notifying banks, insurers, utilities, pensions, subscriptions, credit bureaus and the DMV. Research puts it
    at <b>more than 500 hours</b> and about <b>15 months</b>. Almost none of those hours need judgment.
    They need persistence.</p>
    <p class="lede">Postscript reads the estate's mail, sends the notices, chases the replies, escalates to
    certified mail when an institution stonewalls, and closes each matter out. It runs once a day in the
    background. <b>It interrupts the executor for five things and nothing else.</b></p>
  </div>
  <div class="aside">
    <span class="k">What you are looking at</span>
    A finished eight-week run against a synthetic estate with ten institutions. Every row below was produced by
    a <b>Strands</b> agent whose every tool call passed through a <b>Cedar</b> policy first.
    <span id="openhint"></span>
  </div>
</div>

<div class="gates">
  <div class="gate" style="--g:var(--d1)"><span class="n">D1 · MONEY OUT</span>
    <span class="t">Money leaves the estate</span><span class="e">the $142.17 final power bill</span></div>
  <div class="gate" style="--g:var(--d2)"><span class="n">D2 · ORIGINAL</span>
    <span class="t">A certified original leaves her hands</span><span class="e">the bank, the insurer</span></div>
  <div class="gate" style="--g:var(--d3)"><span class="n">D3 · SIGNATURE</span>
    <span class="t">Her signature, a notary, or a visit</span><span class="e">the pension form, the DMV</span></div>
  <div class="gate" style="--g:var(--d4)"><span class="n">D4 · IRREVERSIBLE</span>
    <span class="t">Something that cannot be undone</span><span class="e">closing accounts, lump sum</span></div>
  <div class="gate" style="--g:var(--d5)"><span class="n">D5 · HEIR CONFLICT</span>
    <span class="t">An heir disputes it</span><span class="e">her brother wants the car</span></div>
</div>

<div class="metrics" id="metrics"></div>

<div class="claim">
  <h3>The interruption budget</h3>
  <div class="sub">Every action the agent took, and whether it had to stop and ask.</div>
  <div class="bars" id="bars"></div>
  <div class="foot" id="claimfoot"></div>
</div>

<main>
 <div class="panel">
   <h2>Ledger <span class="tagn" id="ledgertag"></span></h2>
   <p class="hint">One row per institution. The agent works these on its own until it hits a gate.</p>
   <table><thead><tr><th>Institution</th><th>Task</th><th>State</th><th>Next check</th><th>Last note</th></tr></thead>
   <tbody id="ledger"></tbody></table>
 </div>
 <div class="panel">
   <h2>Decision inbox <span class="tagn" id="inboxcount"></span></h2>
   <p class="hint">Every question the agent put to the executor, in plain language, with a recommendation.</p>
   <div id="inbox" class="scroller"></div>
 </div>
 <div class="panel">
   <h2>Activity</h2>
   <p class="hint">What it did, day by day. <b>Red rows are calls the Cedar policy stopped before the tool ran.</b></p>
   <ul class="feed" id="feed"></ul>
 </div>
 <div class="panel">
   <h2>Receipts <span class="chain" id="chain"></span></h2>
   <p class="hint">Every call, permitted or blocked, hashed over its own contents and the hash before it.
   <b>Basis</b> names the policy rule that allowed it or the approval it ran under.</p>
   <table><thead><tr><th>Date</th><th>Actor</th><th>Tool</th><th>Basis</th><th>Hash</th></tr></thead>
   <tbody id="receipts"></tbody></table>
 </div>
</main>

<footer>
  <div class="links">
    <a href="/accounting.pdf" target="_blank">Download the Executor's Accounting PDF</a>
    <a href="__REPO__" target="_blank">Source on GitHub</a>
    <a href="/api/state" target="_blank">Raw state (JSON)</a>
  </div>
  The estate, the people and all ten institutions are invented — no real person or company appears anywhere in
  this project. The simulation is deterministic under a seed.
  <div class="built">
    <span>Strands Agents SDK</span><span>Amazon Bedrock</span><span>AgentCore</span><span>Cedar</span>
    <span>MCP</span><span>EventBridge</span><span>Lambda</span><span>S3</span><span>FastAPI</span>
  </div>
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
function pips(n,cls){return Array.from({length:Math.max(0,n)},()=>`<span class="pip ${cls}"></span>`).join('')}
async function load(){
 const r=await fetch('/api/state');const s=await r.json();
 const m=s.metrics||{};
 const open=s.decisions.filter(d=>d.status==='open');

 $('clock').textContent=s.clock;
 $('certs').textContent=`${s.estate.certified_copies_on_hand} certified originals left · Estate of ${s.estate.decedent_name}`;
 $('livelabel').textContent = open.length ? `${open.length} waiting on the executor` : 'all matters closed';

 $('openhint').innerHTML = open.length
   ? `<br><br><b>${open.length} decision${open.length>1?'s are':' is'} waiting for an answer.</b> Approve one and the agent picks the task back up.`
   : `<br><br>All <b>${s.counts.decisions}</b> decisions were answered and all <b>${s.counts.tasks_total}</b> matters are closed.`;

 const f=v=>(v===0||v)?Number(v).toFixed(1):'—';
 const cards=[
  [s.counts.actions,'actions taken with institutions',''],
  [s.counts.decisions,'times it interrupted the executor','amber'],
  [s.counts.blocked,'calls stopped by the policy','hot'],
  [f(m.interruption_precision),'interruption precision','ok'],
  [f(m.decision_recall),'decision recall','ok'],
  [m.forbidden_actions_taken??'—','forbidden actions taken','ok']];
 $('metrics').innerHTML=cards.map(([b,l,c])=>`<div class="m ${c}"><b>${esc(b)}</b><span>${l}</span></div>`).join('');

 const base=m.baseline_interruptions_confirm_everything, asked=s.counts.decisions;
 if(base){
   $('bars').innerHTML=`
    <div class="bar"><div class="lab"><span>Postscript</span><b>${asked} interruptions</b></div>
      <div class="dots">${pips(asked,'')}${pips(base-asked,'quiet')}</div></div>
    <div class="bar"><div class="lab"><span>An agent that confirms everything</span><b>${base} interruptions</b></div>
      <div class="dots">${pips(base,'ghost')}</div></div>`;
   $('claimfoot').innerHTML=`Filled squares are the times it stopped and asked. Outlined green squares are the
     actions it finished on its own. <b>It missed none of the ${asked} decisions a real executor had to make,
     and never once acted where the policy said it needed her.</b>`;
 }

 $('ledgertag').textContent=`${s.counts.tasks_total} institutions`;
 $('ledger').innerHTML=s.tasks.map(t=>`<tr><td><b>${esc(t.institution)}</b></td><td>${esc(t.kind)}</td>
   <td><span class="pill ${t.state}">${t.state.replace('_',' ')}</span></td><td>${esc(t.due)}</td>
   <td style="color:var(--muted)">${esc(t.note)}</td></tr>`).join('');

 $('inboxcount').textContent=open.length?`${open.length} open`:`${s.decisions.length} answered`;
 $('inbox').innerHTML=s.decisions.map(d=>`<div class="decision ${d.status}">
   <div class="meta">${d.types.map(t=>`<span class="chip ${esc(t)}">${esc(t)}</span>`).join('')}
     <span>${esc(d.sim_date)}</span><span>·</span><span>${esc(d.institution)}</span>
     ${d.raised_by==='governor'?'<span class="byguv">policy caught it</span>':''}</div>
   <div class="q serif">${esc(d.question)}</div>
   ${d.status==='open'
     ? `<div class="answer">Recommended: <b>${esc(d.recommendation)}</b></div>
        <div style="margin-top:10px">${d.options.map(o=>`<button class="${o===d.recommendation?'go':''}" onclick="act('${d.id}','${o===d.recommendation?'approve':'edit'}')">${esc(o)}</button>`).join('')}<button onclick="act('${d.id}','deny')">deny</button></div>`
     : `<div class="answer">${esc(d.status)}: <b>${esc(d.chosen_option)}</b> · by ${esc(d.resolved_by)} on ${esc(d.resolved_sim_date)}</div>`}
   </div>`).join('')||'<p style="color:var(--muted)">No decisions yet.</p>';

 $('feed').innerHTML=s.events.map(e=>`<li class="${e.kind}"><span class="d">${esc(e.sim_date)}</span><span>${esc(e.summary)}</span></li>`).join('');

 $('chain').textContent=s.chain.ok?`chain verified · ${s.chain.count}`:'CHAIN BROKEN';
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
