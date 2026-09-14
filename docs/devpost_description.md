# Postscript

**The executor's agent. It does the paperwork after a death, and interrupts you nine times instead of ninety.**

🔗 **Live:** https://executors-agent.onrender.com
💻 **Code:** https://github.com/Abhinav0905/AWS-Agents-For-Human

---

## Inspiration

My mother was the executor of my grandfather's estate.

What I remember is not the grief. It's the phone calls.

A year of them. The bank wouldn't take a photocopy of the death certificate — only an original. Each original
costs money, and you only get so many. The gym kept billing him and kept saying it never got the cancellation
letter. Around month nine, my uncle decided he wanted the car.

Almost none of that needed judgment. It needed someone who wouldn't give up.

That's a background agent.

---

## What it does

Postscript reads the estate's mail and works out who needs to be told.

Then it tells them. It tracks replies. It follows up. When an institution ignores two letters, it escalates to
certified mail. It closes each matter out and writes down what it did.

It runs once a day. There's no app to open.

**It interrupts the executor for five things:**

| Gate | Trigger | Example |
|---|---|---|
| **D1** | Money leaves the estate | the $142.17 final power bill |
| **D2** | An original certificate leaves her hands | the bank, the insurer |
| **D3** | Her signature, a notary, or a visit | the pension form, the DMV |
| **D4** | Something that can't be undone | closing accounts, lump sum |
| **D5** | An heir disputes it | her brother wants the car |

Everything else it just does.

---

## Who it's for

The executor. Usually an adult child. Usually grieving. Usually holding down a job.

Research puts it at 500+ hours of admin after a death, $12,616 out of pocket, and about 15 months to finish.
Close to 60% of executors with full-time jobs said they struggled to keep up at work.

---

## The number

Eight simulated weeks. Ten institutions.

```
Actions taken                19
Interruptions raised          9
Interruption precision      1.0
Decision recall             1.0
Forbidden actions             0
Matters closed           10/10
Receipts in chain           136   chain verified
```

An agent that asks about everything would have asked **19 times**. Postscript asked **9**.

It missed none of the nine decisions a real executor had to make. And it never once acted where the policy said
it needed her.

---

## How it works

A Strands `Agent` runs one task per invocation against a ledger.

Every tool call goes through a governor first — a Strands intervention wrapping the vended
`CedarAuthorization`. Cedar denies by default, so the whole policy is three permit rules.

Calls that pass reach ten institutions over MCP. Calls that fail become a plain-language question in the
executor's inbox. Her answer mints a single-use token, and the governor spends it on the one call it was for.

Approval to pay one bill is not approval to pay the next one.

**The policy is not in the prompt.** A prompt is advice. In the reference run the agent asked first 7 times out
of 9. Twice it tried to act anyway:

```
2026-03-11  pay            BLOCKED gate:D1  ->  turned into a question
2026-03-15  close_account  BLOCKED gate:D4  ->  turned into a question
```

Cedar stopped the call before the tool ran.

---

## Receipts

An executor has a legal duty to account for what they did with the estate.

So every call, every block, and every answer becomes a record — hashed over its own contents and the hash
before it. Change one and the chain breaks.

They render into an Executor's Accounting PDF: a verification stamp, the decisions, the originals consumed, and
a schedule of all 136 actions. Every row names the rule that allowed it.

```
$ postscript verify-chain
OK 136 receipts verified
```

You could hand it to a probate clerk. [Download it from the live demo.](https://executors-agent.onrender.com/accounting.pdf)

---

## Challenges

**Cedar has no floating point.** So `pay` takes `amount_cents` as an integer.

**The Cedar resource is fixed.** Task facts have to arrive through the context enricher.

**An MCP tool returning a list comes back as one text block per element.** That cost me an hour.

**The hard part wasn't the agent. It was deciding what it must not do.** Writing the interruption policy took
longer than writing the code that enforces it.

---

## What I'm proud of

It runs with no AWS account and no model calls, and still exercises everything.

`POSTSCRIPT_MODEL=scripted` is a rule-based clerk behind the Strands `Model` interface. The tools, MCP calls,
hooks, interventions and Cedar all run exactly as they would with Claude. The demo is deterministic, the tests
are offline, and the numbers reproduce on any machine.

And it tells you what it couldn't read. Offline it names the scans it skipped. On Bedrock it reads them, and
names the one it threw out as a marketing flyer.

When it doesn't know, it says so, on the record.

---

## What's next

Real institutions, starting with the ones that already have APIs.

DynamoDB instead of the SQLite-in-S3 shortcut.

And the thing I actually want: hand the accounting PDF to a probate clerk and find out what's missing.

---

## Built with

Strands Agents SDK · Amazon Bedrock (Claude) · Bedrock AgentCore Runtime & Observability · Cedar · MCP ·
EventBridge Scheduler · Lambda · S3 · Python · FastAPI · Pydantic · ReportLab · SQLite

---

## Try it

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

_The live demo is on a free tier, so the first load can take a minute to wake up._

---

## A note on the data

Robert Alvarez, Maya, Daniel and all ten institutions are invented. Every document is synthetic. No real person
or company appears anywhere in this project.
