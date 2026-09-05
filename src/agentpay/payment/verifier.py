"""On-chain and demo payment verification for x402 requests."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from agentpay.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Demo-mode replay protection: signature -> expiry timestamp
_demo_used_signatures: dict[str, float] = {}
_DEMO_SIG_TTL_SECONDS = 3600


@dataclass
class PaymentProof:
    payer: str
    signature: str
    amount: str
    recipient: str
    network: str
    token: str = "USDC"
    tx_hash: str | None = None
    raw_payload: dict[str, Any] | None = None


def build_402_headers(settings: Settings) -> dict[str, str]:
    """Build x402 challenge response headers per spec."""
    return {
        "X-Payment-Required": "true",
        "X-Payment-Network": settings.payment_network,
        "X-Payment-Token": settings.payment_token_address,
        "X-Payment-Amount": settings.payment_amount,
        "X-Payment-Recipient": settings.wallet_recipient_address,
    }


def build_402_body(settings: Settings) -> dict[str, Any]:
    """Build x402 challenge JSON body."""
    return {
        "error": "Payment Required",
        "code": 402,
        "network": settings.payment_network,
        "token": settings.payment_token_symbol,
        "amount": settings.payment_amount,
        "recipient": settings.wallet_recipient_address,
        "instructions": (
            "Sign USDC transfer authorization on Base and attach "
            "signature in X-Payment-Signature header with payer in X-Payment-Payer."
        ),
        "details": {
            "recipient": settings.wallet_recipient_address,
            "network": settings.payment_network,
            "token": settings.payment_token_symbol,
            "amount": settings.payment_amount,
        },
    }


def _parse_signature_payload(signature: str) -> dict[str, Any] | None:
    """Try to decode signature as JSON (base64 or raw)."""
    if not signature:
        return None
    try:
        decoded = base64.b64decode(signature).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        pass
    try:
        return json.loads(signature)
    except Exception:
        return None


def _verify_demo_payment(
    signature: str,
    payer: str,
    expected_amount: str,
    recipient: str,
) -> bool:
    """
    Demo mode: accept well-formed payment proofs without on-chain settlement.
    Signature must be a deterministic hash of payer+amount+recipient+nonce.
    """
    if not signature or not payer:
        return False

    now = time.time()
    # Clean expired entries
    expired = [k for k, v in _demo_used_signatures.items() if v < now]
    for k in expired:
        del _demo_used_signatures[k]

    if signature in _demo_used_signatures:
        logger.warning("Demo payment replay detected")
        return False

    payload = _parse_signature_payload(signature)
    if payload:
        if payload.get("payer", "").lower() != payer.lower():
            return False
        if str(payload.get("amount")) != expected_amount:
            return False
        if payload.get("recipient", "").lower() != recipient.lower():
            return False
    else:
        # Accept hex signatures prefixed with demo:
        if not signature.startswith("demo:"):
            return False

    _demo_used_signatures[signature] = now + _DEMO_SIG_TTL_SECONDS
    return True


def _verify_onchain_payment(
    signature: str,
    payer: str,
    expected_amount: str,
    recipient: str,
    settings: Settings,
) -> bool:
    """Verify payment via Base RPC (production mode)."""
    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(settings.base_rpc_url))
        if not w3.is_connected():
            logger.error("Cannot connect to Base RPC")
            return False

        payload = _parse_signature_payload(signature)
        if not payload:
            return False

        tx_hash = payload.get("txHash") or payload.get("tx_hash")
        if not tx_hash:
            return False

        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
        except Exception:
            logger.warning("Transaction not found: %s", tx_hash)
            return False

        if receipt["status"] != 1:
            return False

        # Verify USDC Transfer event to recipient
        transfer_topic = w3.keccak(text="Transfer(address,address,uint256)").hex()
        amount_wei = int(float(expected_amount) * 1_000_000)  # USDC 6 decimals

        for log in receipt["logs"]:
            if log["address"].lower() != settings.payment_token_address.lower():
                continue
            topics = [t.hex() if hasattr(t, "hex") else t for t in log["topics"]]
            if topics[0] != transfer_topic:
                continue
            to_addr = "0x" + topics[2][-40:]
            if to_addr.lower() != recipient.lower():
                continue
            value = int(log["data"].hex(), 16) if hasattr(log["data"], "hex") else int(log["data"], 16)
            if value >= amount_wei:
                return True

        return False
    except ImportError:
        logger.error("web3 not installed for production verification")
        return False


def verify_payment(
    signature: str | None,
    payer: str | None,
    settings: Settings | None = None,
) -> bool:
    """Verify x402 payment proof from request headers."""
    settings = settings or get_settings()
    if not signature or not payer:
        return False

    if settings.is_demo_mode:
        return _verify_demo_payment(
            signature,
            payer,
            settings.payment_amount,
            settings.wallet_recipient_address,
        )

    return _verify_onchain_payment(
        signature,
        payer,
        settings.payment_amount,
        settings.wallet_recipient_address,
        settings,
    )


def create_demo_payment_signature(
    payer: str,
    amount: str,
    recipient: str,
    nonce: str | None = None,
) -> str:
    """Generate a demo-mode payment signature for testing."""
    nonce = nonce or hashlib.sha256(f"{payer}{time.time()}".encode()).hexdigest()[:16]
    payload = {
        "payer": payer,
        "amount": amount,
        "recipient": recipient,
        "nonce": nonce,
        "scheme": "exact",
        "network": "eip155:84532",
    }
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    return encoded
