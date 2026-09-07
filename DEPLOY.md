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

公开仓库：https://github.com/yyxqqq777/mcp-server-agentpay  

远程 MCP（Streamable HTTP）：

`https://agentpay-xhs-production.up.railway.app/mcp`

发布：

1. 打开 https://smithery.ai/new 并用 GitHub 登录  
2. 选择 **URL**，填入上面的 `/mcp` 地址  
3. 名称建议：`@yyxqqq777/agentpay`  
4. 或 CLI：

```bash
export SMITHERY_API_KEY=...   # https://smithery.ai/account/api-keys
npx @smithery/cli mcp publish \
  "https://agentpay-xhs-production.up.railway.app/mcp" \
  -n yyxqqq777/agentpay \
  --config-schema ./scripts/smithery-config-schema.json
```

**已上架：** https://smithery.ai/servers/yyxqqq777/agentpay  
Smithery 代理入口：`https://agentpay--yyxqqq777.run.tools`

## 4. Glama.ai

列表页：https://glama.ai/mcp/servers/yyxqqq777/mcp-server-agentpay  

页面上的 **“This server cannot be installed”** 不是因为没提交仓库，而是还没有做 **Glama Release**（容器化构建）。需要你登录后手动操作：

1. 用 GitHub 登录 Glama（账号需是 maintainer：`glama.json` 里已有 `yyxqqq777`）
2. 打开管理页并点 **Sync Server**（立刻同步最新 README / PyPI）：  
   https://glama.ai/mcp/servers/yyxqqq777/mcp-server-agentpay/admin
3. 打开 Dockerfile 管理页：  
   https://glama.ai/mcp/servers/yyxqqq777/mcp-server-agentpay/admin/dockerfile  
   - Dockerfile path：`Dockerfile.mcp`（stdio MCP；不要用根目录 `Dockerfile`，那是 Railway Gateway）  
   - CMD：`mcp-server-agentpay`  
   - 环境变量：只需 `AGENT_PRIVATE_KEY`（secret）；网关地址已内置默认值
4. 点 **Build**（或 **Build & Release**），成功后发布版本 `0.1.1`  
5. （可选）若提交 Connector：URL 用 `https://agentpay-xhs-production.up.railway.app/mcp`

参考：https://glama.ai/blog/2026-03-15-how-to-make-a-release

仓库已有 `glama.json`（maintainer: `yyxqqq777`）用于认领。GitHub Release：`v0.1.1`。

## 5. Cloudflare Playground / agentic.market

- x402 资源被 CDP Bazaar 索引后，会进入 agentic.market 等消费端  
- Cloudflare Agents Playground：添加你的付费 HTTP 或 MCP 端点做联调  

## 现实预期

外部 Agent **不会**因为「官方自带 USDC」自动扣款；只有配置了 **带 USDC 的买方钱包** 的 Agent（或接了 x402-wallet MCP）才能付费调用。Bazaar / Smithery 解决的是**被发现**，不是**代付**。

**已完成：**

- 官方 MCP Registry：`io.github.yyxqqq777/agentpay`（Streamable HTTP remote）
- 公网 Gateway + `/mcp` 健康
- 至少一笔 Base Sepolia Facilitator 成功结算（Bazaar 索引可能有延迟；`index` 仍为 null 时过几小时再查 CDP validate）
