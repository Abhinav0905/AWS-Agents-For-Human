# Postscript

**The executor's agent. It does the paperwork after a death, and interrupts you nine times instead of ninety.**

---

## Inspiration

My mother was the executor of my grandfather's estate. What I remember is not the grief. It is the phone calls.

A year of them. The bank would not take a photocopy of the death certificate, only an original. Each original
costs money and you only get so many. The gym kept billing him and kept saying it never got the cancellation
letter. Somewhere around month nine, my uncle decided he wanted the car.

Almost none of that work needed judgment. It needed someone who would not give up.

That is a background agent. So I built one.

---

## What it does

Postscript reads the estate's mail, works out who needs to be told, and then tells them.

It sends the notices. It tracks the replies. It follows up. When an institution ignores two letters, it
escalates to certified mail. It closes each matter out and writes down what it did.

It runs once a day. There is no app to open.

It interrupts the executor for five things:

| | |
|---|---|
| Money leaves the estate | the $142.17 final power bill |
| An original certificate leaves her hands | the bank, the insurer, the brokerage |
| She has to sign, notarize, or show up | the pension form, the DMV title |
| Something cannot be undone | closing accounts, lump sum or annuity |
| An heir disagrees | her brother does not want to sell the car |

Everything else it just does.

---

## Who it is for

The executor. Usually an adult child. Usually grieving. Usually holding down a job at the same time.

Empathy's research puts it at more than 500 hours of admin after a death, $12,616 out of pocket, and about 15
months to finish. Close to 60% of executors with full-time jobs said they struggled to keep up at work.

---

## The number I care about

Eight simulated weeks. Ten institutions.

```
Actions taken                    19
Interruptions raised              9
Interruption precision          1.0
Decision recall                 1.0
Forbidden actions taken           0
Tasks closed                 10 / 10
Receipts in chain               136   chain verified
```

An agent that asks permission for everything would have asked 19 times. Postscript asked 9.

It did not miss a single one of the nine decisions a real executor would have had to make. And it never once
acted where the policy said it needed her.

---

## How it works

A Strands `Agent` runs one task per invocation against a ledger.

Every tool call it wants to make goes through a governor first. The governor is a Strands intervention wrapping
the vended `CedarAuthorization` handler. Cedar denies by default, so the whole policy is three permit rules:
clerical work is fine unless an heir has objected; a packet is clerical only if it is copies and needs no
signature; money, closures, elections and originals need a live approval on that task.

Calls that pass reach ten institutions over MCP. Calls that fail become a plain-language question in the
executor's inbox. Her answer mints a single-use token, and the governor spends it on the one call it was for.
Approval to pay one bill is not approval to pay the next one.

**The policy is not in the prompt.** The prompt asks the agent to behave, and mostly it does. But a prompt is
advice. In the reference run the agent asked first 7 times out of 9. Twice it tried to act anyway:

```
2026-03-11  pay              BLOCKED gate:D1   -> turned into a question
2026-03-15  close_account    BLOCKED gate:D4   -> turned into a question
```

Cedar stopped the call before the tool ran.

---

## Receipts

An executor has a legal duty to account for what they did with the estate.

So every tool call, every call the policy blocked, and every answer the executor gave becomes a record. Each
one is hashed over its own contents and the hash before it. Change any record and the chain breaks.

They render into an Executor's Accounting PDF: a verification stamp, the decisions and who answered them, the
originals consumed, and a schedule of all 136 actions. Every row names the rule that allowed it or the approval
it ran under.

```
$ postscript verify-chain
OK 136 receipts verified
```

It is a document you could hand a probate clerk.

---

## How I built it

Strands Agents SDK throughout: `Agent` with tools, hooks and interventions, `InterventionHandler` with `Deny`
and `Proceed`, the vended `CedarAuthorization` with a context enricher, a `HookProvider` on
`AfterToolCallEvent` for the receipts, `@tool` functions closed over the ledger, `MCPClient` over stdio and
streamable HTTP, structured output for intake, `SlidingWindowConversationManager`, `BedrockModel`, and a custom
`Model` provider.

The ten institutions are an MCP server. The agent talks to them the way it would talk to real institution APIs.
It has no idea they are simulated.

On AWS: AgentCore Runtime hosts one entrypoint, EventBridge Scheduler fires a Lambda that calls it daily, the
ledger sits in S3 between invocations, Bedrock serves Claude, and AgentCore Observability collects the traces.

---

## Challenges

**Cedar has no floating point.** So `pay` takes `amount_cents` as an integer.

**The Cedar resource is fixed.** Task facts have to arrive through the context enricher, not the resource.

**An MCP tool returning a list comes back as one text block per element**, not one block. That cost me an hour.

**The hardest part was not the agent. It was deciding what it must not do.** Writing the interruption policy
took longer than writing the code that enforces it.

---

## What I'm proud of

That it runs with no AWS account and no model calls, and still exercises everything.

`POSTSCRIPT_MODEL=scripted` is a rule-based clerk behind the Strands `Model` interface. The tools, the MCP
calls, the hooks, the interventions and Cedar all run exactly as they would with Claude. So the demo is
deterministic, the tests are offline, and the numbers reproduce on any machine.

Also: it tells you what it could not read. Offline it says which scans need a vision model. On Bedrock it reads
them and names the one it threw out as a marketing flyer. When it does not know, it says so, on the record.

---

## What's next

Real institutions instead of simulated ones, starting with the ones that already have APIs.

DynamoDB instead of the SQLite-in-S3 shortcut.

And the thing I actually want: hand the accounting PDF to a probate clerk and find out what is missing.

---

## Built with

`strands-agents` · `amazon-bedrock` · `bedrock-agentcore` · `cedar` · `mcp` · `eventbridge` · `lambda` · `s3` ·
`python` · `fastapi` · `pydantic` · `reportlab` · `sqlite`

---

## Try it

**Live demo:** _<paste your Render URL here>_

**Code:** https://github.com/Abhinav0905/AWS-Agents-For-Human

```bash
git clone https://github.com/Abhinav0905/AWS-Agents-For-Human.git
cd AWS-Agents-For-Human
pip install -e ".[dev]"
python scripts/make_dataset.py
postscript intake
postscript simulate --weeks 8
postscript accounting
postscript dashboard
```

No AWS account needed. Eight weeks runs in about two seconds.

---

## A note on the data

Robert Alvarez, Maya, Daniel and all ten institutions are invented. Every document in `data/estate_alvarez/`
is synthetic. No real person or company appears anywhere in this project.
