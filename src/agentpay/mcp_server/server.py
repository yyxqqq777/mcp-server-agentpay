"""AgentPay MCP Server — x402 micropayments + Xiaohongshu note tools."""

from __future__ import annotations

import json
import logging
import sys

from mcp.server.mcpserver import MCPServer

from agentpay.client.http_client import PaymentPolicyError, X402AgentClient
from agentpay.config import get_settings
from agentpay.xhs.fetcher import fetch_note_detail, fetch_user_notes

# MCP stdio transport requires stdout to be protocol-only; log to stderr.
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

mcp = MCPServer("AgentPay")


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def xhs_get_note_detail(
    note: str,
    note_type: str | None = None,
) -> str:
    """
    Fetch Xiaohongshu (小红书) note detail via AgentPay: title, desc, author,
    stats, images, video URL. Paid with x402 USDC micropayment.

    Args:
        note: Note share URL or 24-char hex note_id
              (e.g. https://www.xiaohongshu.com/explore/.... or abc123...)
        note_type: Optional hint — image / video / 图文 / 视频
    """
    settings = get_settings()
    try:
        if settings.xhs_direct_mode:
            result = await fetch_note_detail(
                note_id_or_link=note,
                note_type_hint=note_type,
                settings=settings,
            )
        else:
            client = X402AgentClient(settings)
            result = await client.get_xhs_note(note=note, note_type=note_type)
        return _json(result)
    except PaymentPolicyError as e:
        return _json({"error": "Payment policy violation", "detail": str(e)})
    except Exception as e:
        logger.exception("xhs_get_note_detail failed")
        return _json({"error": "Request failed", "detail": str(e)})


@mcp.tool()
async def xhs_get_user_notes(
    user_id: str,
    cursor: str | None = None,
) -> str:
    """
    Fetch a Xiaohongshu user's posted notes list (paginated) via AgentPay.
    Paid with x402 USDC micropayment.

    Args:
        user_id: Xiaohongshu user ID
        cursor: Pagination cursor from previous response next_cursor
    """
    settings = get_settings()
    try:
        if settings.xhs_direct_mode:
            result = await fetch_user_notes(
                user_id=user_id,
                cursor=cursor or "",
                settings=settings,
            )
        else:
            client = X402AgentClient(settings)
            result = await client.get_xhs_user_notes(
                user_id=user_id, cursor=cursor or ""
            )
        return _json(result)
    except PaymentPolicyError as e:
        return _json({"error": "Payment policy violation", "detail": str(e)})
    except Exception as e:
        logger.exception("xhs_get_user_notes failed")
        return _json({"error": "Request failed", "detail": str(e)})


@mcp.tool()
async def china_wholesale_pricing_query(
    keyword: str,
    category_id: str | None = None,
    max_price: float | None = None,
) -> str:
    """
    Fetches factory-direct wholesale pricing, MOQ, and supplier verification
    data from China manufacturing hubs. Requires x402 USDC micropayment.

    Args:
        keyword: Product search query in English or Chinese
        category_id: Optional category filter ID
        max_price: Maximum target unit price in USD
    """
    settings = get_settings()
    client = X402AgentClient(settings)

    try:
        result = await client.get_sourcing(
            keyword=keyword,
            category_id=category_id,
            max_price=max_price,
        )
        return _json(result)
    except PaymentPolicyError as e:
        return _json({"error": "Payment policy violation", "detail": str(e)})
    except Exception as e:
        logger.exception("MCP tool error")
        return _json({"error": "Request failed", "detail": str(e)})


@mcp.tool()
async def agentpay_payment_status() -> str:
    """Returns current AgentPay configuration: network, amount, spending limits, and mode."""
    settings = get_settings()
    client = X402AgentClient(settings)
    return _json(
        {
            "service": "AgentPay MCP",
            "payment_network": settings.payment_network,
            "payment_amount_usdc": settings.payment_amount,
            "max_spend_per_call": settings.max_spend_per_call,
            "payment_mode": settings.payment_mode,
            "gateway_url": settings.gateway_base_url,
            "agent_wallet": client.payer_address,
            "xhs_direct_mode": settings.xhs_direct_mode,
            "xhs_credentials_configured": settings.has_xhs_credentials,
        }
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
