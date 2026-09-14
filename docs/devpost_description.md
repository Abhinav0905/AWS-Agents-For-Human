# Postscript: the executor's agent

## What it does

When someone dies, one person becomes the executor and spends the better part of a year notifying banks,
insurers, utilities, pensions, subscriptions, credit bureaus and the DMV. Each one wants different documents.
Some want an original certified death certificate and will not take a copy. Some want a notary. Some ignore the
first two letters.

Postscript does that work in the background. It reads the estate's mail, builds a notification ledger, sends the
notices, tracks the replies, follows up, escalates to certified mail when an institution stonewalls, and closes
each matter out. It runs on a daily tick. There is no app to open.

It interrupts the executor for exactly five kinds of decision: money leaving the estate, an original document
leaving her hands, anything needing her signature or a notary, anything irreversible, and any point where an
heir disputes what is happening.

## Who it is for

The executor. Usually an adult child, usually grieving, usually with a full-time job. Empathy's research
reports more than 500 hours of administrative work after a death, an average of $12,616 out of pocket, and close
to 60% of executors with full-time jobs struggling to keep up at work.

## How it works

A Strands `Agent` runs one task per invocation against a ledger. Every tool call it proposes passes through an
interruption governor: a Strands intervention wrapping the vended `CedarAuthorization` handler, evaluating a
Cedar policy that has three permit rules and denies everything else by default. Permitted calls reach ten
institutions over MCP. Denied calls become a plain-language question in the executor's inbox, and her answer
mints a single-use approval token on that task, which the governor consumes after the one call it authorizes.

A hook on every tool call writes an append-only receipt, hashed over its own contents and the hash before it.
Blocked calls get receipts too. The chain renders as an Executor's Accounting PDF with a verification stamp and
a schedule of every action, because an executor has a legal duty to account for what they did.

Intake uses Strands structured output per document, including vision on scanned pages. The runner uses a
sliding-window conversation manager. Deployment is AgentCore Runtime with an EventBridge Scheduler tick, the
ledger in S3, Bedrock for the model, and AgentCore Observability for the traces.

## The measured claim

Eight simulated weeks over ten institutions, scored against a ground-truth list of the decisions a real
executor would have to make: 19 actions taken, 9 interruptions raised, interruption precision 1.0, decision
recall 1.0, zero forbidden actions, zero missed deadlines, 10 of 10 matters closed, 136 receipts with the chain
verified. An agent that confirms everything would have asked 19 times.

## What is synthetic

The estate, the people and all ten institutions are invented, and the whole simulation is deterministic under a
seed. The agent does not know they are simulated; it reaches them through an MCP server the same way it would
reach real institution APIs.

## Built with

Strands Agents SDK, Amazon Bedrock (Claude), Amazon Bedrock AgentCore Runtime and Observability, Cedar,
Model Context Protocol, EventBridge Scheduler, Lambda, S3, FastAPI, ReportLab, Python.
