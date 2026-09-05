"""Autonomous x402 payment HTTP client for AI agents."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agentpay.config import Settings, get_settings
from agentpay.payment.verifier import create_demo_payment_signature

logger = logging.getLogger(__name__)


class PaymentPolicyError(Exception):
    """Raised when a payment exceeds agent spending policy."""


class X402PaymentRequired(Exception):
    """Raised when 402 is received but auto-pay is disabled."""

    def __init__(self, challenge: dict[str, Any], headers: dict[str, str]):
        self.challenge = challenge
        self.headers = headers
        super().__init__("Payment required")


class X402AgentClient:
    """
    HTTP client that intercepts 402 Payment Required responses,
    signs payment authorization, and automatically retries.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._payer_address: str | None = None

    @property
    def payer_address(self) -> str:
        if self._payer_address:
            return self._payer_address

        if self.settings.agent_private_key:
            try:
                from eth_account import Account

                account = Account.from_key(self.settings.agent_private_key)
                self._payer_address = account.address
                return self._payer_address
            except Exception as e:
                logger.warning("Invalid agent private key: %s", e)

        self._payer_address = "0xAgentDemoWallet000000000000000000000001"
        return self._payer_address

    def _check_spending_policy(self, amount_str: str) -> None:
        amount = float(str(amount_str).lstrip("$"))
        if amount > self.settings.max_spend_per_call:
            raise PaymentPolicyError(
                f"Payment {amount} USDC exceeds max_spend_per_call "
                f"({self.settings.max_spend_per_call} USDC)"
            )

    def _sign_demo_payment(self, challenge: dict[str, Any]) -> str:
        amount = challenge.get("amount") or self.settings.payment_amount
        recipient = challenge.get("recipient") or self.settings.wallet_recipient_address
        self._check_spending_policy(str(amount))
        sig = create_demo_payment_signature(
            payer=self.payer_address,
            amount=str(amount).lstrip("$"),
            recipient=recipient,
        )
        logger.info("Demo payment signed: %s USDC -> %s", amount, recipient[:10])
        return sig

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        auto_pay: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with automatic 402 handling."""
        if not self.settings.is_demo_mode:
            return await self._request_official_x402(
                method, url, params=params, auto_pay=auto_pay, **kwargs
            )

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.request(method, url, params=params, **kwargs)

            if response.status_code != 402:
                return response

            if not auto_pay:
                raise X402PaymentRequired(response.json(), dict(response.headers))

            challenge = response.json()
            amount = (
                challenge.get("amount")
                or response.headers.get("X-Payment-Amount")
                or self.settings.payment_amount
            )
            challenge["amount"] = amount
            challenge["recipient"] = (
                challenge.get("recipient")
                or response.headers.get("X-Payment-Recipient")
                or self.settings.wallet_recipient_address
            )

            signature = self._sign_demo_payment(challenge)
            headers = kwargs.pop("headers", {}) or {}
            headers["X-Payment-Signature"] = signature
            headers["X-Payment-Payer"] = self.payer_address

            logger.info("Retrying paid request to %s", url)
            return await client.request(method, url, params=params, headers=headers, **kwargs)

    async def _request_official_x402(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        auto_pay: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        """Production path: official x402 SDK signs + facilitator settles."""
        if not self.settings.agent_private_key:
            raise ValueError("AGENT_PRIVATE_KEY required for production x402 payments")

        from eth_account import Account
        from x402 import x402Client
        from x402.http.clients.httpx import x402HttpxClient
        from x402.mechanisms.evm.exact import ExactEvmScheme
        from x402.mechanisms.evm.signers import EthAccountSigner

        self._check_spending_policy(self.settings.payment_amount)

        account = Account.from_key(self.settings.agent_private_key)
        self._payer_address = account.address
        signer = EthAccountSigner(account)

        payment_client = x402Client()
        payment_client.register(self.settings.payment_network, ExactEvmScheme(signer))
        # Also register wildcard for network matching quirks
        payment_client.register("eip155:*", ExactEvmScheme(signer))

        if not auto_pay:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.request(method, url, params=params, **kwargs)
                if response.status_code == 402:
                    raise X402PaymentRequired(
                        response.json() if response.content else {},
                        dict(response.headers),
                    )
                return response

        async with x402HttpxClient(payment_client, timeout=90.0) as client:
            response = await client.request(method, url, params=params, **kwargs)
            return response

    async def get_sourcing(
        self,
        keyword: str,
        category_id: str | None = None,
        max_price: float | None = None,
    ) -> dict[str, Any]:
        settings = self.settings
        url = f"{settings.gateway_base_url}/api/v1/paid/sourcing"
        params: dict[str, Any] = {"keyword": keyword}
        if category_id:
            params["category_id"] = category_id
        if max_price is not None:
            params["max_price"] = max_price

        response = await self.request("GET", url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_xhs_note(
        self,
        note: str,
        note_type: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.gateway_base_url}/api/v1/paid/xhs/note"
        params: dict[str, Any] = {"note": note}
        if note_type:
            params["note_type"] = note_type
        response = await self.request("GET", url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_xhs_user_notes(
        self,
        user_id: str,
        cursor: str = "",
    ) -> dict[str, Any]:
        url = f"{self.settings.gateway_base_url}/api/v1/paid/xhs/user_notes"
        params: dict[str, Any] = {"user_id": user_id}
        if cursor:
            params["cursor"] = cursor
        response = await self.request("GET", url, params=params)
        response.raise_for_status()
        return response.json()
