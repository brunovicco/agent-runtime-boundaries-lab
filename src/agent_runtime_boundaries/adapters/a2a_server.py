"""Minimal A2A message-send server adapter for any specialist port."""

from typing import Any

from a2a_otel_kit import Observability, continue_trace
from fastapi import APIRouter, Request

from agent_runtime_boundaries.application.ports import SpecialistPort
from agent_runtime_boundaries.domain.contracts import SpecialistRequest


def build_a2a_router(*, specialist: SpecialistPort, observability: Observability) -> APIRouter:
    """Build an A2A JSON-RPC route around a specialist port."""
    router = APIRouter()

    @router.post("/a2a")
    async def message_send(request: Request) -> dict[str, Any]:
        body = await request.json()
        request_id = body.get("id")
        if body.get("method") not in {"SendMessage", "message/send"}:
            return _error(request_id, -32601, "unsupported A2A method")
        try:
            text = _request_text(body)
            canonical = SpecialistRequest.model_validate_json(text)
        except (KeyError, TypeError, ValueError):
            return _error(request_id, -32602, "invalid specialist request")

        carrier = dict(request.headers)
        with (
            continue_trace(carrier),
            observability.start_span(
                "specialist.handle",
                attributes={"operation": "specialist_handle", "protocol": "a2a"},
                record_exception=False,
            ),
        ):
            observability.emit_event(
                "specialist.request.received",
                "success",
                operation="specialist_request",
            )
            result = await specialist.analyze(canonical)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "messageId": canonical.identity.delegation_id,
                "contextId": canonical.identity.conversation_id,
                "role": "ROLE_AGENT",
                "parts": [{"text": result.model_dump_json()}],
            },
        }

    return router


def _request_text(body: dict[str, Any]) -> str:
    parts = body["params"]["message"]["parts"]
    for part in parts:
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                return text
    raise ValueError("text part missing")


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
