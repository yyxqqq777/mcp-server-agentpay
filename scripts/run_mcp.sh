#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
export PAYMENT_MODE=demo
python -m agentpay.mcp_server.server
