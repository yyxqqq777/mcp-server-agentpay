"""Official x402 facilitator + Bazaar discovery wiring."""

from __future__ import annotations

from typing import Any

from x402.extensions.bazaar import (
    OutputConfig,
    bazaar_resource_server_extension,
    declare_discovery_extension,
)
from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

from agentpay.config import Settings

DEFAULT_TESTNET_FACILITATOR = "https://x402.org/facilitator"
DEFAULT_MAINNET_FACILITATOR = "https://api.cdp.coinbase.com/platform/v2/x402"


def facilitator_url(settings: Settings) -> str:
    if (settings.x402_facilitator_url or "").strip():
        return settings.x402_facilitator_url.strip()
    if "84532" in settings.payment_network:
        return DEFAULT_TESTNET_FACILITATOR
    return DEFAULT_MAINNET_FACILITATOR


def build_resource_server(settings: Settings) -> x402ResourceServer:
    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url=facilitator_url(settings))
    )
    server = x402ResourceServer(facilitator)
    server.register(settings.payment_network, ExactEvmServerScheme())
    # Opt into x402 Bazaar discovery (CDP indexes after a successful settle)
    server.register_extension(bazaar_resource_server_extension)
    return server


def price_usd(settings: Settings) -> str:
    amount = str(settings.payment_amount).strip()
    if amount.startswith("$"):
        return amount
    return f"${amount}"


def _payment_option(settings: Settings) -> PaymentOption:
    return PaymentOption(
        scheme="exact",
        pay_to=settings.wallet_recipient_address,
        price=price_usd(settings),
        network=settings.payment_network,
    )


def build_paid_routes(settings: Settings) -> dict[str, RouteConfig]:
    """Protect monetized routes and declare Bazaar discovery metadata."""
    option = _payment_option(settings)

    return {
        "GET /api/v1/paid/xhs/note": RouteConfig(
            accepts=[option],
            mime_type="application/json",
            description=(
                "Fetch Xiaohongshu (小红书) note detail by share URL or note_id: "
                "title, desc, author, engagement stats, images, video URL. "
                "Use for China social listening / XHS content analysis."
            ),
            extensions=declare_discovery_extension(
                input={
                    "note": "https://www.xiaohongshu.com/explore/6a95a1f30000000026019ab7",
                    "note_type": "video",
                },
                input_schema={
                    "type": "object",
                    "properties": {
                        "note": {
                            "type": "string",
                            "description": "Xiaohongshu note share URL or 24-char note_id",
                        },
                        "note_type": {
                            "type": "string",
                            "description": "Optional media hint: image | video | 图文 | 视频",
                        },
                    },
                    "required": ["note"],
                },
                output=OutputConfig(
                    example={
                        "status": "success",
                        "note": {
                            "note_id": "6a95a1f30000000026019ab7",
                            "title": "示例笔记标题",
                            "desc": "正文…",
                            "author": {"user_id": "u1", "nickname": "作者"},
                            "stats": {"liked": 1, "comments": 0, "collected": 1, "shared": 0},
                            "images": ["https://example.com/cover.webp"],
                            "video_url": None,
                        },
                    }
                ),
            ),
        ),
        "GET /api/v1/paid/xhs/user_notes": RouteConfig(
            accepts=[option],
            mime_type="application/json",
            description=(
                "List Xiaohongshu user posted notes (paginated) by user_id. "
                "Use for creator monitoring and China social opinion workflows."
            ),
            extensions=declare_discovery_extension(
                input={"user_id": "671f285c000000001d0228c4", "cursor": ""},
                input_schema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "Xiaohongshu user ID",
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor from previous next_cursor",
                        },
                    },
                    "required": ["user_id"],
                },
                output=OutputConfig(
                    example={
                        "status": "success",
                        "user_id": "671f285c000000001d0228c4",
                        "has_more": True,
                        "next_cursor": "abc",
                        "total": 20,
                        "notes": [{"note_id": "…", "title": "…"}],
                    }
                ),
            ),
        ),
        "GET /api/v1/paid/sourcing": RouteConfig(
            accepts=[option],
            mime_type="application/json",
            description="Factory wholesale pricing sample endpoint (demo catalog).",
            extensions=declare_discovery_extension(
                input={"keyword": "wireless earbuds"},
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "category_id": {"type": "string"},
                        "max_price": {"type": "number"},
                    },
                    "required": ["keyword"],
                },
                output=OutputConfig(example={"status": "success", "data": {"items": []}}),
            ),
        ),
    }


def settlement_info(settings: Settings) -> dict[str, Any]:
    return {
        "mode": settings.payment_mode,
        "network": settings.payment_network,
        "pay_to": settings.wallet_recipient_address,
        "price": price_usd(settings),
        "facilitator": facilitator_url(settings),
        "bazaar_discovery": True,
    }
