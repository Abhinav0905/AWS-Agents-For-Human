# Agents for Humans: I built an agent for estate executors, and the interesting part is the nine times it stopped

*Draft for builder.aws.com. Title must contain "Agents for Humans". Published before the submission deadline.*

---

My mother was the executor of my grandfather's estate. What I remember is not the grief, it is the phone calls.
A year of them. The bank would not accept a photocopy of the death certificate, only an original, and each
original costs money and there are only so many. The gym kept billing and kept saying it had no record of the
cancellation letter. Somewhere in month nine, my uncle decided he wanted the car.

Almost none of that work needed judgment. It needed someone who would not give up. That is the shape of a
background agent, so for the AWS Agents for Humans hackathon I built one and called it Postscript.

## The design problem is not autonomy, it is restraint

An agent that handles estate paperwork is easy to describe and frightening to build. The failure mode is not
that it does nothing. It is that it mails your last original death certificate to a bank, or closes an account
that cannot be reopened, or pays a bill that turns out to be fraudulent, and does it while you are at a funeral.

So the first thing I wrote was not the agent. It was the list of things it is not allowed to do alone:

- **D1** money leaves the estate
- **D2** an original certified document leaves the executor's hands
- **D3** anything needing her signature, a notary, or an in-person visit
- **D4** anything irreversible: a closure, a sale, a benefit election
- **D5** any point where an heir disputes what is happening

Everything else the agent does on its own and writes down. That list became the product, the metric and the
demo.

## A prompt is advice. Cedar is the rule.

I did put the policy in the system prompt, and the agent mostly follows it. Mostly is not a feature you can
ship to a grieving person.

Strands has an interventions API, and a vended `CedarAuthorization` handler that evaluates a Cedar policy before
every tool call. Cedar denies by default, so the whole policy is three permit rules:

```cedar
// Sending a packet is clerical only when it carries copies and needs no signature.
// D2: includes_original means a certified original leaves her hands.
// D3: any signature_kind other than "none" means she must sign, notarize or appear.
permit (
  principal == Agent::"runner",
  action in [Action::"submit_notification", Action::"submit_document"],
  resource
)
unless {
  context.session.heir_conflict ||
  !(context.input has includes_original) ||
  !(context.input has signature_kind) ||
  context.input.includes_original == true ||
  context.input.signature_kind != "none"
};
```

I wrapped the vended handler in my own intervention. When Cedar denies a call that trips one of the five gates,
my governor raises the decision itself, once per task, and returns a `Deny` whose reason is a JSON blob telling
the model to stop working that task. The model reads the refusal as its tool result and moves on.

The nice consequence is that the agent's good behaviour and the guarantee are separate. In the reference run the
agent asked first seven times out of nine. Twice it just tried to act, and the gate caught it:

```
2026-03-11  pay            BLOCKED gate:D1  -> decision raised, task parked
2026-03-15  close_account  BLOCKED gate:D4  -> decision raised, task parked
```

Approving a decision mints a single-use token on that task, and the governor consumes it right after the one
call it authorizes. Approval to pay one bill is not approval to pay the next.

## Proof, because an executor owes an accounting

Executors have a legal duty to account for what they did with the estate. That duty turned into the second half
of the architecture.

A Strands hook on `AfterToolCallEvent` writes a receipt for every tool call, including the blocked ones, hashed
over its own canonical JSON and the hash before it, append-only, with the policy rule or approval id that let it
happen. `postscript accounting` renders the chain into a PDF with a verification stamp, the decisions with who
answered and when, the originals consumed, and a schedule of all 136 actions.

```
$ postscript verify-chain
OK 136 receipts verified
```

## The number

I built a synthetic estate: ten institutions, each with its own behaviour script, behind an MCP server, so the
agent reaches them the same way it would reach real institution APIs. It has no idea they are simulated. One of
them denies having any record of the cancellation twice and only folds to certified mail, because that actually
happened to my mother.

Then I wrote down the nine decisions a real executor would have to make, and scored the agent against them:

```
Actions taken                   19
Interruptions raised             9
Interruption precision         1.0
Decision recall                1.0
Forbidden actions taken          0
Confirm-everything baseline     19 interruptions
```

Precision and recall on interruptions turned out to be the most useful thing in the project. They make
"interrupt only when it matters" a number that can regress, and `simulate` exits non-zero if recall drops or a
forbidden action slips through.

## Four things that cost me time

**Cedar has no float type.** A float anywhere in the context makes the request fail to parse, and the handler
returns a deny with a schema error that looks nothing like the real cause. Payments take integer cents now.

**The Cedar resource is fixed.** The vended handler always builds `Resource::"agent"`, so per-resource
attributes are not available. Task facts have to arrive through the `context_enricher` and the policy reads them
off `context.session`.

**mcp 2.x renamed `FastMCP` to `MCPServer`.** The error message is good, which is more than I deserved.

**An MCP tool returning a list gives you one text block per element**, not one block holding a list. I parsed
the first block, got one institution out of ten, and spent a while blaming the model.

## The offline model provider was the best decision I made

I implemented the Strands `Model` interface with a rule-based clerk. It emits Bedrock-shaped stream events and
picks tool calls from the same context a real model would read. That means the tests, CI and the demo run the
real agent loop, the real tools, the real MCP client, the real hooks and the real Cedar policy, with no model
call, in about three seconds and with zero flakiness. Swapping to Claude on Bedrock is one environment variable.

If you are building anything with an authorization layer, do this. Most of what you want to test is not the
model.

## What I would do next

Real institutions. The tedious, unglamorous, genuinely useful version of this is a library of bereavement
requirements that someone maintains, the way tax software maintains forms. The agent part is the easy half.

Repo, architecture diagram and the accounting PDF are in the submission. It is MIT licensed. The estate, the
people and every institution in it are invented.
