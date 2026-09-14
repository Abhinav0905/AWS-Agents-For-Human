"""EventBridge Scheduler target: ask the AgentCore Runtime to run today's tick."""

import json
import os
import uuid

import boto3


def handler(event, context):
    client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-west-2"))
    payload = json.dumps({"action": "tick"}).encode("utf-8")
    response = client.invoke_agent_runtime(
        agentRuntimeArn=os.environ["AGENT_RUNTIME_ARN"],
        runtimeSessionId=f"postscript-daily-{uuid.uuid4()}",  # each tick is its own session; state lives in the ledger
        payload=payload,
    )
    body = response["response"].read() if hasattr(response.get("response"), "read") else response.get("response")
    return {"statusCode": 200, "body": body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else str(body)}
