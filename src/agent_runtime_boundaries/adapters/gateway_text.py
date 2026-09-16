"""Bounded text generation through the current provider-neutral gateway SDK."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from governed_llm_gateway_client import GatewayClient, GatewayClientConfig
from governed_llm_gateway_contracts import (
    DataClassification,
    ExecutionStatus,
    Message,
    MessageRole,
    RiskLevel,
)

from agent_runtime_boundaries.adapters.text_generation import TextMessage, TextModelError


@dataclass(frozen=True)
class GatewayTextConfig:
    """Connection, workload intent and explicit caller-declared policy context."""

    connection: GatewayClientConfig
    workload: str
    risk_level: RiskLevel
    data_classification: DataClassification
    max_output_tokens: int = 2000
    provider_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        """Reject obsolete ingress URLs and malformed intent before any request."""
        if urlsplit(self.connection.base_url).path.rstrip("/").endswith("/v1"):
            raise ValueError("GOVERNED_LLM_GATEWAY_URL must be the base URL without /v1")
        if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", self.workload):
            raise ValueError("GOVERNED_LLM_GATEWAY_WORKLOAD must be a dotted workload identifier")
        if not isinstance(self.risk_level, RiskLevel):
            raise ValueError("GOVERNED_LLM_GATEWAY_RISK_LEVEL must be configured")
        if not isinstance(self.data_classification, DataClassification):
            raise ValueError("GOVERNED_LLM_GATEWAY_DATA_CLASSIFICATION must be configured")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        if not 0 < self.provider_timeout_seconds <= 300:
            raise ValueError("provider_timeout_seconds must be in the range (0, 300]")


class GatewayTextClient:
    """Perform one SDK call; the gateway owns routing and all inference resilience."""

    def __init__(
        self,
        config: GatewayTextConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Retain configuration without sharing HTTP pools across event loops."""
        self.config = config
        self._transport = transport

    @property
    def model_id(self) -> str:
        """Return provider-neutral workload intent as the framework identifier."""
        return self.config.workload

    @property
    def backend(self) -> str:
        """Identify the default governed backend."""
        return "gateway"

    async def generate(self, messages: Sequence[TextMessage]) -> str:
        """Close each SDK call and refuse failures, partial output and unexpected features."""
        async with GatewayClient(self.config.connection, transport=self._transport) as gateway:
            response = await gateway.generate(
                workload=self.config.workload,
                messages=tuple(
                    Message(role=MessageRole(message.role), content=message.content)
                    for message in messages
                ),
                risk_level=self.config.risk_level,
                data_classification=self.config.data_classification,
                context_tokens_estimated=(sum(len(message.content) for message in messages) + 3)
                // 4,
                max_output_tokens=self.config.max_output_tokens,
                provider_timeout_seconds=self.config.provider_timeout_seconds,
            )
        if response.status is not ExecutionStatus.SUCCEEDED or response.error is not None:
            raise TextModelError("gateway generation did not succeed")
        if response.tool_calls or response.structured_output is not None:
            raise TextModelError("gateway specialist supports text output only")
        if not response.content or not response.content.strip():
            raise TextModelError("gateway generation returned no text")
        return response.content
