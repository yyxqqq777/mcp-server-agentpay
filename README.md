# AgentPay MCP Server

**Agent-to-Agent micropayments via x402 + MCP** — let AI agents autonomously pay for API access with USDC on Base.

<!-- mcp-name: io.github.yyxqqq777/agentpay -->

## Install (one command)

Works in **Cursor**, **Claude Desktop**, **VS Code**, and any MCP-compatible client:

```json
{
  "mcpServers": {
    "agentpay": {
      "command": "uvx",
      "args": ["mcp-server-agentpay"],
      "env": {
        "GATEWAY_BASE_URL": "https://agentpay-xhs-production.up.railway.app",
        "AGENT_PRIVATE_KEY": "0xYourAgentPrivateKey",
        "MAX_SPEND_PER_CALL": "0.10",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

Or install permanently:

```bash
pip install mcp-server-agentpay
# or
uv tool install mcp-server-agentpay
```

## Tools

| Tool | Description | Cost |
|------|-------------|------|
| `xhs_get_note_detail` | Xiaohongshu note detail | 0.05 USDC/call |
| `xhs_get_user_notes` | Xiaohongshu user posted notes list | 0.05 USDC/call |
| `china_wholesale_pricing_query` | Factory-direct wholesale pricing (1688/Yiwu) | 0.05 USDC/call |
| `agentpay_payment_status` | View payment config, wallet, and spending limits | Free |

### Example prompts

- "帮我看看这条小红书笔记写了什么：https://www.xiaohongshu.com/explore/..."
- "拉一下这个博主最近发的笔记，user_id=..."
- "Search wholesale prices for wireless earbuds under $3"
- "What's my AgentPay wallet and spending limit?"

## Agent Skill（可发布 · agentskills.io）

符合 [Agent Skills](https://agentskills.io)。对外只暴露 **AgentPay 付费小红书接口**，Agent 不知道、也不应调用任何上游爬虫：

```
Agent / MCP  --(x402 0.05 USDC)-->  AgentPay Gateway  -->  笔记 JSON
                                   收款: 你的 Base 钱包
```

```bash
npx skills-ref validate ./skills/xhs-note-fetch

# 本地：Gateway 持有上游密钥；Agent 侧只配 GATEWAY_BASE_URL
PYTHONPATH=src python -m agentpay.gateway.app
GATEWAY_BASE_URL=http://127.0.0.1:8402 \
  python skills/xhs-note-fetch/scripts/fetch_note.py "<笔记链接>"
```

发布 `skills/xhs-note-fetch` 即可。上游密钥只写在 Gateway 部署环境。

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GATEWAY_BASE_URL` | MCP / Skill | AgentPay 网关地址 |
| `AGENT_PRIVATE_KEY` | Production | 付款钱包私钥 |
| `MAX_SPEND_PER_CALL` | No | 单次上限（默认 `0.10`） |
| `PAYMENT_MODE` | Gateway | `demo` 或 `production` |
| `DATAFLOW_API_TOKEN` / `TIKHUB_API_KEY` | **仅 Gateway 部署** | 上游数据源（不对 Agent 暴露） |

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

# 2. Publish to MCP Registry
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher
./mcp-publisher login github
./mcp-publisher validate
./mcp-publisher publish
```

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
