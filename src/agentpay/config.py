"""Central configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Well-known USDC contract addresses
USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gateway
    wallet_recipient_address: str = "0x5f29e616e34bf86dD72B622Ef392b2FDcF1Aa50E"
    payment_network: str = "eip155:8453"  # Base Mainnet; use eip155:84532 for Sepolia test
    payment_amount: str = "0.05"
    payment_token_address: str = USDC_BASE_MAINNET
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 8402
    gateway_base_url: str = "https://agentpay-xhs-production.up.railway.app"

    # demo = local fake pay | production = official x402 facilitator settle
    payment_mode: str = "demo"
    base_rpc_url: str = "https://mainnet.base.org"

    # Agent client
    agent_private_key: str = ""
    max_spend_per_call: float = 0.10

    # Optional override; default picks testnet vs mainnet facilitator
    x402_facilitator_url: str = ""

    # Xiaohongshu data providers (gateway-side secrets only)
    dataflow_base_url: str = "https://dataflowserver.org"
    dataflow_api_token: str = ""
    tikhub_api_key: str = ""

    # Operator debug only — agents should always pay the gateway
    xhs_direct_mode: bool = False

    @property
    def payment_token_symbol(self) -> str:
        return "USDC"

    @property
    def is_demo_mode(self) -> bool:
        return self.payment_mode.lower() == "demo"

    @property
    def is_testnet(self) -> bool:
        return "84532" in self.payment_network

    @property
    def has_xhs_credentials(self) -> bool:
        return bool(
            (self.dataflow_api_token or "").strip() or (self.tikhub_api_key or "").strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
