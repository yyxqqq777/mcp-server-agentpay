#!/usr/bin/env bash
# Publish AgentPay to PyPI + MCP Registry from a local machine.
# Requires: build, twine; GitHub auth via `gh`.
# Optional: PYPI_API_TOKEN / TWINE_PASSWORD / UV_PUBLISH_TOKEN for PyPI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
echo "== building mcp-server-agentpay==$VERSION =="
rm -rf dist
python3 -m pip install -q build twine
python3 -m build

PYPI_OK=0
if [[ -n "${UV_PUBLISH_TOKEN:-}${TWINE_PASSWORD:-}${PYPI_API_TOKEN:-}" ]]; then
  TOKEN="${UV_PUBLISH_TOKEN:-${TWINE_PASSWORD:-$PYPI_API_TOKEN}}"
  echo "== uploading to PyPI =="
  python3 -m twine upload dist/* -u __token__ -p "$TOKEN"
  PYPI_OK=1
else
  echo "WARN: No PYPI_API_TOKEN / TWINE_PASSWORD / UV_PUBLISH_TOKEN — skip PyPI upload"
  echo "      Create a token at https://pypi.org/manage/account/token/ then:"
  echo "      PYPI_API_TOKEN=pypi-... $0"
  echo "      Or configure Trusted Publishing and create a GitHub Release."
fi

PUBLISHER="${MCP_PUBLISHER:-}"
if [[ -z "$PUBLISHER" ]] || ! command -v "$PUBLISHER" >/dev/null 2>&1; then
  ARCH=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')
  OS=$(uname -s | tr '[:upper:]' '[:lower:]')
  curl -fsSL "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_${OS}_${ARCH}.tar.gz" \
    | tar xz -C /tmp mcp-publisher
  PUBLISHER=/tmp/mcp-publisher
fi

echo "== MCP Registry login (GitHub token) =="
"$PUBLISHER" login github -token "$(gh auth token)"

if [[ "$PYPI_OK" -eq 1 ]]; then
  "$PUBLISHER" validate
  "$PUBLISHER" publish
else
  echo "== publishing remotes-only (PyPI package not uploaded) =="
  python3 - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("server.json").read_text())
data.pop("packages", None)
Path("server.remotes-only.json").write_text(json.dumps(data, indent=2) + "\n")
PY
  "$PUBLISHER" validate server.remotes-only.json
  "$PUBLISHER" publish server.remotes-only.json
fi
echo "== done =="
