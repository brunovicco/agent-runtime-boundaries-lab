"""Text-only model boundary shared by explicitly selected inference backends."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


class TextModelError(RuntimeError):
    """Fail inference without exposing private provider details or returning partial text."""


@dataclass(frozen=True)
class TextMessage:
    """Framework-neutral text input; no tools, media or provider continuation state."""

    role: Literal["system", "user", "assistant"]
    content: str


def text_message(role: str, content: object) -> TextMessage:
    """Validate the small message subset supported by both specialist runtimes."""
    if role not in {"system", "user", "assistant"} or not isinstance(content, str):
        raise TextModelError("specialist supports system/user/assistant text only")
    if not content.strip():
        raise TextModelError("specialist requires non-empty text")
    # Narrow the role without allowing unchecked provider-specific roles.
    if role == "system":
        return TextMessage(role="system", content=content)
    if role == "assistant":
        return TextMessage(role="assistant", content=content)
    return TextMessage(role="user", content=content)


class TextGenerationClient(Protocol):
    """Describe one configured backend without exposing its credentials."""

    @property
    def model_id(self) -> str:
        """Return workload intent for the gateway or the explicit direct model ID."""
        ...

    @property
    def backend(self) -> str:
        """Return the selected inference backend name."""
        ...

    async def generate(self, messages: Sequence[TextMessage]) -> str:
        """Generate complete text with no local retries or backend fallback."""
        ...
