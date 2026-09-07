# 发布指南

将 AgentPay 提交到官方 MCP Registry，供全球用户通过 `uvx mcp-server-agentpay` 一键安装。

## 前置条件

1. **GitHub 公开仓库** — 例如 `https://github.com/<你的用户名>/mcp-server-agentpay`
2. **PyPI 账号** — https://pypi.org
3. **更新命名空间** — 将所有 `yyx` 替换为你的 GitHub 用户名：
   - `server.json` → `"name": "io.github.<username>/agentpay"`
   - `README.md` → `<!-- mcp-name: io.github.<username>/agentpay -->`
   - `pyproject.toml` → `[project.urls]` 中的 GitHub 链接

## 步骤 1：发布到 PyPI（Trusted Publishing，推荐）

1. 打开 https://pypi.org/manage/account/publishing/
2. 添加 **pending publisher**（项目尚不存在也可以）：
   - PyPI project name: `mcp-server-agentpay`
   - Owner: `yyxqqq777`
   - Repository: `mcp-server-agentpay`
   - Workflow: `publish.yml`
   - Environment: `pypi`
3. 创建 GitHub Release（tag `v0.1.0`）→ Actions 自动上传到 PyPI

本地手动上传（备选）：

```bash
# https://pypi.org/manage/account/token/ 创建 token
pip install build twine
python -m build
TWINE_PASSWORD=pypi-... twine upload dist/* -u __token__
```

验证：`uvx mcp-server-agentpay` 应能正常运行。

## 步骤 2：发布到 MCP Registry

Remote MCP 已可单独上架（不依赖 PyPI）。含 PyPI 包的完整条目需等包上线后再发：

```bash
# 一键：有 PyPI token 时上传包 + 发布完整 server.json
PYPI_API_TOKEN=pypi-... ./scripts/publish_all.sh

# 或仅 Registry（GitHub 登录）
./mcp-publisher login github -token "$(gh auth token)"
./mcp-publisher publish
```

当前公网远程入口：`https://agentpay-xhs-production.up.railway.app/mcp`  
Registry 名：`io.github.yyxqqq777/agentpay`

## 步骤 3：GitHub Actions 自动化

仓库已配置 `pypi` Environment + OIDC Trusted Publishing（无需 `PYPI_API_TOKEN` secret）。

在 PyPI 配好 pending publisher 后，创建 Release（tag 如 `v0.1.0`）即可自动发布到 PyPI + MCP Registry。

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
        "AGENT_PRIVATE_KEY": "0x..."
      }
    }
  }
}
```

只需 `AGENT_PRIVATE_KEY`；网关默认已指向公网 Gateway。或在 MCP Registry 中搜索 `agentpay` 一键安装。
