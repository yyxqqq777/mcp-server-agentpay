#!/usr/bin/env python3
"""Live x402 settlement test against local AgentPay gateway.

Uses official x402 SDK (Facilitator verify + settle).
Default: Base Sepolia + https://x402.org/facilitator

Usage:
  # 1) Start gateway with PAYMENT_MODE=production and eip155:84532
  # 2) Fund AGENT_PRIVATE_KEY with Base Sepolia USDC (and a little ETH for gas if needed)
  # 3) Run:
  PYTHONPATH=src python scripts/test_x402_settlement.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from eth_account import Account

from agentpay.client.http_client import X402AgentClient
from agentpay.config import get_settings


async def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()

    if settings.is_demo_mode:
        print("ERROR: PAYMENT_MODE=demo — switch to production for real settlement")
        print("  PAYMENT_MODE=production")
        print("  PAYMENT_NETWORK=eip155:84532   # Base Sepolia testnet")
        print("  X402_FACILITATOR_URL=https://x402.org/facilitator")
        return 1

    if not settings.agent_private_key:
        acct = Account.create()
        print("Generated test agent wallet (fund with Base Sepolia USDC):")
        print(f"  address: {acct.address}")
        print(f"  private_key: {acct.key.hex()}")
        print("Add to .env as AGENT_PRIVATE_KEY=..., fund USDC, re-run.")
        return 2

    account = Account.from_key(settings.agent_private_key)
    print("Settlement test")
    print(f"  mode:       {settings.payment_mode}")
    print(f"  network:    {settings.payment_network}")
    print(f"  pay_to:     {settings.wallet_recipient_address}")
    print(f"  amount:     {settings.payment_amount} USDC")
    print(f"  agent:      {account.address}")
    print(f"  gateway:    {settings.gateway_base_url}")

    client = X402AgentClient(settings)
    # Cheap path for settlement proof — sourcing is mock data, still paid
    try:
        result = await client.get_sourcing(keyword="x402-settlement-probe")
        print("\nSUCCESS — payment settled and resource returned:")
        print(json.dumps(result, ensure_ascii=False, indent=2)[:800])
        print(
            f"\nCheck recipient wallet {settings.wallet_recipient_address} "
            f"on network {settings.payment_network} for +{settings.payment_amount} USDC"
        )
        return 0
    except Exception as exc:
        print(f"\nFAILED: {exc}")
        print(
            "\nIf balance-related: fund the agent address with Base Sepolia USDC "
            "(Circle faucet / CDP faucet), then retry."
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
