# 发布指南

将 AgentPay 提交到官方 MCP Registry，供全球用户通过 `uvx mcp-server-agentpay` 一键安装。

## 前置条件

1. **GitHub 公开仓库** — 例如 `https://github.com/<你的用户名>/mcp-server-agentpay`
2. **PyPI 账号** — https://pypi.org
3. **更新命名空间** — 将所有 `yyx` 替换为你的 GitHub 用户名：
   - `server.json` → `"name": "io.github.<username>/agentpay"`
   - `README.md` → `<!-- mcp-name: io.github.<username>/agentpay -->`
   - `pyproject.toml` → `[project.urls]` 中的 GitHub 链接

## 步骤 1：发布到 PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

验证：`uvx mcp-server-agentpay` 应能正常运行。

## 步骤 2：发布到 MCP Registry

```bash
# 安装发布工具
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher

# 验证 server.json
./mcp-publisher validate

# GitHub OAuth 登录
./mcp-publisher login github

# 发布
./mcp-publisher publish
```

## 步骤 3：GitHub Actions 自动化（可选）

在 GitHub 仓库 Settings → Secrets 中添加：

| Secret | 用途 |
|--------|------|
| `PYPI_API_TOKEN` | PyPI 发布 token |

创建 GitHub Release（tag 如 `v0.1.0`）即可自动发布到 PyPI + MCP Registry。

## 步骤 4：部署 Gateway（服务端）

MCP 插件是**客户端**（付款方），用户还需要一个可访问的 x402 Gateway（收款方）：

```bash
pip install "mcp-server-agentpay[gateway]"
# 配置 .env 后
agentpay-gateway
```

可部署到 Railway、Fly.io、Cloud Run 等，将 URL 填入用户的 `GATEWAY_BASE_URL`。

## 其他目录（可选）

- **Smithery** — https://smithery.ai → Publish MCP
- **MCPFind** — https://mcpfind.org

## 用户安装方式

发布成功后，任何用户可在 Cursor 中添加：

```json
{
  "mcpServers": {
    "agentpay": {
      "command": "uvx",
      "args": ["mcp-server-agentpay"],
      "env": {
        "GATEWAY_BASE_URL": "https://你的网关地址",
        "AGENT_PRIVATE_KEY": "0x...",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

或在 MCP Registry 中搜索 `agentpay` 一键安装。
