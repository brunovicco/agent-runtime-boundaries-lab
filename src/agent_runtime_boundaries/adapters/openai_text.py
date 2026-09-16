"""Explicit direct OpenAI Responses API backend for bounded specialist inference."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

import httpx
from openai import AsyncOpenAI, OpenAIError
from openai.types.responses import Response, ResponseInputParam
from pydantic import SecretStr, ValidationError

from agent_runtime_boundaries.adapters.text_generation import (
    TextMessage,
    TextModelError,
    text_message,
)


@dataclass(frozen=True)
class OpenAITextConfig:
    """Secret provider credential and explicit model/limits for the direct backend."""

    api_key: SecretStr = field(repr=False)
    model: str = "gpt-4.1-mini"
    max_output_tokens: int = 2000
    request_timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        """Reject missing credentials and invalid limits before opening a transport."""
        api_key = self.api_key.get_secret_value().strip()
        if not api_key or api_key == "replace-me":
            raise ValueError("OPENAI_API_KEY must be configured")
        if not self.model.strip() or self.model != self.model.strip():
            raise ValueError("OPENAI_MODEL must be a non-empty model identifier")
        if self.max_output_tokens < 16:
            raise ValueError("OPENAI_MAX_OUTPUT_TOKENS must be at least 16")
        if not 0 < self.request_timeout_seconds <= 300:
            raise ValueError("OPENAI_REQUEST_TIMEOUT_SECONDS must be in the range (0, 300]")


class OpenAITextClient:
    """Make one stateless provider request without gateway policy or automatic fallback."""

    def __init__(
        self,
        config: OpenAITextConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Retain secret configuration outside serializable framework fields."""
        self.config = config
        self._transport = transport

    @property
    def model_id(self) -> str:
        """Return the configured OpenAI model."""
        return self.config.model

    @property
    def backend(self) -> str:
        """Identify this explicitly selected direct backend."""
        return "openai"

    async def generate(self, messages: Sequence[TextMessage]) -> str:
        """Close each SDK call and return only validated, complete assistant text."""
        if not messages:
            raise TextModelError("OpenAI specialist requires non-empty messages")
        canonical = tuple(text_message(message.role, message.content) for message in messages)
        inputs: ResponseInputParam = [
            {"role": message.role, "content": message.content} for message in canonical
        ]
        try:
            async with (
                httpx.AsyncClient(
                    transport=self._transport,
                    timeout=self.config.request_timeout_seconds,
                    trust_env=False,
                    follow_redirects=False,
                ) as http_client,
                AsyncOpenAI(
                    api_key=self.config.api_key.get_secret_value().strip(),
                    # Never redirect the provider credential using OPENAI_BASE_URL/proxy env.
                    base_url="https://api.openai.com/v1",
                    max_retries=0,
                    timeout=self.config.request_timeout_seconds,
                    http_client=http_client,
                ) as client,
            ):
                result = await client.responses.create(
                    model=self.config.model,
                    input=inputs,
                    max_output_tokens=self.config.max_output_tokens,
                    store=False,
                    stream=False,
                )
                if not isinstance(result, Response):
                    raise TextModelError("OpenAI generation returned an invalid response")
                response = Response.model_validate(result.model_dump())
        except (OpenAIError, ValidationError, json.JSONDecodeError):
            raise TextModelError("OpenAI generation failed") from None

        if (
            response.status != "completed"
            or response.error is not None
            or response.incomplete_details is not None
        ):
            raise TextModelError("OpenAI generation did not complete")
        for item in response.output:
            # Reasoning is discarded; it never becomes provider continuation/global state.
            if item.type == "reasoning":
                continue
            if item.type != "message" or item.status != "completed":
                raise TextModelError("OpenAI specialist supports complete text output only")
            if any(content.type != "output_text" for content in item.content):
                raise TextModelError("OpenAI specialist returned unsupported output")
        content = response.output_text
        if not content.strip():
            raise TextModelError("OpenAI generation returned no text")
        return content
