---
name: xhs-note-fetch
description: >-
  Fetch Xiaohongshu (小红书) note details and user note lists via AgentPay paid
  APIs (x402 USDC micropayments). Use when the user provides a 小红书笔记链接 /
  note_id, asks for note title/desc/stats/images/video, or a creator homepage
  note list. Call AgentPay MCP tools or GATEWAY paid HTTP endpoints only.
license: MIT
compatibility: Requires AgentPay MCP or HTTP access to an AgentPay x402 gateway; network access
metadata:
  author: agentpay
  version: "0.3.0"
  product: AgentPay
  network: "eip155:8453"
  payment: x402
---

# Xiaohongshu Note Fetch (AgentPay)

Get Xiaohongshu note data by **paying AgentPay**. You call our API; we return structured JSON. You do not integrate any third-party note crawlers yourself.

```
Your Agent  --(x402 ~0.05 USDC)-->  AgentPay  -->  note JSON
```

## Prefer MCP tools

| Tool | Args |
|------|------|
| `xhs_get_note_detail` | `note` (URL or note_id), optional `note_type` (`image` / `video`) |
| `xhs_get_user_notes` | `user_id`, optional `cursor` |

MCP handles payment (402 → pay → retry). Configure `GATEWAY_BASE_URL` (and `AGENT_PRIVATE_KEY` in production).

## Or HTTP scripts

```bash
export GATEWAY_BASE_URL="https://api.your-agentpay-host.com"

python scripts/fetch_note.py "<note_url_or_id>" [--type image|video]
python scripts/fetch_user_notes.py "<user_id>" [--cursor CURSOR]
```

Paid paths:

- `GET /api/v1/paid/xhs/note?note=...`
- `GET /api/v1/paid/xhs/user_notes?user_id=...`

## Rules for the agent

1. Only call AgentPay MCP tools or `{GATEWAY_BASE_URL}/api/v1/paid/xhs/*`.
2. Do not invent alternate note-scraping endpoints or ask users for upstream API keys.
3. On 402 / payment errors, surface the AgentPay error; do not fabricate note content.
4. Summarize in the user's language; keep full JSON when they need raw fields.

## Response shape

```json
{
  "status": "success",
  "note": {
    "note_id": "...",
    "title": "...",
    "desc": "...",
    "author": {"user_id": "...", "nickname": "..."},
    "stats": {"liked": 0, "comments": 0, "collected": 0, "shared": 0},
    "images": ["https://..."],
    "video_url": null,
    "topics": ["..."]
  }
}
```

See [references/api.md](references/api.md).
