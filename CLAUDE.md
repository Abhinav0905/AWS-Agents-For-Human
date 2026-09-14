# CLAUDE.md

Working notes for anyone, human or model, picking this repo up.

## Purpose

Postscript is a background agent for estate executors. When someone dies, the executor spends months notifying
banks, insurers, utilities, pensions, subscriptions, credit bureaus and agencies. Each wants different
documents, some want originals, some want a notary, some ignore the first two letters. Postscript reads the
estate's mail, builds a notification ledger, sends the notices, chases the replies, escalates, and closes each
matter out, on a daily tick, in the background.

It interrupts the executor for five kinds of decision and nothing else. Every tool call becomes a hash-chained
receipt, and the receipts render as an Executor's Accounting PDF, because an executor has a legal duty to
account for what they did.

## Architecture in one screen

Estate mail -> intake agent (structured output per document) -> ledger. A daily tick drives the runner agent,
one Strands `Agent` per task per tick. Every tool call passes through `PostscriptGovernor`, a Strands
intervention wrapping the vended `CedarAuthorization`. Permitted calls reach the institution gateway over MCP.
Denied calls raise a Decision to the inbox, which mints a single-use approval token back onto the task.
`ReceiptHooks` records every call, permitted or blocked, into the chain. `local` mode is SQLite plus a stdio MCP
server; `aws` mode is the same code on AgentCore Runtime with the ledger in S3 and the gateway over HTTP.

## The interruption policy

Auto-allowed, never interrupts: read an institution's requirements, draft a letter, send a packet of copies
needing no signature, check status, follow up (certified after two non-responses), send a requested unsigned
form, log a note, update the ledger, ask the executor a question.

Decision required, always interrupts, one decision per event:

- **D1 money_out** any payment or transfer from the estate
- **D2 consumes_original** an original certified document leaves the executor's hands
- **D3 requires_signature** signature, notarization, or in-person identity
- **D4 irreversible** closure, sale, election, anything that cannot be undone
- **D5 heir_conflict** an heir disputes an action

A task tripping two types raises one decision covering both. A false interruption is a bug. A gated action taken
without a live approval is a release blocker.

## Data minimization

Never store SSNs, full account numbers or certificate images. Receipt arguments are redacted before they are
written. Packets reference documents by id. Anything requiring identity verification goes to the human.

## Coding rules

Pydantic v2 everywhere. Tools are `@tool` functions with typed arguments and docstrings, because Strands hands
the docstring to the model as the tool description; write them for the model. No network calls in unit tests.
Deterministic under `POSTSCRIPT_SIM_SEED`. Every agent side effect goes through a tool. `structlog`, never
`print`. The receipts table gets INSERT only; there is no UPDATE or DELETE for it anywhere, and it should stay
that way.

## Strands rules

Model provider is `BedrockModel` with `POSTSCRIPT_MODEL_ID`, or `ScriptedModel` offline. Before using any
Strands feature, check the installed version rather than the docs, and record what you found in
`docs/DECISIONS.md`. The verified facts for 1.55.1 are already in there, including three that will cost you an
hour each if you miss them: Cedar rejects floats, the Cedar resource is fixed at `Resource::"agent"` so task
facts must arrive through the context enricher, and an MCP tool returning a list produces one text block per
element.

## local vs aws

`POSTSCRIPT_MODE=local` uses SQLite under `POSTSCRIPT_DATA_DIR` and starts the MCP gateway as a stdio
subprocess. `POSTSCRIPT_MODE=aws` pulls and pushes the ledger from `POSTSCRIPT_LEDGER_S3`, talks to the gateway
at `POSTSCRIPT_GATEWAY_URL`, and uses AgentCore Memory when `POSTSCRIPT_MEMORY_ID` is set. `POSTSCRIPT_MODEL`
is independent of both.

## Definition of done

`make simulate` runs eight simulated weeks in under three minutes and writes `out/metrics.json`; each of D1
through D5 is raised at least once and each ground-truth decision event exactly once; `forbidden_actions_taken`
is 0; `make accounting` produces a PDF whose chain verifies; the dashboard shows the run; one real tick has run
on AgentCore Runtime.
