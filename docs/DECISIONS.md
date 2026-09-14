# Decisions log

## Strands capability check (strands-agents 1.55.1, strands-agents-tools 0.8.8, mcp 2.1.1, cedarpy 4)

| Capability | Present | Used as |
|---|---|---|
| `Agent(model, tools, hooks, interventions, session_manager, state, conversation_manager)` | yes | `agents/runner.py` |
| Interventions API (`InterventionHandler`, `Proceed`, `Deny`, `Confirm`, `Guide`, `Transform`) | yes | `policy/governor.py` |
| Vended `CedarAuthorization` intervention (`strands.vended_interventions.cedar`) | yes | wrapped by the governor |
| Vended `HumanInTheLoop` intervention, `Confirm` interrupt/resume | yes | not used; see below |
| Hooks `BeforeToolCallEvent` (`cancel_tool`), `AfterToolCallEvent` (`cancel_message`, `result`) | yes | `receipts/hooks.py` |
| Structured output via `agent(prompt, structured_output_model=...)` | yes | `agents/intake.py` |
| `MCPClient` (stdio and streamable HTTP), `tool_filters`, `call_tool_sync` | yes | `simulate.py`, `infra/agentcore/app.py` |
| `SlidingWindowConversationManager` | yes | runner |
| `FileSessionManager`, AgentCore Memory session manager (`bedrock-agentcore[strands-agents]`) | yes | optional, `POSTSCRIPT_MEMORY_ID` |
| `GoalLoop` plugin (`strands.vended_plugins.goal`) | yes | not used; one task per invocation ends on a ledger update |
| `strands.telemetry.StrandsTelemetry` OTLP exporter | yes | `infra/agentcore/app.py` when `OTEL_EXPORTER_OTLP_ENDPOINT` is set |
| Custom `Model` provider (`stream`, `structured_output`, `get_config`, `update_config`) | yes | `agents/models.py` ScriptedModel |

## Choices

1. Handoff by ledger state, not by interrupt/resume. Strands can pause an agent on `Confirm` and resume it later
   with the human's answer. A tick runs once a day as a stateless invocation and an executor may take days to
   answer, so a Decision row plus a single-use approval token is the durable, auditable equivalent. The approval
   itself becomes a receipt.
2. The governor raises decisions too. If the model tries a gated action (the scripted clerk tries to pay the final
   bill and to close the bank accounts), Cedar denies it and the governor creates the decision. The prompt says
   ask first; the governor makes sure the executor is asked exactly once either way.
3. Cedar has no floating point. `pay` takes `amount_cents: int`. Packets declare `includes_original` and
   `signature_kind` as top-level arguments so the policy can read them without walking arrays.
4. mcp 2.x renamed `FastMCP` to `MCPServer`; list results arrive as one text block per item. The server imports
   both names; the clerk, the receipts and the harness parse multi-block results.
5. A scripted `Model` for offline runs. It is a rule-based clerk behind the Strands `Model` interface, so tests
   and the demo exercise the real agent loop, tools, MCP, hooks and Cedar without a model call. Set
   `POSTSCRIPT_MODEL=bedrock` for Claude. The three PNG scans in the dataset are read only in Bedrock mode.
6. Ledger durability in aws mode is a SQLite file pulled from and pushed to S3 around each invocation
   (`store_sync.py`). A daily tick is a single writer. DynamoDB is the production path; the store interface is
   already shaped for it.
7. Intake merges duplicates by institution name slug plus account last four. Institution ids in the ledger are
   name slugs; the gateway's ids are matched by name at first contact and by `case_ref` afterwards.

## Verified in this build

- `pytest`: 24 tests, including an 8-week end-to-end run through Strands, Cedar and MCP (about 3 seconds).
- Reference metrics: 9 interruptions, precision 1.0, recall 1.0, 0 forbidden actions, 136 receipts, chain verified,
  10/10 tasks done in 21 simulated days, certificates 5 to 2.

## Not verified in this build (no AWS access from the build sandbox)

- `agentcore launch`, the Lambda tick, S3 ledger sync, AgentCore Memory, OTLP export. The code paths exist and
  import cleanly; docs/DEPLOY.md lists the exact commands and what to check.
- Bedrock runs. The prompts are written for Claude; the scripted clerk follows the same rules.

## Reference run, regenerated at package time

```
Simulated 8.0 weeks (2026-03-09 to 2026-05-04)
Actions taken by the agent        19   (autonomous 11, with approval 8)
Interruptions raised               9   (agent 7, governor 2)
Interruption precision           1.0
Decision recall                  1.0
Forbidden actions taken            0
Blocked by policy                  2
Confirm-everything baseline       19 interruptions
Tasks done / total                10 / 10
Missed deadlines                   0
Days to settle everything         21
Certified originals left           2   (started with 5)
Receipts in chain                136   chain verified: True
```

The nine decisions, in the order they were raised: Harborline D2, Summit D2+D3, DMV D3 (all day 1, the agent
asking before it acts), Pacific Coast D1 (day 3, the governor blocking a payment the agent attempted), Sequoia
D2 (day 5), Pension D3 (day 6), Harborline D4 (day 7, the governor blocking an attempted closure), Sequoia D4
(day 13), DMV D5 (day 19, after the heir objects).
