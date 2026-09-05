#!/usr/bin/env bash
# Deploy AgentPay Gateway to Railway.
# Prerequisites: railway login (browser), then run this script.
set -euo pipefail
cd "$(dirname "$0")/.."
source "$HOME/.railway/env" 2>/dev/null || true

if ! railway whoami >/dev/null 2>&1; then
  echo "Not logged in. Opening browser for railway login..."
  railway login
fi

echo "Logged in as: $(railway whoami)"

# Link or create project
if ! railway status >/dev/null 2>&1; then
  echo "Creating Railway project agentpay-xhs..."
  railway init -n agentpay-xhs || railway link
fi

# Required env vars (set once; secrets must exist)
# Prefer Sepolia for first live discovery settle; switch to mainnet when ready.
railway variables set \
  PAYMENT_MODE=production \
  PAYMENT_NETWORK=eip155:84532 \
  PAYMENT_AMOUNT=0.01 \
  PAYMENT_TOKEN_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e \
  WALLET_RECIPIENT_ADDRESS=0x5f29e616e34bf86dD72B622Ef392b2FDcF1Aa50E \
  BASE_RPC_URL=https://sepolia.base.org \
  X402_FACILITATOR_URL=https://x402.org/facilitator \
  GATEWAY_HOST=0.0.0.0 \
  XHS_DIRECT_MODE=false

# Upstream keys from local .env if present
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  if [[ -n "${DATAFLOW_API_TOKEN:-}" ]]; then
    railway variables set DATAFLOW_API_TOKEN="$DATAFLOW_API_TOKEN" DATAFLOW_BASE_URL="${DATAFLOW_BASE_URL:-https://dataflowserver.org}"
  fi
  if [[ -n "${TIKHUB_API_KEY:-}" ]]; then
    railway variables set TIKHUB_API_KEY="$TIKHUB_API_KEY"
  fi
fi

echo "Deploying..."
railway up --detach

echo "Generating public domain (if missing)..."
railway domain 2>/dev/null || true

echo "Status:"
railway status
echo
echo "Public URL (also check Railway dashboard → Networking):"
railway domain 2>/dev/null || railway variables | rg -i "RAILWAY_PUBLIC|URL" || true
