"""End-to-end x402 payment flow tests (demo mode)."""

import pytest
from httpx import ASGITransport, AsyncClient

from agentpay.config import Settings, get_settings
from agentpay.gateway.app import create_app
from agentpay.payment.verifier import create_demo_payment_signature


@pytest.fixture
def app(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("PAYMENT_MODE", "demo")
    monkeypatch.setenv("PAYMENT_NETWORK", "eip155:8453")
    monkeypatch.setenv(
        "WALLET_RECIPIENT_ADDRESS",
        "0x5f29e616e34bf86dD72B622Ef392b2FDcF1Aa50E",
    )
    monkeypatch.setenv("PAYMENT_AMOUNT", "0.05")
    get_settings.cache_clear()
    application = create_app()
    yield application
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["payment_mode"] == "demo"


@pytest.mark.asyncio
async def test_unpaid_returns_402(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/paid/sourcing", params={"keyword": "earbuds"})
    assert resp.status_code == 402
    assert resp.headers["X-Payment-Required"] == "true"
    body = resp.json()
    assert body["error"] == "Payment Required"
    assert body["amount"] == "0.05"


@pytest.mark.asyncio
async def test_paid_request_with_demo_signature(app):
    transport = ASGITransport(app=app)
    payer = "0xAgentDemoWallet000000000000000000000001"
    settings = get_settings()
    sig = create_demo_payment_signature(
        payer=payer,
        amount="0.05",
        recipient=settings.wallet_recipient_address,
    )
    headers = {
        "X-Payment-Signature": sig,
        "X-Payment-Payer": payer,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/paid/sourcing",
            params={"keyword": "phone case"},
            headers=headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["data"]["items"]) > 0
    assert resp.headers.get("X-Payment-Verified") == "true"
