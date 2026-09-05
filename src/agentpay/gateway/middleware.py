"""FastAPI x402 payment enforcement middleware."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from agentpay.config import Settings, get_settings
from agentpay.payment.verifier import build_402_body, build_402_headers, verify_payment

logger = logging.getLogger(__name__)

PROTECTED_PREFIX = "/api/v1/paid/"


class X402PaymentMiddleware(BaseHTTPMiddleware):
    """Intercept unpaid requests to monetized routes and return HTTP 402."""

    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith(PROTECTED_PREFIX):
            return await call_next(request)

        signature = request.headers.get("X-Payment-Signature")
        payer = request.headers.get("X-Payment-Payer")

        if not verify_payment(signature, payer, self.settings):
            logger.info(
                "402 challenge for %s %s (payer=%s)",
                request.method,
                request.url.path,
                payer or "none",
            )
            return JSONResponse(
                status_code=402,
                headers=build_402_headers(self.settings),
                content=build_402_body(self.settings),
            )

        response = await call_next(request)

        # Attach settlement confirmation header
        response.headers["X-Payment-Verified"] = "true"
        if payer:
            response.headers["X-Payment-Payer"] = payer
        return response
