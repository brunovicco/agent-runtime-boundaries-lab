"""A2A JSON-RPC transport carrying canonical contracts and W3C trace context."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
from a2a_otel_kit import Observability, inject_trace_context
from opentelemetry import trace

from agent_runtime_boundaries.domain.contracts import SpecialistRequest, SpecialistResponse


class A2ASpecialistClient:
    """Small protocol adapter around an A2A message-send boundary."""

    def __init__(self, *, endpoint: str, observability: Observability) -> None:
        """Configure the specialist endpoint and trace lifecycle."""
        self._endpoint = endpoint.rstrip("/")
        self._observability = observability

    async def analyze(self, request: SpecialistRequest) -> SpecialistResponse:
        """Send a canonical specialist request inside an A2A text part."""
        headers: dict[str, str] = {"content-type": "application/json", "A2A-Version": "1.0"}
        with self._observability.start_span(
            "specialist.delegate",
            attributes={"operation": "specialist_delegate", "protocol": "a2a"},
            record_exception=False,
        ):
            inject_trace_context(headers)
            body = {
                "jsonrpc": "2.0",
                "id": str(uuid4()),
                "method": "SendMessage",
                "params": {
                    "message": {
                        "messageId": request.identity.delegation_id,
                        "contextId": request.identity.conversation_id,
                        "role": "ROLE_USER",
                        "parts": [{"text": request.model_dump_json()}],
                    },
                    "metadata": {
                        "schema": "agent-runtime-boundaries.specialist-request/1.0",
                        "conversation_id": request.identity.conversation_id,
                        "execution_id": request.identity.execution_id,
                        "delegation_id": request.identity.delegation_id,
                    },
                },
            }
            async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
                response = await client.post(self._endpoint, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
        if "error" in payload:
            raise RuntimeError("A2A specialist returned an error")
        result = payload.get("result", {})
        text = _extract_text(result)
        return SpecialistResponse.model_validate_json(text)


def _extract_text(result: dict[str, Any]) -> str:
    """Extract the first text part from common A2A message/task JSON shapes."""
    message = result.get("message") if isinstance(result.get("message"), dict) else result
    parts = message.get("parts", []) if isinstance(message, dict) else []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str):
            return text
        # Compatibility with v0.3 JSON representations that wrap text in a kind-tagged part.
        if part.get("kind") == "text" and isinstance(part.get("text"), str):
            text = part["text"]
            if isinstance(text, str):
                return text
    artifacts = result.get("artifacts", []) if isinstance(result, dict) else []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        for part in artifact.get("parts", []):
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    return text
    raise RuntimeError("A2A response did not contain a text result")


def current_trace_id() -> str | None:
    """Return the active OpenTelemetry trace id for diagnostics."""
    context = trace.get_current_span().get_span_context()
    return f"{context.trace_id:032x}" if context.is_valid else None
