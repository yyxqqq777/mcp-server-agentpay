"""AgentPay x402 Micropayment Data Gateway — FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from agentpay.config import get_settings
from agentpay.gateway.data import query_wholesale_pricing
from agentpay.gateway.middleware import X402PaymentMiddleware
from agentpay.mcp_server.server import mcp as mcp_server
from agentpay.payment.x402_setup import build_paid_routes, build_resource_server, settlement_info
from agentpay.xhs.fetcher import fetch_note_detail, fetch_user_notes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    # Remote MCP (Streamable HTTP) for Smithery / Glama connectors
    mcp_http = mcp_server.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        host="0.0.0.0",
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        async with mcp_http.router.lifespan_context(mcp_http):
            logger.info("MCP Streamable HTTP mounted at /mcp")
            yield

    app = FastAPI(
        title="AgentPay x402 Gateway",
        description=(
            "Monetized API gateway with HTTP 402 micropayment enforcement. "
            "Agents pay USDC on Base per request for Xiaohongshu note data and other premium APIs. "
            "Also exposes MCP tools at /mcp (Streamable HTTP)."
        ),
        version="0.1.3",
        lifespan=lifespan,
    )
    app.mount("/mcp", mcp_http)

    # Railway/Fly terminate TLS; trust X-Forwarded-* so 402 resource URLs are https://
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Payment-Required",
            "X-Payment-Network",
            "X-Payment-Token",
            "X-Payment-Amount",
            "X-Payment-Recipient",
            "X-Payment-Verified",
            "X-Payment-Payer",
            "PAYMENT-REQUIRED",
            "PAYMENT-RESPONSE",
        ],
    )

    if settings.is_demo_mode:
        # Local/dev: accept demo signatures (no on-chain settlement)
        app.add_middleware(X402PaymentMiddleware, settings=settings)
        logger.info("Payment middleware: demo (no chain settlement)")
    else:
        # Production/testnet: official x402 verify + settle via facilitator
        from x402.http.middleware.fastapi import PaymentMiddlewareASGI

        server = build_resource_server(settings)
        routes = build_paid_routes(settings)
        app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
        logger.info(
            "Payment middleware: x402 facilitator=%s network=%s pay_to=%s",
            settlement_info(settings)["facilitator"],
            settings.payment_network,
            settings.wallet_recipient_address,
        )

    @app.get("/health")
    async def health():
        info = settlement_info(settings)
        return {
            "status": "ok",
            "service": "agentpay-gateway",
            "payment_mode": settings.payment_mode,
            "xhs_credentials": settings.has_xhs_credentials,
            "mcp": "/mcp",
            "settlement": info,
        }

    @app.get("/api/v1/pricing")
    async def pricing_info():
        """Public endpoint: returns payment requirements without serving data."""
        return {
            "services": [
                {
                    "name": "xhs_note_detail",
                    "paid_endpoint": "/api/v1/paid/xhs/note",
                    "amount": settings.payment_amount,
                },
                {
                    "name": "xhs_user_notes",
                    "paid_endpoint": "/api/v1/paid/xhs/user_notes",
                    "amount": settings.payment_amount,
                },
                {
                    "name": "china_wholesale_pricing",
                    "paid_endpoint": "/api/v1/paid/sourcing",
                    "amount": settings.payment_amount,
                },
            ],
            "payment_required": True,
            "network": settings.payment_network,
            "token": settings.payment_token_symbol,
            "recipient": settings.wallet_recipient_address,
            "settlement": settlement_info(settings),
        }

    @app.get("/api/v1/paid/sourcing")
    async def get_sourcing_data(
        keyword: str = Query(..., description="Product search query"),
        category_id: str | None = Query(None, description="Optional category filter"),
        max_price: float | None = Query(None, description="Max unit price USD"),
    ):
        """Monetized endpoint: wholesale pricing data (requires x402 payment)."""
        return query_wholesale_pricing(keyword, category_id, max_price)

    @app.get("/api/v1/paid/xhs/note")
    async def get_xhs_note(
        note: str = Query(..., description="Xiaohongshu note URL or 24-char note_id"),
        note_type: str | None = Query(
            None, description="Optional hint: image | video | 图文 | 视频"
        ),
    ):
        """Monetized: fetch Xiaohongshu note detail."""
        if not settings.has_xhs_credentials:
            return {
                "status": "error",
                "error": "Note data provider not configured on gateway",
            }
        return await fetch_note_detail(
            note_id_or_link=note,
            note_type_hint=note_type,
            settings=settings,
        )

    @app.get("/api/v1/paid/xhs/user_notes")
    async def get_xhs_user_notes(
        user_id: str = Query(..., description="Xiaohongshu user ID"),
        cursor: str = Query("", description="Pagination cursor from previous response"),
    ):
        """Monetized: fetch a user's posted notes list."""
        if not settings.has_xhs_credentials:
            return {
                "status": "error",
                "error": "Note data provider not configured on gateway",
            }
        return await fetch_user_notes(user_id=user_id, cursor=cursor, settings=settings)

    return app


app = create_app()


def main() -> None:
    # Clear settings cache so .env edits apply on restart
    get_settings.cache_clear()
    settings = get_settings()
    info = settlement_info(settings)
    # Railway/Cloud inject PORT
    import os

    port = int(os.getenv("PORT") or settings.gateway_port)
    host = os.getenv("HOST") or settings.gateway_host or "0.0.0.0"
    logger.info(
        "Starting AgentPay Gateway on %s:%s mode=%s network=%s pay_to=%s facilitator=%s",
        host,
        port,
        settings.payment_mode,
        settings.payment_network,
        settings.wallet_recipient_address,
        info["facilitator"],
    )
    uvicorn.run(
        "agentpay.gateway.app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
