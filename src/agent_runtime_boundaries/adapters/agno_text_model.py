"""Agno model boundary over an explicitly selected text generation client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse

from agent_runtime_boundaries.adapters.text_generation import (
    TextGenerationClient,
    TextModelError,
    text_message,
)


class AgnoTextModel(Model):
    """Implement the asynchronous text path used by the bounded Agno specialist."""

    def __init__(self, client: TextGenerationClient) -> None:
        """Expose only backend/model identity and disable local retries."""
        super().__init__(
            id=client.model_id,
            name="Specialist text model",
            provider=client.backend,
            retries=0,
            retry_with_guidance=False,
        )
        self._client = client

    async def ainvoke(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        """Translate text without flattening tools, media or provider continuation state."""
        if kwargs.get("tools") or kwargs.get("response_format") is not None:
            raise TextModelError("Agno text model supports text generation only")
        if kwargs.get("tool_choice") not in (None, "none"):
            raise TextModelError("Agno text model does not support tool choice")
        for message in messages:
            if any(
                getattr(message, field, None)
                for field in (
                    "tool_calls",
                    "tool_call_id",
                    "images",
                    "audio",
                    "videos",
                    "files",
                    "provider_data",
                    "reasoning_content",
                    "redacted_reasoning_content",
                )
            ):
                raise TextModelError("Agno text model supports plain text messages only")
        content = await self._client.generate(
            tuple(text_message(message.role, message.content) for message in messages)
        )
        return ModelResponse(role="assistant", content=content)

    def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
        """Reject synchronous Agno calls outside the selected specialist path."""
        raise TextModelError("Agno text model requires asynchronous non-streaming execution")

    def invoke_stream(self, *args: Any, **kwargs: Any) -> Iterator[ModelResponse]:
        """Reject streaming outside the specialist's complete-text interface."""
        raise TextModelError("Agno text model does not expose framework streaming")

    def ainvoke_stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[ModelResponse]:
        """Reject asynchronous framework streaming before inference."""
        raise TextModelError("Agno text model does not expose framework streaming")

    def _parse_provider_response(self, response: Any, **kwargs: Any) -> ModelResponse:
        """Return the already normalized framework response."""
        if not isinstance(response, ModelResponse):
            raise TextModelError("unexpected Agno text response")
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        """Reject unsupported framework deltas."""
        raise TextModelError("Agno text model does not expose framework streaming")
