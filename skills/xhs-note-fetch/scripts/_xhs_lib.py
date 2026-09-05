"""HTTP client for AgentPay x402 paid endpoints."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from typing import Any

import httpx


def _gateway() -> str:
    return (os.getenv("GATEWAY_BASE_URL") or "http://127.0.0.1:8402").rstrip("/")


def _demo_signature(payer: str, amount: str, recipient: str) -> str:
    nonce = hashlib.sha256(f"{payer}{time.time()}".encode()).hexdigest()[:16]
    payload = {
        "payer": payer,
        "amount": amount,
        "recipient": recipient,
        "nonce": nonce,
        "scheme": "exact",
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def _payer() -> str:
    key = (os.getenv("AGENT_PRIVATE_KEY") or "").strip()
    if key:
        try:
            from eth_account import Account

            return Account.from_key(key).address
        except Exception:
            pass
    return "0xAgentDemoWallet000000000000000000000001"


async def paid_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET AgentPay paid API with automatic 402 handling."""
    url = f"{_gateway()}{path}"
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 402:
            resp.raise_for_status()
            return resp.json()

        challenge = resp.json() if resp.content else {}
        amount = (
            challenge.get("amount")
            or resp.headers.get("X-Payment-Amount")
            or "0.05"
        )
        recipient = (
            challenge.get("recipient")
            or resp.headers.get("X-Payment-Recipient")
            or ""
        )
        max_spend = float(os.getenv("MAX_SPEND_PER_CALL") or "0.10")
        if float(amount) > max_spend:
            raise ValueError(
                f"Payment {amount} USDC exceeds MAX_SPEND_PER_CALL={max_spend}"
            )

        payer = _payer()
        signature = _demo_signature(payer, str(amount), recipient)
        headers = {
            "X-Payment-Signature": signature,
            "X-Payment-Payer": payer,
        }
        paid = await client.get(url, params=params, headers=headers)
        paid.raise_for_status()
        return paid.json()
