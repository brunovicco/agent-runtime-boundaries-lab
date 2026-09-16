"""CrewAI custom LLM over an explicitly selected text generation client."""

import asyncio
from typing import TYPE_CHECKING, Any

from crewai import BaseLLM
from crewai.utilities.types import LLMMessage
from pydantic import BaseModel, PrivateAttr

from agent_runtime_boundaries.adapters.text_generation import (
    TextGenerationClient,
    TextMessage,
    TextModelError,
    text_message,
)

if TYPE_CHECKING:
    from crewai.agents.agent_builder.base_agent import BaseAgent
    from crewai.task import Task
    from crewai.tools.base_tool import BaseTool


class CrewAITextLLM(BaseLLM):
    """Translate bounded CrewAI text calls without local retries or backend fallback."""

    _client: TextGenerationClient = PrivateAttr()

    def __init__(self, client: TextGenerationClient) -> None:
        """Keep credentials outside serializable framework fields."""
        super().__init__(model=client.model_id, provider=client.backend)
        self._client = client

    def call(
        self,
        messages: str | list[LLMMessage],
        tools: "list[dict[str, BaseTool]] | None" = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: "Task | None" = None,
        from_agent: "BaseAgent | None" = None,
        response_model: type[BaseModel] | None = None,
    ) -> str:
        """Run the async SDK inside the specialist's CrewAI worker thread."""
        return asyncio.run(
            self.acall(
                messages,
                tools,
                callbacks,
                available_functions,
                from_task,
                from_agent,
                response_model,
            )
        )

    async def acall(
        self,
        messages: str | list[LLMMessage],
        tools: "list[dict[str, BaseTool]] | None" = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: "Task | None" = None,
        from_agent: "BaseAgent | None" = None,
        response_model: type[BaseModel] | None = None,
    ) -> str:
        """Accept only text and reject unimplemented features before inference."""
        if tools or available_functions or response_model is not None or self._effective_stream():
            raise TextModelError("CrewAI text LLM supports non-streaming text only")
        canonical: tuple[TextMessage, ...]
        if isinstance(messages, str):
            canonical = (text_message("user", messages),)
        else:
            for message in messages:
                if any(
                    message.get(field)
                    for field in ("tool_calls", "tool_call_id", "raw_tool_call_parts", "files")
                ):
                    raise TextModelError("CrewAI text LLM supports plain text messages only")
            canonical = tuple(
                text_message(message["role"], message["content"]) for message in messages
            )
        return await self._client.generate(canonical)

    def supports_function_calling(self) -> bool:
        """Prevent CrewAI from selecting its native tool-execution path."""
        return False

    def supports_stop_words(self) -> bool:
        """Declare that this bounded bridge exposes no caller sampling controls."""
        return False
