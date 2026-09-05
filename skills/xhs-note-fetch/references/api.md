# AgentPay Xiaohongshu API

Public surface for agents. All paid routes require x402.

## Endpoints

| Method | Path | Query | Auth |
|--------|------|-------|------|
| GET | `/health` | — | free |
| GET | `/api/v1/pricing` | — | free price sheet |
| GET | `/api/v1/paid/xhs/note` | `note`, optional `note_type` | x402 |
| GET | `/api/v1/paid/xhs/user_notes` | `user_id`, optional `cursor` | x402 |

## Payment

1. Request without payment → `402` + `X-Payment-*` headers  
2. Pay / sign per AgentPay x402 rules  
3. Retry with `X-Payment-Signature` + `X-Payment-Payer`  
4. `200` + JSON

Agent env: `GATEWAY_BASE_URL`, optional `AGENT_PRIVATE_KEY`, `MAX_SPEND_PER_CALL`.
