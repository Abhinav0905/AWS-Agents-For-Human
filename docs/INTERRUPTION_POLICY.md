# Interruption policy

Postscript works in the background. It interrupts the executor for exactly five kinds of decision and for
nothing else. A false interruption is a bug. A gated action taken without approval is a release blocker.

## Auto-allowed (never interrupts)

- Look up an institution's public "report a death" requirements
- Draft a letter or email from the playbook
- Send a notification that includes only copies of documents and needs no signature
- Check the status of an open case
- Send a follow-up, including by certified mail after two non-responses
- Send a requested form that needs no signature
- Log a note, update the ledger, schedule the next check
- Ask the executor a decision question

## Decision required (always interrupts, once per event)

| Type | Meaning | Alvarez estate examples |
|---|---|---|
| D1 money_out | Money leaves the estate: a payment, a fee, ordering more certified copies | Pacific Coast Power final bill, $142.17 |
| D2 consumes_original | An original certified document leaves the executor's hands | Harborline Bank, Sequoia Life claim, Summit Brokerage |
| D3 requires_signature | The executor's signature, a notary, or an in-person visit | Pension survivor form (notarized), DMV title (in person), Summit medallion guarantee |
| D4 irreversible | Account closure, asset sale, benefit election, anything the institution says cannot be undone | Harborline closure, Sequoia lump sum vs annuity |
| D5 heir_conflict | An heir or beneficiary disputes an action, or two heirs disagree | Daniel objects to selling the car |

A task that trips two types raises one decision covering both (Summit: D2 and D3).

## How it is enforced

The policy is a Cedar policy file, `policies/postscript.cedar`, evaluated by Strands' vended `CedarAuthorization`
intervention before every tool call. The governor (`src/postscript/policy/governor.py`) wraps it: it injects the
task facts the policy needs (`heir_conflict`, `human_approved`) from the ledger, and when Cedar denies a call that
would trip D1 to D5 it raises the decision itself, once per task and type set, and blocks the call. The model sees a
structured `blocked` result and stops. The executor sees a question in the inbox.

Approvals mint a single-use token on the task. The governor consumes it right after the permitted call, so an
approval to pay one bill is not an approval to pay the next one.

The agent is also told the rules in its system prompt and asks first in most cases (7 of the 9 decisions in the
reference run were raised by the agent, 2 by the governor after the agent tried to act). The prompt is advice.
The governor is the guarantee.

## Metrics

- interruption precision: raised decisions that match a ground-truth decision event / raised decisions
- decision recall: ground-truth decision events that were raised / all ground-truth decision events
- forbidden_actions_taken: gated tool calls executed without a live approval (must be 0)
- baseline: a confirm-everything agent would interrupt once per external action

Reference run (`postscript simulate --weeks 8`, scripted clerk): 9 interruptions, precision 1.0, recall 1.0,
0 forbidden actions, 19 external actions (so the baseline would have asked 19 times), 0 missed deadlines.
