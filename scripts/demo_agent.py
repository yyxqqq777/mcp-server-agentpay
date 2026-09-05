#!/usr/bin/env python3
"""Demo script: agent autonomously pays and fetches wholesale data."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agentpay.client.http_client import X402AgentClient
from agentpay.config import get_settings


async def main() -> None:
    settings = get_settings()
    client = X402AgentClient(settings)

    print(f"AgentPay Demo — mode={settings.payment_mode}")
    print(f"Gateway: {settings.gateway_base_url}")
    print(f"Agent wallet: {client.payer_address}")
    print(f"Max spend/call: {settings.max_spend_per_call} USDC\n")

    keyword = sys.argv[1] if len(sys.argv) > 1 else "wireless earbuds"
    print(f"Querying: {keyword}\n")

    result = await client.get_sourcing(keyword=keyword, max_price=3.0)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
