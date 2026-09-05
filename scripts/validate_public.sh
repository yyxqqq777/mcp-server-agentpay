#!/usr/bin/env bash
# After Railway URL is live: validate x402 + print Smithery/Glama next steps.
set -euo pipefail
URL="${1:?Usage: $0 https://your-app.up.railway.app}"
URL="${URL%/}"

echo "== health =="
curl -sf "$URL/health" | python3 -m json.tool

echo "== unpaid xhs note (expect 402) =="
CODE=$(curl -s -o /tmp/agentpay402.json -w "%{http_code}" \
  "$URL/api/v1/paid/xhs/note?note=6a95a1f30000000026019ab7")
echo "HTTP $CODE"
python3 - <<'PY'
import base64, json, sys
from pathlib import Path
# try header from a second request
PY
HDR=$(curl -sI "$URL/api/v1/paid/xhs/note?note=6a95a1f30000000026019ab7" | tr -d '\r')
echo "$HDR" | rg -i "HTTP/|payment-required" || true
PR=$(echo "$HDR" | awk -F': ' 'tolower($1)=="payment-required"{print $2}')
if [[ -n "$PR" ]]; then
  echo "$PR" | python3 -c "import sys,base64,json; print(json.dumps(json.loads(base64.b64decode(sys.stdin.read().strip())),indent=2)[:1200])"
fi

echo
echo "== CDP validate (Bazaar readiness) =="
curl -s -X POST https://api.cdp.coinbase.com/platform/v2/x402/validate \
  -H "Content-Type: application/json" \
  -d "{\"resource\":\"$URL/api/v1/paid/xhs/note\",\"method\":\"GET\"}" | python3 -m json.tool | head -80

echo
echo "Next:"
echo "  1) Complete one successful paid settle → CDP Bazaar indexes the route"
echo "  2) Smithery: https://smithery.ai/new  (connect GitHub or publish MCP URL)"
echo "  3) Glama: https://glama.ai  → submit MCP server pointing at this repo / PyPI"
echo "  4) Set MCP client env GATEWAY_BASE_URL=$URL"
