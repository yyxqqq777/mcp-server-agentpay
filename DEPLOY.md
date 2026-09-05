# Deploy & Discovery

## 1. Railway（Gateway 公网）

```bash
# 安装 CLI 后登录（浏览器授权）
railway login

# 一键部署
./scripts/deploy_railway.sh
```

**已部署公网（production）：**

`https://agentpay-xhs-production.up.railway.app`

Dashboard：https://railway.com/project/aa132f03-a1f8-455b-9c0b-c61619dd308e

健康检查：`GET /health`  
付费探测：`GET /api/v1/paid/xhs/note?note=<id>` → 应返回 **402** + `PAYMENT-REQUIRED`（含 bazaar 元数据）。

### 必填环境变量

| 变量 | 说明 |
|------|------|
| `PAYMENT_MODE` | `production` |
| `WALLET_RECIPIENT_ADDRESS` | 你的收款地址 |
| `PAYMENT_NETWORK` | 测试 `eip155:84532` / 主网 `eip155:8453` |
| `DATAFLOW_API_TOKEN` / `TIKHUB_API_KEY` | 上游密钥（仅服务端） |
| `X402_FACILITATOR_URL` | Sepolia: `https://x402.org/facilitator`；主网用 CDP |

## 2. x402 Bazaar（Coinbase 自动索引）

代码已 `register_extension(bazaar)` + 每条路由 `declare_discovery_extension`。

索引条件（官方）：

1. 公网 HTTPS 可访问  
2. 返回合法 402 + bazaar 扩展  
3. **完成一笔通过 Facilitator 的成功结算** 后才会进入 CDP Bazaar  

验证：

```bash
curl -X POST https://api.cdp.coinbase.com/platform/v2/x402/validate \
  -H "Content-Type: application/json" \
  -d '{"resource":"https://YOUR_RAILWAY_URL/api/v1/paid/xhs/note","method":"GET"}'
```

## 3. Smithery.ai（MCP 目录）

本仓库 MCP 为 **stdio**（`uvx mcp-server-agentpay`）。发布方式：

1. 先把代码推到公开 GitHub  
2. 打开 https://smithery.ai/new 连接仓库，或：

```bash
npx @smithery/cli auth login
# 若有远程 Streamable HTTP MCP：
# smithery mcp publish "https://…/mcp" -n @you/agentpay
```

用户安装时配置 `GATEWAY_BASE_URL=https://YOUR_RAILWAY_URL` + 付款钱包。

## 4. Glama.ai

1. https://glama.ai → 提交 MCP Server  
2. 指向 GitHub 仓库 / PyPI `mcp-server-agentpay`  
3. 在描述中写清：小红书舆情 / x402 付费 / 需自备 USDC 钱包  

## 5. Cloudflare Playground / agentic.market

- x402 资源被 CDP Bazaar 索引后，会进入 agentic.market 等消费端  
- Cloudflare Agents Playground：添加你的付费 HTTP 或 MCP 端点做联调  

## 现实预期

外部 Agent **不会**因为「官方自带 USDC」自动扣款；只有配置了 **带 USDC 的买方钱包** 的 Agent（或接了 x402-wallet MCP）才能付费调用。Bazaar / Smithery 解决的是**被发现**，不是**代付**。
