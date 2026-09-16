"""Environment-backed application settings."""

from __future__ import annotations

from typing import Literal

from governed_llm_gateway_client import GatewayClientConfig
from governed_llm_gateway_contracts import DataClassification, RiskLevel
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_runtime_boundaries.adapters.gateway_text import GatewayTextClient, GatewayTextConfig
from agent_runtime_boundaries.adapters.openai_text import OpenAITextClient, OpenAITextConfig
from agent_runtime_boundaries.adapters.text_generation import TextGenerationClient


class Settings(BaseSettings):
    """Settings shared by the local reference services."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql://postgres:postgres@127.0.0.1:5432/agent_runtime_boundaries"
    specialist_a2a_url: str = "http://127.0.0.1:8101/a2a"
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://127.0.0.1:4318/v1/traces"
    agno_db_file: str = ".data/agno-specialist.db"

    llm_backend: Literal["gateway", "openai"] = "gateway"
    openai_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    openai_model: str = "gpt-4.1-mini"
    openai_max_output_tokens: int = Field(default=2000, ge=16)
    openai_request_timeout_seconds: float = Field(default=60.0, gt=0, le=300)

    # SDK base URL; /v1/generate is appended by the client. No provider/model selector.
    governed_llm_gateway_url: str = "http://127.0.0.1:8001"
    governed_llm_gateway_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    governed_llm_gateway_workload: str = "agent.orchestration"
    governed_llm_gateway_risk_level: Literal["low", "medium", "high", "critical"] | None = None
    governed_llm_gateway_data_classification: (
        Literal["public", "internal", "confidential", "restricted"] | None
    ) = None
    governed_llm_gateway_max_output_tokens: int = Field(default=2000, gt=0)
    governed_llm_gateway_provider_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    governed_llm_gateway_request_timeout_seconds: float = Field(default=60.0, gt=0, le=300)

    fail_after_specialist_once: bool = False

    def text_client(self) -> TextGenerationClient:
        """Compose only the explicitly selected backend; never fall back on missing keys."""
        if self.llm_backend == "openai":
            return OpenAITextClient(
                OpenAITextConfig(
                    api_key=self.openai_api_key,
                    model=self.openai_model,
                    max_output_tokens=self.openai_max_output_tokens,
                    request_timeout_seconds=self.openai_request_timeout_seconds,
                )
            )
        return GatewayTextClient(self.gateway_text_config())

    def gateway_text_config(self) -> GatewayTextConfig:
        """Require explicit gateway context only when composing a model-backed specialist."""
        api_key = self.governed_llm_gateway_api_key.get_secret_value()
        if not api_key or api_key == "replace-me":
            raise ValueError("GOVERNED_LLM_GATEWAY_API_KEY must be configured")
        if self.governed_llm_gateway_risk_level is None:
            raise ValueError("GOVERNED_LLM_GATEWAY_RISK_LEVEL must be configured")
        if self.governed_llm_gateway_data_classification is None:
            raise ValueError("GOVERNED_LLM_GATEWAY_DATA_CLASSIFICATION must be configured")
        return GatewayTextConfig(
            connection=GatewayClientConfig(
                base_url=self.governed_llm_gateway_url,
                api_key=api_key,
                request_timeout_seconds=self.governed_llm_gateway_request_timeout_seconds,
            ),
            workload=self.governed_llm_gateway_workload,
            risk_level=RiskLevel(self.governed_llm_gateway_risk_level),
            data_classification=DataClassification(self.governed_llm_gateway_data_classification),
            max_output_tokens=self.governed_llm_gateway_max_output_tokens,
            provider_timeout_seconds=self.governed_llm_gateway_provider_timeout_seconds,
        )
