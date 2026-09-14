#!/usr/bin/env bash
set -euo pipefail
aws cloudformation delete-stack --stack-name postscript-tick || true
agentcore destroy || echo "destroy the runtime from the AgentCore console if the CLI command is unavailable"
