# Deploying to AWS

Nothing here is required to run the demo. `POSTSCRIPT_MODE=local` runs the whole system with no AWS account.
This is the path to a real AgentCore deployment, which strengthens the hackathon's technical score.

## Prerequisites

1. An AWS account with Bedrock model access for a Claude inference profile in your region.
   `aws bedrock list-inference-profiles --region us-west-2` gives you the id for `POSTSCRIPT_MODEL_ID`.
   If model access is blocked account-wide, open the support case first; it is the long pole.
2. The AgentCore CLI. Install per the current AWS docs, then `agentcore --version`.
3. An S3 bucket for the ledger.
4. A budget alert. `$50` of hackathon credits is the whole budget; set the alarm at `$30`.

## One command

```bash
export AWS_REGION=us-west-2
export POSTSCRIPT_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0
export POSTSCRIPT_LEDGER_S3=s3://your-bucket/postscript/ledger.db
bash infra/deploy.sh
```

That runs `agentcore configure`, `agentcore launch`, writes the runtime ARN to `infra/outputs.json`, and
deploys `infra/scheduler.yaml`, which is the EventBridge Scheduler rule, the Lambda, and least-privilege IAM for
the daily tick.

## Smoke test

```bash
agentcore invoke '{"action": "intake"}'
agentcore invoke '{"action": "tick"}'
agentcore invoke '{"action": "state"}'
```

`state` returns the clock, the tasks, any open decisions, and the chain status. Paste the output of one real
tick into `docs/DECISIONS.md`; it is evidence for the judges.

## The gateway

The ten institutions are an MCP server. Locally it runs as a stdio subprocess. In the cloud, run it over
streamable HTTP on whatever is fastest for you (App Runner or a small Fargate task):

```bash
PORT=8080 python -m postscript.sim.server --http
```

Then set `POSTSCRIPT_GATEWAY_URL=https://your-host/mcp` at launch. If you skip this, the runtime falls back to
the stdio subprocess inside the container, which works for a demo.

## Observability

Set `OTEL_EXPORTER_OTLP_ENDPOINT` and the AgentCore Observability variables at launch. `infra/agentcore/app.py`
calls `StrandsTelemetry().setup_otlp_exporter()` when it sees them. In the trace you can watch a tool call, the
governor's permit or deny, and the receipt id on the span. One screenshot of that is worth thirty seconds of
demo video.

## Memory

Optional. Create an AgentCore Memory resource and pass `POSTSCRIPT_MEMORY_ID`; the runner will use
`AgentCoreMemorySessionManager` keyed by estate and task. The ledger stays the source of truth either way, so
losing memory never makes the agent wrong.

## Teardown

```bash
bash infra/destroy.sh
```

## Known shortcuts

The ledger is a SQLite file pulled from and pushed to S3 around each invocation. A daily tick is a single
writer, so this is safe here and simple to demo. `DynamoLedgerStore` is the production path and the store
interface is already shaped for it.
