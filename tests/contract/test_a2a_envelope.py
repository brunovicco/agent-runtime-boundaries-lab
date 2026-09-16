"""Contract checks for the minimal A2A message envelope used by the lab."""

import httpx
import pytest

pytest.importorskip("a2a_otel_kit")

from agent_runtime_boundaries.adapters.a2a_transport import A2ASpecialistClient, _extract_text
from agent_runtime_boundaries.adapters.observability import configure_observability
from agent_runtime_boundaries.domain.contracts import SpecialistRequest, SpecialistResponse
from agent_runtime_boundaries.domain.identity import ExecutionIdentity


def test_extract_text_accepts_v1_message_shape() -> None:
    assert _extract_text({"parts": [{"text": "result"}]}) == "result"


def test_extract_text_accepts_message_wrapper() -> None:
    assert _extract_text({"message": {"parts": [{"text": "result"}]}}) == "result"


def test_extract_text_rejects_missing_content() -> None:
    with pytest.raises(RuntimeError, match="text result"):
        _extract_text({"parts": []})


def _specialist_request() -> SpecialistRequest:
    identity = ExecutionIdentity(
        conversation_id="conversation-1", execution_id="exec:1", delegation_id="deleg:1"
    )
    return SpecialistRequest(
        identity=identity,
        prompt="Review merchant risk",
        payload={"merchant_tier": "growth"},
        idempotency_key=identity.idempotency_key("specialist-risk-review"),
    )


def _a2a_client(handler: httpx.Response) -> A2ASpecialistClient:
    def respond(_request: httpx.Request) -> httpx.Response:
        return handler

    return A2ASpecialistClient(
        endpoint="https://specialist.invalid/a2a",
        observability=configure_observability(
            service_name="test", enabled=False, otlp_endpoint="http://127.0.0.1:4318/v1/traces"
        ),
        transport=httpx.MockTransport(respond),
    )


def _a2a_result(response: SpecialistResponse) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "jsonrpc": "2.0",
            "id": "1",
            "result": {"parts": [{"text": response.model_dump_json()}]},
        },
    )


@pytest.mark.asyncio
async def test_analyze_rejects_response_identity_mismatch() -> None:
    request = _specialist_request()
    mismatched_identity = ExecutionIdentity(
        conversation_id="conversation-1", execution_id="exec:1", delegation_id="deleg:other"
    )
    forged = SpecialistResponse(
        identity=mismatched_identity,
        specialist=request.specialist,
        summary="unrelated result",
    )
    client = _a2a_client(_a2a_result(forged))

    with pytest.raises(RuntimeError, match="identity does not match"):
        await client.analyze(request)


@pytest.mark.asyncio
async def test_analyze_accepts_matching_response_identity() -> None:
    request = _specialist_request()
    genuine = SpecialistResponse(
        identity=request.identity,
        specialist=request.specialist,
        summary="matching result",
    )
    client = _a2a_client(_a2a_result(genuine))

    result = await client.analyze(request)
    assert result.summary == "matching result"
