#!/usr/bin/env bash
# Deploy Postscript to Amazon Bedrock AgentCore Runtime and wire the daily tick.
# Prereqs: AWS CLI with credentials, the AgentCore CLI (see docs/DEPLOY.md for the current install command),
# Bedrock model access for POSTSCRIPT_MODEL_ID, and an S3 bucket for the ledger.
set -euo pipefail
: "${POSTSCRIPT_MODEL_ID:?set POSTSCRIPT_MODEL_ID to a Claude inference profile enabled in your account}"
: "${POSTSCRIPT_LEDGER_S3:?set POSTSCRIPT_LEDGER_S3 to s3://<bucket>/postscript/ledger.db}"
export AWS_REGION="${AWS_REGION:-us-west-2}"

echo "1/4 configure the runtime"
agentcore configure --entrypoint infra/agentcore/app.py --name postscript \
  --requirements-file infra/agentcore/requirements.txt --non-interactive

echo "2/4 launch (builds the container in CodeBuild and creates the runtime)"
agentcore launch \
  --env POSTSCRIPT_MODE=aws --env POSTSCRIPT_MODEL=bedrock --env POSTSCRIPT_MODEL_ID="$POSTSCRIPT_MODEL_ID" \
  --env POSTSCRIPT_LEDGER_S3="$POSTSCRIPT_LEDGER_S3" --env AWS_REGION="$AWS_REGION" \
  ${POSTSCRIPT_GATEWAY_URL:+--env POSTSCRIPT_GATEWAY_URL="$POSTSCRIPT_GATEWAY_URL"} \
  ${POSTSCRIPT_MEMORY_ID:+--env POSTSCRIPT_MEMORY_ID="$POSTSCRIPT_MEMORY_ID"}

echo "3/4 read the runtime ARN"
RUNTIME_ARN=$(agentcore status --json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("agent_arn") or d["agent"]["agent_arn"])' \
  || { echo "paste the ARN printed by agentcore launch:"; read -r RUNTIME_ARN; echo "$RUNTIME_ARN"; })
mkdir -p infra && echo "{\"agent_runtime_arn\": \"$RUNTIME_ARN\"}" > infra/outputs.json

echo "4/4 daily tick: EventBridge Scheduler -> Lambda -> runtime"
aws cloudformation deploy --stack-name postscript-tick --template-file infra/scheduler.yaml \
  --capabilities CAPABILITY_IAM --parameter-overrides AgentRuntimeArn="$RUNTIME_ARN"

echo "done. Smoke test:"
echo "  agentcore invoke '{\"action\": \"intake\"}'"
echo "  agentcore invoke '{\"action\": \"tick\"}'"
