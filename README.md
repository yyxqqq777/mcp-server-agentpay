# AgentPay MCP Server

**Agent-to-Agent micropayments via x402 + MCP** — let AI agents autonomously pay for API access with USDC on Base.

<!-- mcp-name: io.github.yyxqqq777/agentpay -->

## Install

### Option A — Remote MCP（推荐，无需本地安装）

在 Cursor / Claude / 任意支持 Streamable HTTP 的客户端添加：

`https://agentpay-xhs-production.up.railway.app/mcp`

官方 Registry 条目：`io.github.yyxqqq777/agentpay`

### Option B — 本地 stdio（`uvx` / PyPI）

```json
{
  "mcpServers": {
    "agentpay": {
      "command": "uvx",
      "args": ["mcp-server-agentpay"],
      "env": {
        "AGENT_PRIVATE_KEY": "0xYourAgentPrivateKey"
      }
    }
  }
}
```

只需填付款钱包私钥（需有 USDC）。网关地址已内置，一般不用改。

或永久安装：

```bash
pip install mcp-server-agentpay
# or
uv tool install mcp-server-agentpay
```

## Tools

| Tool | Description | Cost |
|------|-------------|------|
| `xhs_get_note_detail` | Xiaohongshu note detail | 0.01 USDC/call |
| `xhs_get_user_notes` | Xiaohongshu user posted notes list | 0.01 USDC/call |
| `china_wholesale_pricing_query` | Factory-direct wholesale pricing (1688/Yiwu) | 0.01 USDC/call |
| `agentpay_payment_status` | View payment config, wallet, and spending limits | Free |

### Example prompts

- "帮我看看这条小红书笔记写了什么：https://www.xiaohongshu.com/explore/..."
- "拉一下这个博主最近发的笔记，user_id=..."
- "Search wholesale prices for wireless earbuds under $3"
- "What's my AgentPay wallet and spending limit?"

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AGENT_PRIVATE_KEY` | Yes（付费工具） | 付款钱包私钥 |
| `MAX_SPEND_PER_CALL` | No | 单次上限（默认 `0.10`） |
| `GATEWAY_BASE_URL` | No | 网关地址（默认已指向公网 Gateway） |

## How it works

```
MCP Client  →  mcp-server-agentpay  →  x402 Gateway  →  Paid API
              (auto 402 → sign → retry)   (verify USDC)
```

1. Tool call hits a paid API endpoint
2. Gateway returns `402 Payment Required` with USDC payment details
3. MCP server signs payment and retries automatically
4. JSON data flows back to the LLM

## Self-host the Gateway

If you operate the paid API, deploy the gateway separately:

```bash
pip install "mcp-server-agentpay[gateway]"
# .env: PAYMENT_MODE=production + upstream keys + your receive wallet
agentpay-gateway
```

### Real USDC settlement (x402)

| Mode | Behavior |
|------|----------|
| `PAYMENT_MODE=demo` | Local fake pay (dev only) |
| `PAYMENT_MODE=production` | Official Facilitator **verify + settle** on-chain |

**Testnet (Base Sepolia)** — use `https://x402.org/facilitator`, network `eip155:84532`.

```bash
# Fund a test agent with Sepolia USDC, then:
PYTHONPATH=src python scripts/test_x402_settlement.py
```

**Mainnet** — set `PAYMENT_NETWORK=eip155:8453` and a mainnet facilitator
(`https://api.cdp.coinbase.com/platform/v2/x402` or PayAI). USDC goes to `WALLET_RECIPIENT_ADDRESS`.

See [`.env.example`](.env.example).

## Publish to MCP Registry

This package is designed for the [official MCP Registry](https://registry.modelcontextprotocol.io).

```bash
# 1. Publish to PyPI
pip install build twine
python -m build && twine upload dist/*

# 2. Publish to MCP Registry (packages + remotes)
./scripts/publish_all.sh
```

Or create a GitHub Release (`v0.1.0`) — Actions uses Trusted Publishing to PyPI then updates the Registry.

Before publishing, update `server.json` and README `mcp-name` with your GitHub namespace (`io.github.<username>/agentpay`).

## Development

```bash
git clone https://github.com/yyxqqq777/mcp-server-agentpay
cd mcp-server-agentpay
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
