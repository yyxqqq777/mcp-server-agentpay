"""AgentPay MCP Server — x402 micropayments + Xiaohongshu note tools."""

from __future__ import annotations

import json
import logging
import sys
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from agentpay import __version__
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

mcp = MCPServer(
    name="AgentPay",
    title="AgentPay",
    version=__version__,
    website_url="https://github.com/yyxqqq777/mcp-server-agentpay",
    description=(
        "Pay-per-call Xiaohongshu (小红书) and China wholesale data for AI agents. "
        "Each paid tool settles USDC on Base via x402; configure AGENT_PRIVATE_KEY only."
    ),
    instructions=(
        "AgentPay exposes paid China social and sourcing data. "
        "Use xhs_get_note_detail when the user provides a Xiaohongshu note URL or note_id. "
        "Use xhs_get_user_notes to list a creator's posts by user_id. "
        "Use china_wholesale_pricing_query for factory/wholesale price research. "
        "Call agentpay_payment_status first if payment fails or to confirm wallet/network. "
        "Paid tools charge ~0.01 USDC per call on Base (testnet or mainnet per gateway). "
        "Never invent note content — always call the tools."
    ),
)

_READ_OPEN = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
_READ_LOCAL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool(
    name="xhs_get_note_detail",
    title="Get Xiaohongshu note detail",
    description=(
        "Fetch one Xiaohongshu (小红书) note by share URL or 24-char note_id and return "
        "title, description, author, engagement stats, images, and video URL as JSON. "
        "Call this when the user pastes an xiaohongshu.com/explore link or a note id. "
        "Settles ~0.01 USDC via x402 on each successful call."
    ),
    annotations=_READ_OPEN,
)
async def xhs_get_note_detail(
    note: Annotated[
        str,
        Field(
            description=(
                "Xiaohongshu note share URL or 24-character hex note_id. "
                "Example: https://www.xiaohongshu.com/explore/6a95a1f30000000026019ab7"
            )
        ),
    ],
    note_type: Annotated[
        str | None,
        Field(
            description="Optional media hint to speed lookup: image, video, 图文, or 视频."
        ),
    ] = None,
) -> str:
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


@mcp.tool(
    name="xhs_get_user_notes",
    title="List Xiaohongshu user notes",
    description=(
        "List posted notes for a Xiaohongshu user_id (paginated). Returns note summaries "
        "and next_cursor for pagination. Use when the user asks for a creator's recent posts. "
        "Settles ~0.01 USDC via x402 per page."
    ),
    annotations=_READ_OPEN,
)
async def xhs_get_user_notes(
    user_id: Annotated[
        str,
        Field(description="Xiaohongshu user ID string from a profile or prior note author."),
    ],
    cursor: Annotated[
        str | None,
        Field(
            description=(
                "Pagination cursor from the previous response's next_cursor. "
                "Omit or null for the first page."
            )
        ),
    ] = None,
) -> str:
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


@mcp.tool(
    name="china_wholesale_pricing_query",
    title="Query China wholesale pricing",
    description=(
        "Search factory-direct wholesale pricing samples for a product keyword "
        "(1688 / Yiwu style catalog). Returns items with MOQ, unit price USD, "
        "factory location, and supplier verification flags. Use for China sourcing "
        "research. Settles ~0.01 USDC via x402 per query."
    ),
    annotations=_READ_OPEN,
)
async def china_wholesale_pricing_query(
    keyword: Annotated[
        str,
        Field(
            description=(
                "Product search query in English or Chinese, e.g. 'wireless earbuds' or '蓝牙耳机'."
            )
        ),
    ],
    category_id: Annotated[
        str | None,
        Field(description="Optional category filter ID when the user specifies a catalog category."),
    ] = None,
    max_price: Annotated[
        float | None,
        Field(description="Optional maximum target unit price in USD to filter results."),
    ] = None,
) -> str:
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


@mcp.tool(
    name="agentpay_payment_status",
    title="Check AgentPay payment status",
    description=(
        "Return AgentPay payment configuration without charging: network, price, "
        "spending limit, payment mode, gateway URL, and agent wallet address. "
        "Call this before paid tools to verify the wallet is configured, or after a payment error."
    ),
    annotations=_READ_LOCAL,
)
async def agentpay_payment_status(
    include_wallet: Annotated[
        bool,
        Field(
            description=(
                "If true (default), include the derived agent wallet address from AGENT_PRIVATE_KEY."
            )
        ),
    ] = True,
) -> str:
    settings = get_settings()
    payload: dict[str, object] = {
        "service": "AgentPay MCP",
        "payment_network": settings.payment_network,
        "payment_amount_usdc": settings.payment_amount,
        "max_spend_per_call": settings.max_spend_per_call,
        "payment_mode": settings.payment_mode,
        "gateway_url": settings.gateway_base_url,
        "xhs_direct_mode": settings.xhs_direct_mode,
        "xhs_credentials_configured": settings.has_xhs_credentials,
    }
    if include_wallet:
        client = X402AgentClient(settings)
        payload["agent_wallet"] = client.payer_address
    return _json(payload)


@mcp.resource(
    "agentpay://docs/usage",
    name="AgentPay usage guide",
    title="AgentPay usage guide",
    description="When to call each AgentPay tool and how x402 payment works.",
    mime_type="text/markdown",
)
def agentpay_usage_guide() -> str:
    return """# AgentPay usage

1. Set `AGENT_PRIVATE_KEY` (wallet with USDC on the gateway network).
2. Optional: call `agentpay_payment_status` to confirm network and wallet.
3. Paid tools (~0.01 USDC each):
   - `xhs_get_note_detail` — note URL or note_id
   - `xhs_get_user_notes` — creator `user_id` (+ optional `cursor`)
   - `china_wholesale_pricing_query` — product `keyword`
4. Gateway default is the public AgentPay x402 endpoint; override with `GATEWAY_BASE_URL` only if self-hosting.
"""


@mcp.prompt(
    name="analyze_xhs_note",
    title="Analyze a Xiaohongshu note",
    description="Prompt template to fetch a Xiaohongshu note via AgentPay and summarize it.",
)
def analyze_xhs_note(
    note: Annotated[
        str,
        Field(description="Xiaohongshu note URL or note_id to analyze."),
    ],
) -> str:
    return (
        "Use the AgentPay tool xhs_get_note_detail with "
        f"note={note!r}. Then summarize title, author, main points, and engagement stats "
        "in the user's language. Do not invent fields missing from the JSON."
    )


@mcp.prompt(
    name="source_product_china",
    title="Source a product in China",
    description="Prompt template to query China wholesale pricing via AgentPay.",
)
def source_product_china(
    keyword: Annotated[
        str,
        Field(description="Product keyword to search, e.g. wireless earbuds."),
    ],
    max_price: Annotated[
        str | None,
        Field(description="Optional max unit price in USD as a string number."),
    ] = None,
) -> str:
    price_line = f" Respect max_price={max_price}." if max_price else ""
    return (
        "Use china_wholesale_pricing_query with "
        f"keyword={keyword!r}.{price_line} "
        "Compare MOQ, unit_price_usd, and supplier_verified, then recommend 2–3 options."
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
